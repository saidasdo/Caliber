"""Replay leakage (nothing shown for a replay date may use information dated after it), health
margin against the healthy baseline, emission estimate, MTBF/MTTR, and the KO-3201 vibration
display unit. Each rule is documented in the assumptions table (see npm run ingest)."""

import json
import re
import sqlite3
from statistics import median

import pytest
from fastapi.testclient import TestClient

from app.config import DB_PATH
from app.engine.energy_proxy import get_emission
from app.engine.gauges import compute_gauges
from app.engine.impact import estimate_impact
from app.engine.reliability import compute_reliability
from app.main import app

pytestmark = pytest.mark.skipif(not DB_PATH.exists(), reason="run `npm run ingest` first")

client = TestClient(app)
ALL_TAGS = ["PU-2101B", "KO-3201", "PM-4405B", "HE-3301", "BL-5702"]


@pytest.fixture
def conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    yield c
    c.close()


def _keys(obj, found: set) -> set:
    if isinstance(obj, dict):
        for key, value in obj.items():
            found.add(key)
            _keys(value, found)
    elif isinstance(obj, list):
        for value in obj:
            _keys(value, found)
    return found


def _replay_responses(tag: str, replay_date: str) -> dict:
    """Every response that shows machine-level information for a replay date."""
    return {
        "equipment": client.get(f"/api/equipment/{tag}", params={"replay_date": replay_date}).json(),
        "suggested": client.get(f"/api/equipment/{tag}/suggested-actions", params={"replay_date": replay_date}).json(),
        "similar": client.get(f"/api/equipment/{tag}/similar-incidents", params={"replay_date": replay_date}).json(),
        "overview": client.get("/api/overview", params={"replay_date": replay_date}).json(),
    }


def _rca_texts(conn: sqlite3.Connection, rca_id: int) -> list:
    row = conn.execute(
        "SELECT root_cause, problem_statement FROM rca_reports WHERE rca_id = ?", (rca_id,)
    ).fetchone()
    texts = [t for t in (row["root_cause"], row["problem_statement"]) if t and len(t) > 25]
    texts += [
        r[0]
        for r in conn.execute(
            "SELECT action_text FROM capa_actions WHERE rca_id = ? AND length(action_text) > 25", (rca_id,)
        ).fetchall()
    ]
    return texts


# ---------------------------------------------------------------------------
# Part 1: replay leakage
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("tag, replay_date, rca_id", [("KO-3201", "2026-04-08", 2), ("PM-4405B", "2026-07-01", 3)])
def test_no_future_loss_rca_or_incident_leaks_into_replay(conn, tag, replay_date, rca_id):
    responses = _replay_responses(tag, replay_date)
    keys = set()
    for body in responses.values():
        _keys(body, keys)
    # The whole-period performance summary (includes later failures) and its loss are never returned.
    assert "performance_summary" not in keys
    assert "estimated_loss_kusd" not in keys

    # The RCA is not shown yet, and none of its text appears in any replay response.
    assert responses["equipment"]["linked_rca"] is None
    blob = json.dumps(responses)
    for text in _rca_texts(conn, rca_id):
        assert text not in blob

    # Later incidents for this machine exist in the data, but none is returned for the replay date.
    later = conn.execute(
        "SELECT serial_no FROM incidents WHERE tag_number = ? AND date_of_occur >= ?", (tag, replay_date)
    ).fetchall()
    assert later
    for row in responses["similar"]["results"]:
        assert row["date_of_occur"] < replay_date
    for row in later:
        # word boundary: serial 2 must not match serial 213
        assert re.search(rf'"serial_no": {row[0]}', blob) is None


def test_ko3201_replay_impact_uses_only_earlier_incidents(conn):
    replay = "2026-04-08"
    impact = estimate_impact(conn, "KO-3201", replay)
    count = conn.execute(
        "SELECT COUNT(*) FROM incidents WHERE date_of_occur < ? AND eq_type_family = 'compressor' "
        "AND total_loss_kusd IS NOT NULL",
        (replay,),
    ).fetchone()[0]
    assert impact["basis"] == "eq_type_family"
    assert impact["n_incidents"] == count
    # No role header means Executive (see visibility.py), which sees the money value.
    body_exec = client.get("/api/equipment/KO-3201", params={"replay_date": replay}).json()
    assert body_exec["impact"]["value_kusd"] == impact["value_kusd"]
    # Engineer never sees the value (server-side redaction).
    body_eng = client.get(
        "/api/equipment/KO-3201", params={"replay_date": replay}, headers={"X-Role": "Engineer"}
    ).json()
    assert "value_kusd" not in body_eng["impact"]


def test_ko3201_rca_is_shown_once_the_failure_date_has_passed():
    body = client.get("/api/equipment/KO-3201", params={"replay_date": "2026-05-01"}).json()
    assert body["linked_rca"] is not None
    assert body["linked_rca"]["root_cause"]


