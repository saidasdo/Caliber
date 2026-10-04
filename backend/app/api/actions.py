"""Actions: list, approve, reject, status update (SPEC section 5.7), plus the phase 10
role-gated flow (propose, approve/reject proposal, close, escalate, comment)."""

import json
import sqlite3
from datetime import date, datetime

from fastapi import Header, APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.audit import write_audit_log as _write_audit_log
from app.db import get_connection, rows_to_dicts
from app.engine.replay import DEFAULT_REPLAY_DATE
from app.scope import RoleScope, get_role_scope, require_role

router = APIRouter()

OPEN_STATUSES = ("Open", "In progress")


def _overdue_days(due_date: str | None, status: str, replay_date: str) -> int | None:
    """SPEC 5.7: "overdue days relative to the replay date." Only open/in-progress actions
    with a due date in the past (relative to the replay clock, not wall-clock today) count."""
    if not due_date or status not in OPEN_STATUSES:
        return None
    due = date.fromisoformat(due_date[:10])
    today = date.fromisoformat(replay_date[:10])
    delta = (today - due).days
    return delta if delta > 0 else None


@router.get("/actions")
def list_actions(
    status: str | None = Query(None),
    equipment_tag: str | None = Query(None),
    source: str | None = Query(None),
    plant_code: str | None = Query(None),
    replay_date: str = Query(DEFAULT_REPLAY_DATE),
    conn: sqlite3.Connection = Depends(get_connection),
):
    join = " JOIN equipment ON equipment.tag = actions.equipment_tag" if plant_code else ""
    sql = f"SELECT actions.* FROM actions{join} WHERE 1=1"
    # Replay rule: only actions known on or before the replay date (legacy rows with no date stay).
    sql += " AND (actions.as_of_date IS NULL OR actions.as_of_date <= ?)"
    params: list = [replay_date]
    if plant_code:
        sql += " AND equipment.plant_code = ?"
        params.append(plant_code)
    if status:
        sql += " AND actions.status = ?"
        params.append(status)
    if equipment_tag:
        sql += " AND actions.equipment_tag = ?"
        params.append(equipment_tag)
    if source:
        sql += " AND actions.source = ?"
        params.append(source)
    sql += " ORDER BY actions.due_date IS NULL, actions.due_date"
    rows = rows_to_dicts(conn.execute(sql, params).fetchall())
    for row in rows:
        row["overdue_days"] = _overdue_days(row["due_date"], row["status"], replay_date)

    if plant_code:
        counts = dict(
            conn.execute(
                "SELECT actions.status, COUNT(*) FROM actions "
                "JOIN equipment ON equipment.tag = actions.equipment_tag "
                "WHERE equipment.plant_code = ? AND (actions.as_of_date IS NULL OR actions.as_of_date <= ?) "
                "GROUP BY actions.status",
                (plant_code, replay_date),
            ).fetchall()
        )
    else:
        counts = dict(
            conn.execute(
                "SELECT status, COUNT(*) FROM actions "
                "WHERE as_of_date IS NULL OR as_of_date <= ? GROUP BY status",
                (replay_date,),
            ).fetchall()
        )
    return {"results": rows, "counts_by_status": counts}


class ApproveRequest(BaseModel):
    equipment_tag: str
    action_text: str
    pic: str
    due_date: str
    source_capa_action_id: int | None = None
    actor_role: str | None = None


@router.post("/actions/approve")
def approve_suggested_action(body: ApproveRequest, conn: sqlite3.Connection = Depends(get_connection), x_replay_date: str | None = Header(None)):
    """SPEC 5.7: a suggested action "only becomes a tracked action after an engineer clicks
    Approve (with PIC and due date)." Every approve is written to audit_log."""
    problem = conn.execute(
        "SELECT id FROM problems WHERE source_type = 'rca' AND source_ref = ?",
        (body.equipment_tag,),
    ).fetchone()

    now = datetime.utcnow().isoformat()
    cur = conn.execute(
        "INSERT INTO actions (problem_id, equipment_tag, source, capa_action_id, action_text, "
        "pic, due_date, status, approved_at, created_at) VALUES (?, ?, 'diagnosis_suggestion', "
        "?, ?, ?, ?, 'Open', ?, ?)",
        (
            problem[0] if problem else None,
            body.equipment_tag,
            body.source_capa_action_id,
            body.action_text,
            body.pic,
            body.due_date,
            now,
            now,
        ),
    )
    _write_audit_log(
        conn,
        "approve_suggested_action",
        {"equipment_tag": body.equipment_tag, "action_text": body.action_text, "pic": body.pic, "due_date": body.due_date},
        body.actor_role,
    )
    conn.commit()

    conn.execute("UPDATE actions SET as_of_date = ? WHERE id = ?", (x_replay_date, cur.lastrowid))
    conn.commit()
    row = conn.execute("SELECT * FROM actions WHERE id = ?", (cur.lastrowid,)).fetchone()
    return dict(row)


