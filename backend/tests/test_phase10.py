"""Tests for phase 10: role-based views (money redaction, action-flow role enforcement,
diagnosis review, end-to-end flow, audit log).
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from app.config import DB_PATH
from app.main import app

pytestmark = pytest.mark.skipif(not DB_PATH.exists(), reason="run `npm run ingest` first")

client = TestClient(app)

MONEY_KEYS = {"loss_kusd", "total_loss_kusd", "estimated_loss_kusd", "pot_loss_kusd", "act_loss_kusd"}


def _find_money_keys(obj, path=""):
    """Recursively collect every money-shaped key found anywhere in a response body."""
    found = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in MONEY_KEYS:
                found.append(f"{path}.{k}")
            found += _find_money_keys(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            found += _find_money_keys(v, f"{path}[{i}]")
    return found


def _unique_text(label: str) -> str:
    return f"{label} [{uuid.uuid4().hex[:8]}]"


# ---------------------------------------------------------------------------
# Money redaction (SPEC 5.11 / phase 10 section 5)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    [
        "/api/overview?replay_date=2026-04-08",
        "/api/plants/ZCU?replay_date=2026-04-08",
        "/api/equipment/KO-3201?replay_date=2026-04-08",
        "/api/backtest",
    ],
)
def test_engineer_sees_no_money_in_any_response(path):
    r = client.get(path, headers={"X-Role": "Engineer"})
    assert r.status_code == 200
    assert _find_money_keys(r.json()) == []


def test_executive_sees_money_everywhere_money_exists():
    r = client.get("/api/overview?replay_date=2026-04-08", headers={"X-Role": "Executive"})
    assert "loss_kusd" in r.json()["kpi_band"]


def test_plant_manager_sees_money_only_for_own_plant_in_overview():
    r = client.get(
        "/api/overview?replay_date=2026-04-08",
        headers={"X-Role": "Plant manager", "X-Plant": "ZCU"},
    )
    body = r.json()
    assert "loss_kusd" not in body["kpi_band"]  # all-plant aggregate, not "their" plant
    by_plant = {row["plant_code"]: row for row in body["loss_by_plant"]}
    assert "loss_kusd" in by_plant["ZCU"]
    assert "loss_kusd" not in by_plant["ARP"]


def test_plant_manager_sees_money_for_own_plant_detail_but_not_other_plants_rows():
    own = client.get(
        "/api/plants/ZCU?replay_date=2026-04-08",
        headers={"X-Role": "Plant manager", "X-Plant": "ZCU"},
    )
    assert "loss_kusd" in own.json()["kpis"]

    other = client.get(
        "/api/plants/ARP?replay_date=2026-04-08",
        headers={"X-Role": "Plant manager", "X-Plant": "ZCU"},
    )
    assert "loss_kusd" not in other.json()["kpis"]


def test_missing_role_header_defaults_to_executive_unredacted():
    # No pre-phase-10 caller (including every earlier test module) ever sends X-Role; they
    # must keep seeing full data.
    r = client.get("/api/overview?replay_date=2026-04-08")
    assert "loss_kusd" in r.json()["kpi_band"]


# ---------------------------------------------------------------------------
# Diagnosis review (action flow step 1)
# ---------------------------------------------------------------------------


def test_diagnosis_confirm_requires_engineer_role():
    r = client.post(
        "/api/equipment/KO-3201/diagnosis-review",
        json={"status": "confirmed", "replay_date": "2026-04-08"},
        headers={"X-Role": "Plant manager"},
    )
    assert r.status_code == 403


def test_diagnosis_reject_requires_a_reason():
    r = client.post(
        "/api/equipment/KO-3201/diagnosis-review",
        json={"status": "rejected", "replay_date": "2026-04-08"},
        headers={"X-Role": "Engineer"},
    )
    assert r.status_code == 422


def test_diagnosis_confirm_is_recorded_and_fetchable():
    r = client.post(
        "/api/equipment/KO-3201/diagnosis-review",
        json={"status": "confirmed", "replay_date": "2026-04-08"},
        headers={"X-Role": "Engineer"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "confirmed"

    fetched = client.get("/api/equipment/KO-3201/diagnosis-review")
    assert fetched.json()["status"] == "confirmed"


# ---------------------------------------------------------------------------
# Full action flow, role by role (phase 10 section 4 and acceptance checks)
# ---------------------------------------------------------------------------


def test_full_action_flow_propose_approve_done_close():
    action_text = _unique_text("Phase 10 full flow action")

    # Plant manager cannot propose.
    forbidden = client.post(
        "/api/actions/propose",
        json={"equipment_tag": "KO-3201", "action_text": action_text},
        headers={"X-Role": "Plant manager"},
    )
    assert forbidden.status_code == 403

    # Engineer proposes.
    proposed = client.post(
        "/api/actions/propose",
        json={"equipment_tag": "KO-3201", "action_text": action_text},
        headers={"X-Role": "Engineer"},
    )
    assert proposed.status_code == 200
    body = proposed.json()
    assert body["status"] == "Proposed"
    assert body["pic"] is None
    action_id = body["id"]

    # Engineer cannot approve its own proposal.
    forbidden2 = client.post(
        f"/api/actions/{action_id}/approve-proposal",
        json={"pic": "ENG-01", "due_date": "2026-05-01"},
        headers={"X-Role": "Engineer"},
    )
    assert forbidden2.status_code == 403

    # Plant manager approves, assigning PIC and due date.
    approved = client.post(
        f"/api/actions/{action_id}/approve-proposal",
        json={"pic": "ENG-01", "due_date": "2026-05-01"},
        headers={"X-Role": "Plant manager"},
    )
    assert approved.status_code == 200
    approved_body = approved.json()
    assert approved_body["status"] == "Open"
    assert approved_body["pic"] == "ENG-01"

    # Plant manager cannot move it to In progress (that's the engineer's step).
    forbidden3 = client.patch(
        f"/api/actions/{action_id}",
        json={"status": "In progress"},
        headers={"X-Role": "Plant manager"},
    )
    assert forbidden3.status_code == 403

    # Engineer updates progress, then marks Done with a note.
    in_progress = client.patch(
        f"/api/actions/{action_id}",
        json={"status": "In progress"},
        headers={"X-Role": "Engineer"},
    )
    assert in_progress.status_code == 200
    done = client.patch(
        f"/api/actions/{action_id}",
        json={"status": "Done", "note": "Fixed, verified on next reading"},
        headers={"X-Role": "Engineer"},
    )
    assert done.status_code == 200
    assert done.json()["progress_note"] == "Fixed, verified on next reading"

    # Engineer cannot close.
    forbidden4 = client.post(f"/api/actions/{action_id}/close", headers={"X-Role": "Engineer"})
    assert forbidden4.status_code == 403

    # Plant manager closes.
    closed = client.post(f"/api/actions/{action_id}/close", headers={"X-Role": "Plant manager"})
    assert closed.status_code == 200
    assert closed.json()["status"] == "Closed"

    # Every step landed in the audit log.
    for action_type in ("propose_action", "approve_proposal", "update_action_status", "close_action"):
        entries = client.get("/api/audit-log", params={"action_type": action_type}).json()["results"]
        assert any(str(action_id) in e["detail_json"] for e in entries), action_type


def test_reject_proposal_requires_plant_manager_and_a_reason():
    proposed = client.post(
        "/api/actions/propose",
        json={"equipment_tag": "HE-3301", "action_text": _unique_text("Reject proposal test")},
        headers={"X-Role": "Engineer"},
    ).json()
    action_id = proposed["id"]

    wrong_role = client.post(
        f"/api/actions/{action_id}/reject-proposal",
        json={"reason": "not needed"},
        headers={"X-Role": "Engineer"},
    )
    assert wrong_role.status_code == 403

    blank_reason = client.post(
        f"/api/actions/{action_id}/reject-proposal",
        json={"reason": "   "},
        headers={"X-Role": "Plant manager"},
    )
    assert blank_reason.status_code == 422

    rejected = client.post(
        f"/api/actions/{action_id}/reject-proposal",
        json={"reason": "Duplicate of an existing item"},
        headers={"X-Role": "Plant manager"},
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "Rejected"


def test_escalate_requires_executive_and_an_overdue_action():
    proposed = client.post(
        "/api/actions/propose",
        json={"equipment_tag": "BL-5702", "action_text": _unique_text("Escalate test")},
        headers={"X-Role": "Engineer"},
    ).json()
    approved = client.post(
        f"/api/actions/{proposed['id']}/approve-proposal",
        json={"pic": "PM-01", "due_date": "2026-01-01"},
        headers={"X-Role": "Plant manager"},
    ).json()

    wrong_role = client.post(
        f"/api/actions/{approved['id']}/escalate",
        json={"replay_date": "2026-04-08"},
        headers={"X-Role": "Plant manager"},
    )
    assert wrong_role.status_code == 403

    not_overdue = client.post(
        f"/api/actions/{approved['id']}/escalate",
        json={"replay_date": "2025-01-01"},
        headers={"X-Role": "Executive"},
    )
    assert not_overdue.status_code == 400

    escalated = client.post(
        f"/api/actions/{approved['id']}/escalate",
        json={"replay_date": "2026-04-08", "comment": "please expedite"},
        headers={"X-Role": "Executive"},
    )
    assert escalated.status_code == 200
    assert escalated.json()["escalated"] == 1

    comments = client.get(f"/api/actions/{approved['id']}/comments").json()["results"]
    assert any(c["comment"] == "please expedite" for c in comments)


def test_comments_are_open_to_all_three_roles():
    # Comments are a shared thread on an action: every role can add one (the engineer and plant manager
    # use it while working an action; the executive's comment right is kept).
    proposed = client.post(
        "/api/actions/propose",
        json={"equipment_tag": "KO-3201", "action_text": _unique_text("Comment test")},
        headers={"X-Role": "Engineer"},
    ).json()
    for role in ["Engineer", "Plant manager", "Executive"]:
        ok = client.post(
            f"/api/actions/{proposed['id']}/comment",
            json={"comment": f"looks fine ({role})"},
            headers={"X-Role": role},
        )
        assert ok.status_code == 200, role


def test_action_history_merges_audit_events_and_comments():
    proposed = client.post(
        "/api/actions/propose",
        json={"equipment_tag": "KO-3201", "action_text": _unique_text("History test")},
        headers={"X-Role": "Engineer"},
    ).json()
    client.post(f"/api/actions/{proposed['id']}/comment", json={"comment": "first"}, headers={"X-Role": "Engineer"})
    client.patch(f"/api/actions/{proposed['id']}", json={"status": "In progress"}, headers={"X-Role": "Engineer"})
    r = client.get(f"/api/actions/{proposed['id']}/history").json()
    kinds = [e["kind"] for e in r["results"]]
    events = [e["event"] for e in r["results"] if e["kind"] == "event"]
    assert "propose_action" in events
    assert "update_action_status" in events
    assert "comment" in kinds
    ts = [e["ts"] for e in r["results"]]
    assert ts == sorted(ts)  # oldest first


def test_legacy_approve_endpoint_still_works_without_any_role_header():
    # The original phase 6 flow must keep working for callers that never adopted X-Role.
    r = client.post(
        "/api/actions/approve",
        json={
            "equipment_tag": "KO-3201",
            "action_text": _unique_text("Legacy approve still works"),
            "pic": "LEGACY-01",
            "due_date": "2026-05-01",
        },
    )
    assert r.status_code == 200
    assert r.json()["status"] == "Open"


def test_approve_proposal_on_non_proposed_action_is_400():
    # The legacy endpoint creates an action that starts at Open, not Proposed.
    legacy = client.post(
        "/api/actions/approve",
        json={
            "equipment_tag": "KO-3201",
            "action_text": _unique_text("Already open action"),
            "pic": "LEGACY-02",
            "due_date": "2026-05-01",
        },
    ).json()
    r = client.post(
        f"/api/actions/{legacy['id']}/approve-proposal",
        json={"pic": "X", "due_date": "2026-06-01"},
        headers={"X-Role": "Plant manager"},
    )
    assert r.status_code == 400
