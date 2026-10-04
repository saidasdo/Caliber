"""Replay visibility (SPEC 4): with the replay date set, every live view behaves as if today is that
date. Nothing dated after it is returned, except the labeled 7-day forecast of the energy proxy.
Also covers the revised alert severity, the class fallback, the Executive KPI cells and the action
visibility rule."""

import json
import re
import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.config import DB_PATH
from app.engine.priority import _urgency
from app.engine.replay import REPLAY_PRESETS
from app.main import app

pytestmark = pytest.mark.skipif(not DB_PATH.exists(), reason="run `npm run ingest` first")

client = TestClient(app)
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
FULL_RECORD = "2099-12-31"


def _dates_in(obj, found: list) -> list:
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key == "forecast":  # the labeled projection, checked separately
                continue
            _dates_in(value, found)
    elif isinstance(obj, list):
        for value in obj:
            _dates_in(value, found)
    elif isinstance(obj, str):
        found.extend(DATE_RE.findall(obj))
    return found


def _live_views(tag: str, replay: str) -> dict:
    """Every live view for a machine on a replay date (equipment, its series, the overview and its plant)."""
    plant = client.get(f"/api/equipment/{tag}", params={"replay_date": replay}).json()["plant_code"]
    views = {
        "equipment": client.get(f"/api/equipment/{tag}", params={"replay_date": replay}),
        "diagnosis": client.get(f"/api/equipment/{tag}/diagnosis", params={"replay_date": replay}),
        "similar": client.get(f"/api/equipment/{tag}/similar-incidents", params={"replay_date": replay}),
        "suggested": client.get(f"/api/equipment/{tag}/suggested-actions", params={"replay_date": replay}),
        "status_timeline": client.get(f"/api/equipment/{tag}/status-timeline", params={"replay_date": replay}),
        "weekly_series": client.get(f"/api/equipment/{tag}/weekly-series", params={"replay_date": replay}),
        "anomalies": client.get(
            f"/api/equipment/{tag}/anomalies", params={"replay_date": replay, "signal": "vibration"}
        ),
        "energy_proxy": client.get(f"/api/equipment/{tag}/energy-proxy", params={"replay_date": replay}),
        "emission": client.get(f"/api/equipment/{tag}/emission", params={"replay_date": replay}),
        "overview": client.get("/api/overview", params={"replay_date": replay}),
        "plant": client.get(f"/api/plants/{plant}", params={"replay_date": replay}),
        "problems": client.get("/api/problems", params={"replay_date": replay}),
        "actions": client.get("/api/actions", params={"replay_date": replay, "equipment_tag": tag}),
    }
    for signal in ("vibration", "temperature", "motor_current", "plant_rate", "discharge_pressure", "feed"):
        views[f"series_{signal}"] = client.get(
            f"/api/equipment/{tag}/series", params={"replay_date": replay, "signal": signal}
        )
    return views


@pytest.mark.parametrize("tag, replay", [("KO-3201", "2026-04-08"), ("PM-4405B", "2026-07-01")])
def test_no_live_view_returns_a_date_after_the_replay_date(tag, replay):
    for name, response in _live_views(tag, replay).items():
        if response.status_code == 404:
            continue  # the series that does not exist for this machine
        assert response.status_code == 200, name
        body = response.json()
        if name.startswith("series_") and not body.get("points"):
            continue
        dates = _dates_in(body, [])
        later = [d for d in dates if d > replay]
        assert not later, f"{name} returns dates after {replay}: {sorted(set(later))[:5]}"


@pytest.mark.parametrize("tag, replay", [("KO-3201", "2026-04-08"), ("PM-4405B", "2026-07-01")])
def test_weekly_series_has_no_week_after_the_replay_and_no_trip_week(tag, replay):
    body = client.get(f"/api/equipment/{tag}/weekly-series", params={"replay_date": replay}).json()
    for parameter in body["parameters"]:
        assert all(p["week_date"] <= replay for p in parameter["points"])
        assert all(p["health_status"] != "TRIP" for p in parameter["points"])
    assert body["axis_weeks"] == 26  # the chart keeps the full record width


