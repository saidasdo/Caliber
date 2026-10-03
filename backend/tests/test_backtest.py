"""Tests for the backtest engine (SPEC section 5.8). All values must be computed, never
hardcoded, so these check derivations against the raw tables rather than literal numbers
where possible, in addition to the known section 9 figures."""

import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.config import DB_PATH
from app.engine.backtest import run_backtest
from app.main import app

pytestmark = pytest.mark.skipif(not DB_PATH.exists(), reason="run `npm run ingest` first")

client = TestClient(app)

ALL_TAGS = ["PU-2101B", "KO-3201", "PM-4405B", "HE-3301", "BL-5702"]


@pytest.fixture
def conn():
    c = sqlite3.connect(DB_PATH)
    yield c
    c.close()


def test_returns_all_five_equipment(conn):
    results = run_backtest(conn)
    assert {r["equipment_tag"] for r in results} == set(ALL_TAGS)


def test_lead_time_weeks_matches_spec_section_9(conn):
    expected = {"PU-2101B": 6, "KO-3201": 11, "PM-4405B": 6, "HE-3301": 10, "BL-5702": 15}
    results = {r["equipment_tag"]: r for r in run_backtest(conn)}
    for tag, weeks in expected.items():
        assert results[tag]["lead_time_weeks"] == weeks


def test_lead_time_weeks_is_literally_trip_minus_alarm(conn):
    for r in run_backtest(conn):
        assert r["lead_time_weeks"] == r["first_trip_week"] - r["first_alarm_week"]


def test_first_alarm_and_trip_dates_come_from_health_weekly(conn):
    for r in run_backtest(conn):
        tag = r["equipment_tag"]
        alarm_date = conn.execute(
            "SELECT week_date FROM health_weekly WHERE equipment_tag = ? AND week = ?",
            (tag, r["first_alarm_week"]),
        ).fetchone()[0]
        trip_date = conn.execute(
            "SELECT week_date FROM health_weekly WHERE equipment_tag = ? AND week = ?",
            (tag, r["first_trip_week"]),
        ).fetchone()[0]
        assert r["first_alarm_date"] == alarm_date
        assert r["first_trip_date"] == trip_date


def test_weekly_health_has_all_26_weeks_in_order(conn):
    for r in run_backtest(conn):
        weeks = r["weekly_health"]
        assert len(weeks) == 26
        assert [w["week"] for w in weeks] == list(range(1, 27))


def test_weekly_health_trip_week_status_is_trip(conn):
    for r in run_backtest(conn):
        trip_row = next(w for w in r["weekly_health"] if w["week"] == r["first_trip_week"])
        assert trip_row["health_status"] == "TRIP"


def test_first_hourly_anomaly_week_falls_within_the_weekly_series(conn):
    for r in run_backtest(conn):
        if r["first_hourly_anomaly_week"] is not None:
            assert 1 <= r["first_hourly_anomaly_week"] <= 26
            # The anomaly, found from hourly data, should not predate the weekly ALARM that
            # the same underlying degradation already produced.
            assert r["first_hourly_anomaly_week"] >= r["first_alarm_week"]


def test_downtime_and_loss_come_from_performance_summary(conn):
    for r in run_backtest(conn):
        row = conn.execute(
            "SELECT total_downtime_hours, estimated_loss_kusd FROM performance_summary "
            "WHERE equipment_tag = ?",
            (r["equipment_tag"],),
        ).fetchone()
        assert r["downtime_hours"] == row[0]
        assert r["loss_kusd"] == row[1]


def test_message_states_the_computed_lead_time():
    r = client.get("/api/backtest")
    for row in r.json()["results"]:
        assert row["message"] == (
            f"Warning was available {row['lead_time_weeks']} weeks before the trip "
            "(weekly ALARM to TRIP)."
        )


def test_api_response_includes_weekly_health_and_anomaly_week():
    r = client.get("/api/backtest")
    assert r.status_code == 200
    for row in r.json()["results"]:
        assert "weekly_health" in row
        assert "first_hourly_anomaly_week" in row