class RejectRequest(BaseModel):
    equipment_tag: str
    action_text: str
    reason: str
    source_capa_action_id: int | None = None
    actor_role: str | None = None


@router.post("/actions/reject")
def reject_suggested_action(body: RejectRequest, conn: sqlite3.Connection = Depends(get_connection), x_replay_date: str | None = Header(None)):
    """SPEC 5.7: "Reject needs a reason." Recorded as a Rejected action (so it stays visible
    and filterable in the dense table) rather than discarded, and logged to audit_log."""
    if not body.reason.strip():
        raise HTTPException(status_code=422, detail="Reject reason is required")

    problem = conn.execute(
        "SELECT id FROM problems WHERE source_type = 'rca' AND source_ref = ?",
        (body.equipment_tag,),
    ).fetchone()

    now = datetime.utcnow().isoformat()
    cur = conn.execute(
        "INSERT INTO actions (problem_id, equipment_tag, source, capa_action_id, action_text, "
        "status, reject_reason, created_at) VALUES (?, ?, 'diagnosis_suggestion', ?, ?, "
        "'Rejected', ?, ?)",
        (
            problem[0] if problem else None,
            body.equipment_tag,
            body.source_capa_action_id,
            body.action_text,
            body.reason,
            now,
        ),
    )
    _write_audit_log(
        conn,
        "reject_suggested_action",
        {"equipment_tag": body.equipment_tag, "action_text": body.action_text, "reason": body.reason},
        body.actor_role,
    )
    conn.commit()

    conn.execute("UPDATE actions SET as_of_date = ? WHERE id = ?", (x_replay_date, cur.lastrowid))
    conn.commit()
    row = conn.execute("SELECT * FROM actions WHERE id = ?", (cur.lastrowid,)).fetchone()
    return dict(row)


class StatusUpdateRequest(BaseModel):
    status: str
    actor_role: str | None = None
    note: str | None = None


VALID_STATUSES = ("Open", "In progress", "Done", "Rejected")

# Phase 10: who may move an action into which status via this endpoint, enforced only when
# the caller sends X-Role (see app.scope.require_role) so every pre-phase-10 call site, which
# never did, keeps working exactly as before.
STATUS_ROLES = {
    "In progress": ("Engineer",),
    "Done": ("Engineer",),
    "Open": ("Engineer", "Plant manager"),
    "Rejected": ("Engineer", "Plant manager"),
}


@router.patch("/actions/{action_id}")
def update_action_status(
    action_id: int,
    body: StatusUpdateRequest,
    conn: sqlite3.Connection = Depends(get_connection),
    scope: RoleScope = Depends(get_role_scope),
):
    if body.status not in VALID_STATUSES:
        raise HTTPException(status_code=422, detail=f"status must be one of {VALID_STATUSES}")

    existing = conn.execute("SELECT * FROM actions WHERE id = ?", (action_id,)).fetchone()
    if existing is None:
        raise HTTPException(status_code=404, detail=f"No action with id {action_id}")

    if scope.role_header_sent:
        require_role(scope, *STATUS_ROLES.get(body.status, ("Executive", "Plant manager", "Engineer")))

    conn.execute(
        "UPDATE actions SET status = ?, progress_note = COALESCE(?, progress_note) WHERE id = ?",
        (body.status, body.note, action_id),
    )
    _write_audit_log(
        conn,
        "update_action_status",
        {"action_id": action_id, "old_status": existing["status"], "new_status": body.status, "note": body.note},
        body.actor_role or scope.role,
    )
    conn.commit()

    row = conn.execute("SELECT * FROM actions WHERE id = ?", (action_id,)).fetchone()
    return dict(row)


class ProposeRequest(BaseModel):
    equipment_tag: str
    action_text: str
    source_capa_action_id: int | None = None