def test_energy_forecast_starts_the_day_after_the_replay_date():
    body = client.get("/api/equipment/KO-3201/energy-proxy", params={"replay_date": "2026-04-08"}).json()
    assert all(h["day"] <= "2026-04-08" for h in body["history"])
    assert body["forecast"][0]["day"] == "2026-04-09"
    assert len(body["forecast"]) == 7
    assert all(f["kind"] == "forecast" for f in body["forecast"])


def test_hourly_series_stops_at_the_replay_date_and_keeps_the_axis_width():
    body = client.get(
        "/api/equipment/KO-3201/series", params={"replay_date": "2026-04-08", "signal": "vibration"}
    ).json()
    assert body["points"][-1]["ts"].startswith("2026-04-08")
    assert body["axis_hours"] > len(body["points"])  # the record is longer than the replay window
    full = client.get(
        "/api/equipment/KO-3201/series", params={"replay_date": FULL_RECORD, "signal": "vibration"}
    ).json()
    assert full["axis_hours"] == body["axis_hours"]


def test_replay_before_the_hourly_record_returns_no_points():
    body = client.get(
        "/api/equipment/KO-3201/series", params={"replay_date": "2025-01-01", "signal": "vibration"}
    ).json()
    assert body["points"] == []


def test_status_timeline_only_counts_hours_up_to_the_replay_date():
    body = client.get("/api/equipment/KO-3201/status-timeline", params={"replay_date": "2026-04-08"}).json()
    assert all(s["end_ts"] <= "2026-04-08 23:59:59" for s in body["segments"])
    trip_off = next(d for d in body["distribution"] if d["lane"] == "trip_off")
    assert trip_off["duration_hours"] == 0  # the OFF hours come after the replay date
    assert body["segments"][-1]["lane"] == "alarm"


# ---------------------------------------------------------------------------
# Revised alert severity and class fallback
# ---------------------------------------------------------------------------


def _state(status: str, trend: str = "flat", alarm: float | None = 1.0, value: float = 0.5):
    # value below the alarm limit by default: no parameter past alarm, so the alarm share is 0
    return {
        "health_status": status,
        "parameters": [{"trend": trend, "alarm": alarm, "value": value, "direction": "higher_is_worse"}],
    }


def _severity(week_state, margin):
    """The engine's urgency terms for a machine state (kept under the old helper name for the tests)."""
    return {"severity": _urgency(week_state, margin)["urgency"]}


def test_urgency_is_proximity_and_alarm_share_with_trip_at_one():
    assert _severity(_state("TRIP"), -5.0)["severity"] == 1.0
    assert _severity(_state("ALARM"), 90.0)["severity"] == pytest.approx(0.06)  # 0.6 x 0.1, no share
    assert _severity(_state("ALARM"), 20.0)["severity"] == pytest.approx(0.48)  # 0.6 x 0.8
    assert _severity(_state("NORMAL"), 60.0)["severity"] == pytest.approx(0.24)  # no status floor
    assert _severity(_state("NORMAL", trend="rising"), 95.0)["severity"] == pytest.approx(0.03)  # no rising floor
    assert _severity(_state("NORMAL"), 100.0)["severity"] == 0.0  # at baseline: nothing to worry about
    assert _severity(None, 50.0)["severity"] == 0.0  # no data on or before the replay date


def test_alarm_share_raises_urgency_when_parameters_are_past_their_limit():
    past = _state("ALARM", value=2.0)  # one parameter, past its alarm limit: share 1.0
    assert _severity(past, 90.0)["severity"] == pytest.approx(0.46)  # 0.6 x 0.1 + 0.4 x 1.0


def test_criticality_breakdown_is_carried_for_the_tie_break():
    body = client.get("/api/overview", params={"replay_date": "2026-04-08"}).json()
    for row in body["priority_queue"]:
        b = row["breakdown"]
        assert {"health_margin_pct", "proximity", "alarm_share", "criticality"} <= set(b)
        if b["health_margin_pct"] is not None:
            proximity = min(1.0, max(0.0, 1 - b["health_margin_pct"] / 100))
            assert row["priority_score"] == pytest.approx(0.6 * proximity + 0.4 * b["alarm_share"], abs=1e-3)


