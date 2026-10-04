"""Alert priority (SPEC section 5.4, revised) against the real ingested DB. Urgency is both the rank and the
displayed number; labels depend on urgency and status only."""

import sqlite3

import pytest

from app.config import DB_PATH
from app.engine.priority import compute_priority

pytestmark = pytest.mark.skipif(not DB_PATH.exists(), reason="run `npm run ingest` first")


@pytest.fixture
def conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    yield c
    c.close()


def test_returns_all_five_sensor_equipment(conn):
    rows = compute_priority(conn, "2026-04-08")
    assert {r["equipment_tag"] for r in rows} == {
        "PU-2101B", "KO-3201", "PM-4405B", "HE-3301", "BL-5702",
    }


def test_score_is_the_urgency_formula(conn):
    for date in ["2026-04-08", "2026-03-05"]:
        for r in compute_priority(conn, date):
            b = r["breakdown"]
            if r["health_status"] == "TRIP":
                assert r["priority_score"] == 1.0
            else:
                expected = 0.6 * b["proximity"] + 0.4 * b["alarm_share"]
                assert r["priority_score"] == pytest.approx(expected, abs=1e-3)
            assert b["severity"] == r["priority_score"]  # the displayed number is the urgency


def test_score_order_equals_rank_order(conn):
    for date in ["2026-04-08", "2026-04-22", "2026-03-05", "2026-07-01", "2026-05-14", "2026-06-10"]:
        rows = compute_priority(conn, date)
        assert [r["rank"] for r in rows] == list(range(1, len(rows) + 1))
        scores = [r["priority_score"] for r in rows]
        assert scores == sorted(scores, reverse=True)


def test_trip_week_gets_max_urgency(conn):
    # PU-2101B's TRIP week is 2026-03-12 (see backtest / acceptance data).
    rows = compute_priority(conn, "2026-03-12")
    pu = next(r for r in rows if r["equipment_tag"] == "PU-2101B")
    assert pu["breakdown"]["severity"] == 1.0
    assert pu["health_status"] == "TRIP"
    assert pu["priority_label"] == "Critical"


def test_normal_week_urgency_is_proximity_and_share_only(conn):
    # Before any equipment's first ALARM: no status floor, so urgency is the margin-based terms alone.
    rows = compute_priority(conn, "2026-01-01")
    for r in rows:
        b = r["breakdown"]
        if b["health_margin_pct"] is None:
            assert r["priority_score"] == 0.0
            continue
        proximity = min(1.0, max(0.0, 1 - b["health_margin_pct"] / 100))
        assert r["priority_score"] == pytest.approx(0.6 * proximity + 0.4 * b["alarm_share"], abs=1e-3)


def test_criticality_is_carried_for_the_tie_break(conn):
    rows = compute_priority(conn, "2026-04-08")
    ko = next(r for r in rows if r["equipment_tag"] == "KO-3201")
    assert ko["breakdown"]["criticality"] == "High"


def test_loss_exposure_is_normalized_zero_to_one(conn):
    rows = compute_priority(conn, "2026-04-08")
    exposures = [r["breakdown"]["loss_exposure"] for r in rows]
    assert min(exposures) >= 0.0
    assert max(exposures) <= 1.0
    assert max(exposures) == 1.0


def test_ko3201_loss_exposure_uses_replay_safe_estimate(conn):
    # KO-3201's estimated impact on 8 Apr is the lowest of the five (earlier compressor incidents only).
    rows = compute_priority(conn, "2026-04-08")
    ko = next(r for r in rows if r["equipment_tag"] == "KO-3201")
    assert ko["breakdown"]["loss_exposure"] == 0.0
    assert ko["estimated_impact"]["basis"] == "eq_type_family"


def test_worst_parameter_present_when_weekly_data_exists(conn):
    for r in compute_priority(conn, "2026-04-08"):
        assert r["worst_parameter"] is not None
