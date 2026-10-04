"""Dominance rule and the urgency order (SPEC 5.4, revised). No equipment names in the engine: these checks
run over every pair of equipment on several dates."""

import sqlite3

import pytest

from app.config import DB_PATH
from app.engine.priority import compute_priority
from app.engine.replay import REPLAY_PRESETS

pytestmark = pytest.mark.skipif(not DB_PATH.exists(), reason="run `npm run ingest` first")

DATES = ["2026-04-08", "2026-04-22", "2026-03-20", "2026-05-01", "2026-06-01", "2026-07-01", *REPLAY_PRESETS.values()]
CRITICALITY_RANK = {"High": 3, "Medium": 2, "Low": 1}


@pytest.fixture
def conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    yield c
    c.close()


def test_dominance_rule_holds_for_every_pair_on_every_date(conn):
    """If A has a lower health margin, at least as many parameters past alarm, and an equal or higher
    criticality than B, then A ranks above B, whatever the loss exposure."""
    checked = 0
    for date in DATES:
        rows = compute_priority(conn, date)
        for a in rows:
            for b in rows:
                if a is b:
                    continue
                ba, bb = a["breakdown"], b["breakdown"]
                if ba["health_margin_pct"] is None or bb["health_margin_pct"] is None:
                    continue
                dominates = (
                    ba["health_margin_pct"] < bb["health_margin_pct"]
                    and ba["parameters_past_alarm"] >= bb["parameters_past_alarm"]
                    and CRITICALITY_RANK.get(ba["criticality"], 0) >= CRITICALITY_RANK.get(bb["criticality"], 0)
                )
                if dominates:
                    checked += 1
                    assert a["rank"] < b["rank"], f"{date}: {a['equipment_tag']} should rank above {b['equipment_tag']}"
    assert checked > 0  # the rule was exercised, not vacuously true


def test_score_order_equals_rank_order_on_every_date(conn):
    for date in DATES:
        rows = compute_priority(conn, date)
        assert [r["rank"] for r in rows] == list(range(1, len(rows) + 1))
        scores = [r["priority_score"] for r in rows]
        assert scores == sorted(scores, reverse=True)


def test_urgency_is_the_weighted_terms(conn):
    for date in DATES:
        for r in compute_priority(conn, date):
            b = r["breakdown"]
            if r["health_status"] == "TRIP":
                assert r["priority_score"] == 1.0
            else:
                assert r["priority_score"] == pytest.approx(0.6 * b["proximity"] + 0.4 * b["alarm_share"], abs=1e-3)


def test_proximity_and_share_match_the_margin_and_parameters(conn):
    for date in DATES:
        for r in compute_priority(conn, date):
            b = r["breakdown"]
            if b["health_margin_pct"] is None:
                continue
            assert b["proximity"] == pytest.approx(min(1.0, max(0.0, 1 - b["health_margin_pct"] / 100)), abs=1e-3)
            assert b["alarm_share"] == pytest.approx(b["parameters_past_alarm"] / b["parameters_total"], abs=1e-3)


def test_expected_order_on_the_documented_dates(conn):
    expected = {
        "2026-04-08": ["KO-3201", "HE-3301", "BL-5702"],
        "2026-04-22": ["KO-3201", "HE-3301", "BL-5702"],
        "2026-05-14": ["HE-3301"],
        "2026-06-10": ["BL-5702"],
        "2026-07-01": ["PM-4405B"],
    }
    for date, first in expected.items():
        tags = [r["equipment_tag"] for r in compute_priority(conn, date)]
        assert tags[: len(first)] == first


def test_normal_status_never_gets_a_label_above_normal(conn):
    for date in DATES:
        for r in compute_priority(conn, date):
            if r["health_status"] == "NORMAL":
                assert r["priority_label"] == "Normal"


def test_labels_follow_the_urgency_thresholds(conn):
    for date in DATES:
        for r in compute_priority(conn, date):
            u, status = r["priority_score"], r["health_status"]
            if status == "TRIP" or u >= 0.7:
                assert r["priority_label"] == "Critical"
            elif u >= 0.5:
                assert r["priority_label"] == "High"
            elif u >= 0.25 or status == "ALARM":
                assert r["priority_label"] == "Medium"
            else:
                assert r["priority_label"] == "Normal"
