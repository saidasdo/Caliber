"""Tests for phase 9: energy proxy, role/money audit logging, reset demo data."""

import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.config import DB_PATH
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


# ---------------------------------------------------------------------------
# Energy proxy
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("tag", ALL_TAGS)
def test_energy_proxy_always_carries_the_required_label(tag):
    r = client.get(f"/api/equipment/{tag}/energy-proxy")
    assert r.status_code == 200
    assert r.json()["label"] == "Proxy derived from motor current, not metered energy"


@pytest.mark.parametrize("tag", ALL_TAGS)
def test_energy_proxy_history_matches_hourly_window_days(conn, tag):
    expected_days = conn.execute(
        "SELECT COUNT(DISTINCT substr(ts, 1, 10)) FROM sensor_hourly "
        "WHERE equipment_tag = ? AND signal = 'motor_current'",
        (tag,),
    ).fetchone()[0]
    r = client.get(f"/api/equipment/{tag}/energy-proxy")
    body = r.json()
    assert len(body["history"]) == expected_days
    assert len(body["moving_average"]) == expected_days


def test_energy_proxy_daily_sum_matches_raw_hourly_data(conn):
    tag = "KO-3201"
    first_day_sum = conn.execute(
        "SELECT substr(ts,1,10) AS day, SUM(value) FROM sensor_hourly "
        "WHERE equipment_tag = ? AND signal = 'motor_current' GROUP BY day ORDER BY day LIMIT 1",
        (tag,),
    ).fetchone()
    r = client.get(f"/api/equipment/{tag}/energy-proxy")
    first_history_point = r.json()["history"][0]
    assert first_history_point["day"] == first_day_sum[0]
    assert abs(first_history_point["motor_load_index"] - first_day_sum[1]) < 0.01


def test_energy_proxy_forecast_is_seven_days_starting_after_the_window():
    r = client.get("/api/equipment/KO-3201/energy-proxy")
    body = r.json()
    last_history_day = body["history"][-1]["day"]
    forecast_days = [f["day"] for f in body["forecast"]]
    assert len(forecast_days) == 7
    assert forecast_days[0] > last_history_day
    assert forecast_days == sorted(forecast_days)


def test_energy_proxy_forecast_equals_final_moving_average():
    r = client.get("/api/equipment/KO-3201/energy-proxy")
    body = r.json()
    last_moving_average = body["moving_average"][-1]["value"]
    assert all(f["value"] == last_moving_average for f in body["forecast"])


def test_energy_proxy_unknown_tag_is_404():
    r = client.get("/api/equipment/NOT-A-TAG/energy-proxy")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Role switch / view money audit logging (SPEC section 5.11)
# ---------------------------------------------------------------------------


def test_role_switch_is_logged_to_audit_log():
    before = len(client.get("/api/audit-log", params={"action_type": "role_switch"}).json()["results"])
    r = client.post(
        "/api/audit-log/role-switch",
        json={"from_role": "Engineer", "to_role": "Plant manager", "selected_plant": "ZCU"},
    )
    assert r.status_code == 200
    after = client.get("/api/audit-log", params={"action_type": "role_switch"}).json()["results"]
    assert len(after) == before + 1
    assert "ZCU" in after[0]["detail_json"]


def test_view_money_is_logged_to_audit_log():
    before = len(client.get("/api/audit-log", params={"action_type": "view_money"}).json()["results"])
    r = client.post(
        "/api/audit-log/view-money",
        json={"actor_role": "Executive", "page": "overview", "plant_code": None},
    )
    assert r.status_code == 200
    after = client.get("/api/audit-log", params={"action_type": "view_money"}).json()["results"]
    assert len(after) == before + 1
    assert after[0]["actor_role"] == "Executive"


# ---------------------------------------------------------------------------
# Reset demo data
# ---------------------------------------------------------------------------


def test_reset_demo_data_restores_pristine_action_count():
    # Other test modules in the full suite may have already mutated this shared DB (see
    # tests/test_actions_phase6.py), so compare against a captured baseline, not a literal
    # count, and only assert the known-pristine invariant (47 preloaded) after reset.
    before_count = len(client.get("/api/actions").json()["results"])

    client.post(
        "/api/actions/approve",
        json={
            "equipment_tag": "KO-3201",
            "action_text": "Phase 9 reset test action",
            "pic": "TEST-RESET",
            "due_date": "2026-05-01",
        },
    )
    mutated_count = len(client.get("/api/actions").json()["results"])
    assert mutated_count == before_count + 1

    r = client.post("/api/reset-demo-data")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

    reset_count = len(client.get("/api/actions").json()["results"])
    assert reset_count == 47  # always true post-reset: exactly the preloaded CAPA actions


def test_reset_demo_data_reports_all_acceptance_checks():
    r = client.post("/api/reset-demo-data")
    checks = r.json()["checks"]
    assert len(checks) == 11
    assert all(c["passed"] is not False for c in checks)