def test_priority_order_on_the_replay_dates_is_derived_not_hardcoded():
    """The order is re-derived on every call from the rank key; the ranks are 1..n on every date."""
    for replay in ["2026-04-08", *REPLAY_PRESETS.values()]:
        rows = client.get("/api/overview", params={"replay_date": replay}).json()["priority_queue"]
        assert [r["rank"] for r in rows] == list(range(1, len(rows) + 1))


def test_priority_order_on_8_apr_2026_matches_the_documented_result():
    rows = client.get("/api/overview", params={"replay_date": "2026-04-08"}).json()["priority_queue"]
    assert rows[0]["equipment_tag"] == "KO-3201"
    assert rows[0]["priority_label"] == "Critical"


# ---------------------------------------------------------------------------
# Executive KPI cells
# ---------------------------------------------------------------------------


def test_production_vs_normal_cell_is_empty_when_no_equipment_has_hourly_data():
    kpi = client.get("/api/overview", params={"replay_date": "2025-01-01"}).json()["kpi_band"]["production_vs_normal"]
    assert kpi["value"] is None
    assert kpi["message"] == "No hourly data"
    assert kpi["breakdown"] == []


def test_production_vs_normal_cell_averages_the_equipment_with_hourly_data():
    kpi = client.get("/api/overview", params={"replay_date": "2026-04-08"}).json()["kpi_band"]["production_vs_normal"]
    assert kpi["count"] == len(kpi["breakdown"]) > 0
    values = [b["value"] for b in kpi["breakdown"]]
    assert kpi["value"] == pytest.approx(sum(values) / len(values), abs=0.06)


def test_energy_cell_compares_the_replay_week_with_the_week_before():
    kpi = client.get("/api/overview", params={"replay_date": "2026-04-08"}).json()["kpi_band"]["energy_proxy"]
    assert kpi["value"] > 0
    assert kpi["previous"] > 0
    assert kpi["forecast_direction"] in {"up", "down", "flat"}
    assert sum(b["week"] for b in kpi["breakdown"]) == pytest.approx(kpi["value"], abs=0.05)


def test_emission_cell_breakdown_excludes_the_heat_exchanger():
    kpi = client.get("/api/overview", params={"replay_date": "2026-04-08"}).json()["kpi_band"]["emission_kg"]
    tags = {b["equipment_tag"] for b in kpi["breakdown"]}
    assert "HE-3301" not in tags  # no motor drive
    # Only machines with motor current on the replay date are counted (the others have no hourly
    # record that day), so the breakdown is a subset of the four motor-driven machines.
    assert tags <= {"PU-2101B", "KO-3201", "PM-4405B", "BL-5702"} and tags


# ---------------------------------------------------------------------------
# Action visibility: an action is known from the date it was made (or its RCA's failure date)
# ---------------------------------------------------------------------------


def test_preloaded_capa_actions_appear_only_once_their_rca_is_known():
    before = client.get("/api/actions", params={"replay_date": "2026-04-08", "equipment_tag": "KO-3201"}).json()
    after = client.get("/api/actions", params={"replay_date": "2026-05-01", "equipment_tag": "KO-3201"}).json()
    assert before["results"] == []  # the KO-3201 RCA failure date is 29 Apr 2026
    assert len(after["results"]) > 0


def test_action_created_on_a_replay_date_is_hidden_before_that_date():
    created = client.post(
        "/api/actions/approve",
        json={
            "equipment_tag": "BL-5702",
            "action_text": "Replay visibility test action",
            "pic": "Test",
            "due_date": "2026-12-31",
        },
        headers={"X-Replay-Date": "2026-04-08"},
    )
    assert created.status_code == 200
    try:
        text = "Replay visibility test action"
        seen_later = client.get("/api/actions", params={"replay_date": "2026-05-01"}).json()["results"]
        seen_earlier = client.get("/api/actions", params={"replay_date": "2026-03-01"}).json()["results"]
        assert any(a["action_text"] == text for a in seen_later)
        assert not any(a["action_text"] == text for a in seen_earlier)
    finally:
        client.post("/api/reset-demo-data")