@router.post("/actions/propose")
def propose_action(
    body: ProposeRequest,
    conn: sqlite3.Connection = Depends(get_connection),
    scope: RoleScope = Depends(get_role_scope),
    x_replay_date: str | None = Header(None),
):
    """Phase 10 action flow step 1b: engineer proposes an action from a suggestion (or a new
    one), with no PIC or due date yet; those are the plant manager's to assign on approval."""
    require_role(scope, "Engineer")
    problem = conn.execute(
        "SELECT id FROM problems WHERE source_type = 'rca' AND source_ref = ?",
        (body.equipment_tag,),
    ).fetchone()

    now = datetime.utcnow().isoformat()
    cur = conn.execute(
        "INSERT INTO actions (problem_id, equipment_tag, source, capa_action_id, action_text, "
        "status, proposed_by_role, created_at) VALUES (?, ?, 'diagnosis_suggestion', ?, ?, "
        "'Proposed', ?, ?)",
        (
            problem[0] if problem else None,
            body.equipment_tag,
            body.source_capa_action_id,
            body.action_text,
            scope.role,
            now,
        ),
    )
    _write_audit_log(
        conn,
        "propose_action",
        {"action_id": cur.lastrowid, "equipment_tag": body.equipment_tag, "action_text": body.action_text},
        scope.role,
    )
    conn.commit()
    conn.execute("UPDATE actions SET as_of_date = ? WHERE id = ?", (x_replay_date, cur.lastrowid))
    conn.commit()
    return dict(conn.execute("SELECT * FROM actions WHERE id = ?", (cur.lastrowid,)).fetchone())


class ApproveProposalRequest(BaseModel):
    pic: str
    due_date: str


@router.post("/actions/{action_id}/approve-proposal")
def approve_proposal(
    action_id: int,
    body: ApproveProposalRequest,
    conn: sqlite3.Connection = Depends(get_connection),
    scope: RoleScope = Depends(get_role_scope),
):
    """Phase 10 action flow step 2: plant manager approves a proposed action, assigning PIC
    and due date. Proposed -> Open."""
    require_role(scope, "Plant manager")
    existing = _get_action_or_404(conn, action_id)
    if existing["status"] != "Proposed":
        raise HTTPException(status_code=400, detail=f"Action {action_id} is not Proposed (status: {existing['status']})")

    now = datetime.utcnow().isoformat()
    conn.execute(
        "UPDATE actions SET status = 'Open', pic = ?, due_date = ?, approved_by_role = ?, approved_at = ? "
        "WHERE id = ?",
        (body.pic, body.due_date, scope.role, now, action_id),
    )
    _write_audit_log(
        conn, "approve_proposal", {"action_id": action_id, "pic": body.pic, "due_date": body.due_date}, scope.role
    )
    conn.commit()
    return dict(conn.execute("SELECT * FROM actions WHERE id = ?", (action_id,)).fetchone())


class RejectProposalRequest(BaseModel):
    reason: str


@router.post("/actions/{action_id}/reject-proposal")
def reject_proposal(
    action_id: int,
    body: RejectProposalRequest,
    conn: sqlite3.Connection = Depends(get_connection),
    scope: RoleScope = Depends(get_role_scope),
):
    require_role(scope, "Plant manager")
    if not body.reason.strip():
        raise HTTPException(status_code=422, detail="Reject reason is required")
    existing = _get_action_or_404(conn, action_id)
    if existing["status"] != "Proposed":
        raise HTTPException(status_code=400, detail=f"Action {action_id} is not Proposed (status: {existing['status']})")

    conn.execute(
        "UPDATE actions SET status = 'Rejected', reject_reason = ? WHERE id = ?",
        (body.reason, action_id),
    )
    _write_audit_log(conn, "reject_proposal", {"action_id": action_id, "reason": body.reason}, scope.role)
    conn.commit()
    return dict(conn.execute("SELECT * FROM actions WHERE id = ?", (action_id,)).fetchone())


@router.post("/actions/{action_id}/close")
def close_action(
    action_id: int,
    conn: sqlite3.Connection = Depends(get_connection),
    scope: RoleScope = Depends(get_role_scope),
):
    """Phase 10 action flow step 4: plant manager closes a Done action."""
    require_role(scope, "Plant manager")
    existing = _get_action_or_404(conn, action_id)
    if existing["status"] != "Done":
        raise HTTPException(status_code=400, detail=f"Action {action_id} is not Done (status: {existing['status']})")

    now = datetime.utcnow().isoformat()
    conn.execute(
        "UPDATE actions SET status = 'Closed', closed_by_role = ?, closed_at = ? WHERE id = ?",
        (scope.role, now, action_id),
    )
    _write_audit_log(conn, "close_action", {"action_id": action_id}, scope.role)
    conn.commit()
    return dict(conn.execute("SELECT * FROM actions WHERE id = ?", (action_id,)).fetchone())


