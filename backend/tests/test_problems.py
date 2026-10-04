"""Tests for the Problem Tank (SPEC section 5.7)."""

import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.config import DB_PATH
from app.main import app

pytestmark = pytest.mark.skipif(not DB_PATH.exists(), reason="run `npm run ingest` first")

client = TestClient(app)


@pytest.fixture
def conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    yield c
    c.close()


def test_ingestion_created_one_rca_problem_per_equipment(conn):
    rows = conn.execute("SELECT source_ref FROM problems WHERE source_type = 'rca'").fetchall()
    assert {r[0] for r in rows} == {"PU-2101B", "KO-3201", "PM-4405B", "HE-3301", "BL-5702"}


def test_ingestion_created_incident_problems_only_for_open_statuses(conn):
    open_count = conn.execute(
        "SELECT COUNT(*) FROM incidents WHERE overall_status NOT IN ('RISK CLOSED', 'RISK CANCELED')"
    ).fetchone()[0]
    problem_count = conn.execute(
        "SELECT COUNT(*) FROM problems WHERE source_type = 'incident'"
    ).fetchone()[0]
    assert problem_count == open_count


def test_problems_filtered_by_replay_date():
    # Well before any incident/RCA exists: nothing should show.
    r = client.get("/api/problems", params={"replay_date": "2020-01-01"})
    assert r.json()["results"] == []


def test_alert_problems_appear_before_the_rca_case_opens():
    """KO-3201 alarms on 2026-02-11 but its RCA case does not open until the 2026-04-29
    failure date; on 2026-04-08 it must show as an 'alert' problem, not be missing."""
    r = client.get("/api/problems", params={"replay_date": "2026-04-08"})
    body = r.json()
    alerts = [p for p in body["results"] if p["source_type"] == "alert"]
    assert {a["source_ref"] for a in alerts} == {"KO-3201", "HE-3301", "BL-5702"}
    assert body["counts_by_source_type"]["alert"] == 3


def test_alert_problem_disappears_once_its_own_rca_case_opens():
    # On the failure date itself, KO-3201 should be represented by its 'rca' problem instead.
    r = client.get("/api/problems", params={"replay_date": "2026-04-29"})
    by_ref = {p["source_ref"]: p["source_type"] for p in r.json()["results"] if p["source_ref"] == "KO-3201"}
    assert by_ref.get("KO-3201") == "rca"


def test_rca_problem_priority_label_is_computed_live_not_stored(conn):
    stored = conn.execute(
        "SELECT priority_label FROM problems WHERE source_type = 'rca' AND source_ref = 'KO-3201'"
    ).fetchone()[0]
    assert stored is None  # see api/problems.py: computed from the priority engine per request

    r = client.get("/api/problems", params={"replay_date": "2026-04-08"})
    ko_rca = next(
        (p for p in r.json()["results"] if p["source_type"] == "alert" and p["source_ref"] == "KO-3201"),
        None,
    )
    assert ko_rca is not None
    # Live: the label must equal what the priority engine computes for this replay date.
    from app.engine.priority import compute_priority

    engine_conn = sqlite3.connect(DB_PATH)
    engine_conn.row_factory = sqlite3.Row
    from_engine = next(p for p in compute_priority(engine_conn, "2026-04-08") if p["equipment_tag"] == "KO-3201")
    engine_conn.close()
    assert ko_rca["priority_label"] == from_engine["priority_label"]


def test_source_type_filter():
    r = client.get("/api/problems", params={"replay_date": "2026-04-08", "source_type": "incident"})
    assert all(p["source_type"] == "incident" for p in r.json()["results"])
    assert "alert" not in r.json()["counts_by_source_type"] or r.json()["results"][0]["source_type"] != "alert"
