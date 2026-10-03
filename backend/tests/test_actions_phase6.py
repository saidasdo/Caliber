"""Tests for CAPA preload, suggested actions, and the approve/reject/status-update flow
(SPEC section 5.7). Mutating tests run against the real ingested DB (there is no cheap way to
swap app.db's module-level DB_PATH per test here), so assertions avoid brittle absolute counts
where a test inserts rows; `npm run ingest` resets the DB to a clean state afterward.
"""

import sqlite3
import uuid

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


# ---------------------------------------------------------------------------
# CAPA preload (ingestion)
# ---------------------------------------------------------------------------


def test_capa_actions_are_preloaded_as_tracked_actions(conn):
    capa_count = conn.execute("SELECT COUNT(*) FROM capa_actions").fetchone()[0]
    preload_count = conn.execute(
        "SELECT COUNT(*) FROM actions WHERE source = 'capa_preload'"
    ).fetchone()[0]
    assert preload_count == capa_count == 47


def test_capa_status_text_mapped_to_canonical_status_values(conn):
    rows = conn.execute("SELECT DISTINCT status FROM actions WHERE source = 'capa_preload'").fetchall()
    statuses = {r[0] for r in rows}
    assert statuses <= {"Open", "In progress", "Done", "Rejected"}
    # "Closed" in the source decks must map to "Done", never pass through verbatim.
    assert conn.execute(
        "SELECT COUNT(*) FROM actions WHERE source = 'capa_preload' AND status = 'Closed'"
    ).fetchone()[0] == 0


def test_preloaded_actions_link_back_to_their_rca_problem(conn):
    rows = conn.execute(
        "SELECT a.problem_id, p.source_ref, a.equipment_tag FROM actions a "
        "JOIN problems p ON p.id = a.problem_id WHERE a.source = 'capa_preload'"
    ).fetchall()
    assert len(rows) == 47
    assert all(r["source_ref"] == r["equipment_tag"] for r in rows)


# ---------------------------------------------------------------------------
# Suggested actions
# ---------------------------------------------------------------------------


def test_suggested_actions_come_from_the_matching_rca_corrective_capa():
    r = client.get("/api/equipment/KO-3201/suggested-actions", params={"replay_date": "2026-04-08"})
    body = r.json()
    assert body["confidence"] == "High"
    assert len(body["suggestions"]) > 0
    for s in body["suggestions"]:
        assert s["source"] == "rca_capa"
        assert s["source_capa_action_id"] is not None


def test_suggested_actions_empty_when_no_confident_diagnosis():
    # PU-2101B has already recovered by 2026-04-08 (see test_diagnosis.py); no hint, no
    # suggestions.
    r = client.get("/api/equipment/PU-2101B/suggested-actions", params={"replay_date": "2026-04-08"})
    body = r.json()
    assert body["confidence"] is None
    assert body["suggestions"] == []


# ---------------------------------------------------------------------------
# Approve / reject / status update
# ---------------------------------------------------------------------------


def _unique_text(label: str) -> str:
    return f"{label} [{uuid.uuid4().hex[:8]}]"