# ---------------------------------------------------------------------------
# Part 2: health margin against the healthy baseline
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("tag", ALL_TAGS)
def test_healthy_week_is_green_for_every_machine(conn, tag):
    """Week 2 is inside the healthy baseline window: margin about 100%, above the alarm margin."""
    week2 = conn.execute(
        "SELECT week_date FROM health_weekly WHERE equipment_tag = ? ORDER BY week LIMIT 1 OFFSET 1", (tag,)
    ).fetchone()[0]
    margin = compute_gauges(conn, tag, week2)["health_margin"]
    assert margin["value"] > margin["alarm_margin_pct"] > 0


@pytest.mark.parametrize("tag", ALL_TAGS)
def test_last_alarm_week_is_red_or_low_amber(conn, tag):
    """The last ALARM week before a trip: margin between 0 (trip limit) and the alarm margin."""
    last_alarm = conn.execute(
        "SELECT week_date FROM health_weekly WHERE equipment_tag = ? AND health_status = 'ALARM' "
        "ORDER BY week DESC LIMIT 1",
        (tag,),
    ).fetchone()[0]
    margin = compute_gauges(conn, tag, last_alarm)["health_margin"]
    assert 0 <= margin["value"] < margin["alarm_margin_pct"]


def test_margin_matches_the_documented_formula(conn):
    replay = "2026-04-22"
    margin = compute_gauges(conn, "KO-3201", replay)["health_margin"]
    parameter = margin["worst_parameter"]
    value, trip, direction = conn.execute(
        "SELECT cw.value, pl.trip, pl.direction FROM condition_weekly cw "
        "JOIN health_weekly hw ON hw.equipment_tag = cw.equipment_tag AND hw.week = cw.week "
        "JOIN param_limits pl ON pl.equipment_tag = cw.equipment_tag AND pl.parameter = cw.parameter "
        "WHERE cw.equipment_tag = 'KO-3201' AND cw.parameter = ? AND hw.week_date <= ? "
        "ORDER BY hw.week_date DESC LIMIT 1",
        (parameter, replay),
    ).fetchone()
    first_week = conn.execute("SELECT MIN(week) FROM condition_weekly WHERE equipment_tag = 'KO-3201'").fetchone()[0]
    baseline = median(
        r[0]
        for r in conn.execute(
            "SELECT value FROM condition_weekly WHERE equipment_tag = 'KO-3201' AND parameter = ? "
            "AND week < ? AND value IS NOT NULL",
            (parameter, first_week + 6),
        ).fetchall()
    )
    assert margin["baseline"] == pytest.approx(baseline, abs=0.01)
    if direction == "higher_is_worse":
        expected = (trip - value) / (trip - baseline) * 100
    else:
        expected = (value - trip) / (baseline - trip) * 100
    assert margin["value"] == pytest.approx(expected, abs=0.1)


# ---------------------------------------------------------------------------
# Part 3: emission, MTBF/MTTR, display unit
# ---------------------------------------------------------------------------


def test_heat_exchanger_has_no_emission_estimate(conn):
    emission = get_emission(conn, "HE-3301", "2026-05-14")
    assert emission["applicable"] is False
    assert emission["today_kg"] is None


def test_motor_driven_emission_is_positive_and_labeled(conn):
    emission = get_emission(conn, "KO-3201", "2026-04-08")
    assert emission["applicable"] is True
    assert emission["today_kg"] and emission["today_kg"] > 0
    assert emission["label"] == "Estimate from motor current, not metered"
    assert set(emission["factors"]) == {"motor_voltage_kv", "power_factor", "grid_emission_factor_kg_per_kwh"}


def test_emission_never_uses_days_after_the_replay_date(conn):
    emission = get_emission(conn, "KO-3201", "2026-04-08")
    assert all(p["day"] <= "2026-04-08" for p in emission["series"])


def test_mtbf_is_no_failure_before_the_first_trip(conn):
    reliability = compute_reliability(conn, "KO-3201", "2026-04-08")
    assert reliability["failures"] == 0
    assert reliability["mtbf_hours"] is None
    assert reliability["message"] == "No failure in period"


def test_mtbf_after_the_trip_uses_only_data_up_to_the_replay_date(conn):
    reliability = compute_reliability(conn, "KO-3201", "2026-06-30")
    assert reliability["failures"] == 1
    assert reliability["downtime_hours"] == 32
    assert reliability["mttr_hours"] == 32.0


def test_ko3201_vibration_series_shows_assumed_micron_unit():
    body = client.get("/api/equipment/KO-3201/series", params={"signal": "vibration"}).json()
    assert body["display_unit"] == "µm (assumed, see DQ1)"
    other = client.get("/api/equipment/PU-2101B/series", params={"signal": "vibration"}).json()
    assert other["display_unit"] == "MM/S"