class EscalateRequest(BaseModel):
    comment: str | None = None
    replay_date: str = DEFAULT_REPLAY_DATE


@router.post("/actions/{action_id}/escalate")
def escalate_action(
    action_id: int,
    body: EscalateRequest,
    conn: sqlite3.Connection = Depends(get_connection),
    scope: RoleScope = Depends(get_role_scope),
):
    """Phase 10 action flow step 5: executive escalates an overdue action; escalated items
    surface at the top of the plant manager's page."""
    require_role(scope, "Executive")
    existing = _get_action_or_404(conn, action_id)
    overdue = _overdue_days(existing["due_date"], existing["status"], body.replay_date)
    if not overdue:
        raise HTTPException(status_code=400, detail=f"Action {action_id} is not overdue")

    conn.execute("UPDATE actions SET escalated = 1 WHERE id = ?", (action_id,))
    if body.comment and body.comment.strip():
        _add_comment(conn, action_id, body.comment, scope.role)
    _write_audit_log(conn, "escalate_action", {"action_id": action_id, "overdue_days": overdue}, scope.role)
    conn.commit()
    return dict(conn.execute("SELECT * FROM actions WHERE id = ?", (action_id,)).fetchone())


class CommentRequest(BaseModel):
    comment: str


@router.post("/actions/{action_id}/comment")
def comment_on_action(
    action_id: int,
    body: CommentRequest,
    conn: sqlite3.Connection = Depends(get_connection),
    scope: RoleScope = Depends(get_role_scope),
):
    # Anyone on the action can comment (the comment thread is shared by all three roles).
    require_role(scope, "Executive", "Plant manager", "Engineer")
    if not body.comment.strip():
        raise HTTPException(status_code=422, detail="Comment cannot be blank")
    _get_action_or_404(conn, action_id)
    comment_id = _add_comment(conn, action_id, body.comment, scope.role)
    conn.commit()
    return dict(conn.execute("SELECT * FROM action_comments WHERE id = ?", (comment_id,)).fetchone())


@router.get("/actions/{action_id}/comments")
def list_comments(action_id: int, conn: sqlite3.Connection = Depends(get_connection)):
    rows = conn.execute(
        "SELECT * FROM action_comments WHERE action_id = ? ORDER BY ts", (action_id,)
    ).fetchall()
    return {"results": rows_to_dicts(rows)}


@router.get("/actions/{action_id}/history")
def action_history(action_id: int, conn: sqlite3.Connection = Depends(get_connection)):
    """Everything that happened to one action, oldest first: its audit_log entries (proposal, approval,
    status changes, escalation, closing) and its comments, merged by time."""
    _get_action_or_404(conn, action_id)
    events = [
        {
            "ts": ts,
            "actor_role": actor_role,
            "kind": "event",
            "event": action_type,
            "detail": json.loads(detail_json or "{}"),
        }
        for ts, actor_role, action_type, detail_json in conn.execute(
            "SELECT ts, actor_role, action_type, detail_json FROM audit_log "
            "WHERE json_extract(detail_json, '$.action_id') = ? ORDER BY ts, id",
            (action_id,),
        ).fetchall()
    ]
    events += [
        {"ts": ts, "actor_role": actor_role, "kind": "comment", "event": "comment", "detail": {"comment": comment}}
        for comment, actor_role, ts in conn.execute(
            "SELECT comment, actor_role, ts FROM action_comments WHERE action_id = ?", (action_id,)
        ).fetchall()
    ]
    events.sort(key=lambda e: e["ts"] or "")
    return {"action_id": action_id, "results": events}


def _get_action_or_404(conn: sqlite3.Connection, action_id: int):
    row = conn.execute("SELECT * FROM actions WHERE id = ?", (action_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail=f"No action with id {action_id}")
    return row


def _add_comment(conn: sqlite3.Connection, action_id: int, comment: str, actor_role: str) -> int:
    now = datetime.utcnow().isoformat()
    cur = conn.execute(
        "INSERT INTO action_comments (action_id, comment, actor_role, ts) VALUES (?, ?, ?, ?)",
        (action_id, comment, actor_role, now),
    )
    return cur.lastrowid