def test_approve_creates_a_tracked_open_action_and_audit_entry():
    action_text = _unique_text("Test approve action")
    r = client.post(
        "/api/actions/approve",
        json={
            "equipment_tag": "KO-3201",
            "action_text": action_text,
            "pic": "TEST-01",
            "due_date": "2026-05-01",
            "actor_role": "Engineer",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["source"] == "diagnosis_suggestion"
    assert body["status"] == "Open"
    assert body["pic"] == "TEST-01"
    assert body["approved_at"] is not None
    assert body["problem_id"] is not None  # linked to KO-3201's RCA problem

    audit = client.get("/api/audit-log", params={"action_type": "approve_suggested_action"}).json()["results"]
    assert any(action_text in e["detail_json"] for e in audit)


def test_reject_requires_a_non_blank_reason():
    r = client.post(
        "/api/actions/reject",
        json={"equipment_tag": "KO-3201", "action_text": _unique_text("x"), "reason": "   "},
    )
    assert r.status_code == 422


def test_reject_creates_a_rejected_action_with_reason_and_audit_entry():
    action_text = _unique_text("Test reject action")
    reason = "Duplicate of an existing PM item"
    r = client.post(
        "/api/actions/reject",
        json={"equipment_tag": "KO-3201", "action_text": action_text, "reason": reason},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "Rejected"
    assert body["reject_reason"] == reason
    assert body["pic"] is None
    assert body["due_date"] is None

    audit = client.get("/api/audit-log", params={"action_type": "reject_suggested_action"}).json()["results"]
    assert any(reason in e["detail_json"] for e in audit)


def test_rejected_action_is_visible_and_filterable_in_the_dense_table():
    action_text = _unique_text("Filterable reject test")
    client.post(
        "/api/actions/reject",
        json={"equipment_tag": "BL-5702", "action_text": action_text, "reason": "test"},
    )
    r = client.get("/api/actions", params={"status": "Rejected"})
    assert any(a["action_text"] == action_text for a in r.json()["results"])


def test_status_update_requires_valid_status():
    action_id = client.get("/api/actions", params={"equipment_tag": "KO-3201"}).json()["results"][0]["id"]
    r = client.patch(f"/api/actions/{action_id}", json={"status": "Not A Status"})
    assert r.status_code == 422


def test_status_update_unknown_action_is_404():
    r = client.patch("/api/actions/999999999", json={"status": "Done"})
    assert r.status_code == 404


def test_status_update_changes_status_and_logs_audit():
    approve = client.post(
        "/api/actions/approve",
        json={
            "equipment_tag": "HE-3301",
            "action_text": _unique_text("Test status update action"),
            "pic": "TEST-02",
            "due_date": "2026-06-01",
        },
    ).json()
    action_id = approve["id"]

    r = client.patch(f"/api/actions/{action_id}", json={"status": "In progress"})
    assert r.status_code == 200
    assert r.json()["status"] == "In progress"

    audit = client.get("/api/audit-log", params={"action_type": "update_action_status"}).json()["results"]
    assert any(f'"action_id": {action_id}' in e["detail_json"] for e in audit)


# ---------------------------------------------------------------------------
# Overdue days
# ---------------------------------------------------------------------------


def test_overdue_days_positive_when_past_due_and_open():
    approve = client.post(
        "/api/actions/approve",
        json={
            "equipment_tag": "PM-4405B",
            "action_text": _unique_text("Overdue test action"),
            "pic": "TEST-03",
            "due_date": "2026-01-01",
        },
    ).json()

    r = client.get("/api/actions", params={"equipment_tag": "PM-4405B", "replay_date": "2026-01-15"})
    row = next(a for a in r.json()["results"] if a["id"] == approve["id"])
    assert row["overdue_days"] == 14


def test_overdue_days_none_when_due_date_in_the_future():
    approve = client.post(
        "/api/actions/approve",
        json={
            "equipment_tag": "PM-4405B",
            "action_text": _unique_text("Not overdue test action"),
            "pic": "TEST-04",
            "due_date": "2026-12-31",
        },
    ).json()

    r = client.get("/api/actions", params={"equipment_tag": "PM-4405B", "replay_date": "2026-01-15"})
    row = next(a for a in r.json()["results"] if a["id"] == approve["id"])
    assert row["overdue_days"] is None


def test_overdue_days_none_once_done():
    action_text = _unique_text("Done action should not be overdue")
    approve = client.post(
        "/api/actions/approve",
        json={"equipment_tag": "BL-5702", "action_text": action_text, "pic": "TEST-05", "due_date": "2026-01-01"},
    ).json()
    client.patch(f"/api/actions/{approve['id']}", json={"status": "Done"})

    r = client.get("/api/actions", params={"equipment_tag": "BL-5702", "replay_date": "2026-06-01"})
    row = next(a for a in r.json()["results"] if a["id"] == approve["id"])
    assert row["status"] == "Done"
    assert row["overdue_days"] is None
