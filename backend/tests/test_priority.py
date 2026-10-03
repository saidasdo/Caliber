"""Tests for alert priority scoring (SPEC section 5.4) against the real ingested DB."""

import sqlite3

import pytest

from app.config import DB_PATH
from app.engine.priority import CLASS_SCORE, compute_priority

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


def test_sorted_descending_by_score(conn):
    rows = compute_priority(conn, "2026-04-08")
    scores = [r["priority_score"] for r in rows]
    assert scores == sorted(scores, reverse=True)


def test_score_formula_matches_breakdown(conn):
    rows = compute_priority(conn, "2026-04-08")
    for r in rows:
        b = r["breakdown"]
        expected = round(0.4 * b["severity"] + 0.3 * b["class_score"] + 0.3 * b["loss_exposure"], 4)
        assert r["priority_score"] == expected


def test_trip_week_gets_max_severity(conn):
    # PU-2101B's TRIP week is 2026-03-12 (see backtest / acceptance data).
    rows = compute_priority(conn, "2026-03-12")
    pu = next(r for r in rows if r["equipment_tag"] == "PU-2101B")
    assert pu["breakdown"]["severity"] == 1.0
    assert pu["health_status"] == "TRIP"


def test_normal_week_gets_zero_or_rising_severity(conn):
    # Well before any equipment's first ALARM, severity should be 0 (normal) for all.
    rows = compute_priority(conn, "2026-01-01")
    for r in rows:
        assert r["breakdown"]["severity"] in (0.0, 0.4)


def test_class_score_mapping_matches_equipment_class(conn):
    rows = compute_priority(conn, "2026-04-08")
    for r in rows:
        eq_class = r["breakdown"]["eq_class"]
        assert r["breakdown"]["class_score"] == CLASS_SCORE.get(eq_class, 0.3)


def test_loss_exposure_is_normalized_zero_to_one(conn):
    rows = compute_priority(conn, "2026-04-08")
    exposures = [r["breakdown"]["loss_exposure"] for r in rows]
    assert min(exposures) >= 0.0
    assert max(exposures) <= 1.0
    assert max(exposures) == 1.0  # the highest-loss equipment defines the top of the scale


def test_ko3201_has_highest_loss_exposure(conn):
    # KO-3201's RCA loss (1584 k USD) is the largest among the five (see SPEC section 9).
    rows = compute_priority(conn, "2026-04-08")
    ko = next(r for r in rows if r["equipment_tag"] == "KO-3201")
    assert ko["breakdown"]["loss_exposure"] == 1.0


def test_priority_label_thresholds_are_consistent_with_score(conn):
    rows = compute_priority(conn, "2026-04-08")
    for r in rows:
        score, label = r["priority_score"], r["priority_label"]
        if label == "Critical":
            assert score >= 0.8
        elif label == "High":
            assert 0.6 <= score < 0.8
        elif label == "Medium":
            assert 0.4 <= score < 0.6
        else:
            assert score < 0.4


def test_worst_parameter_present_when_weekly_data_exists(conn):
    rows = compute_priority(conn, "2026-04-08")
    for r in rows:
        assert r["worst_parameter"] is not None
        assert "parameter" in r["worst_parameter"]
