"""Phase 10 action flow step 1: engineer confirms or rejects the current rule-based diagnosis
before proposing an action. GET returns the latest review (or null if never reviewed); POST
records a new one. Reason is required to reject, same rule as action rejection (SPEC 5.7).
"""

import sqlite3
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.audit import write_audit_log
from app.db import get_connection
from app.engine.diagnosis import diagnose
from app.engine.replay import DEFAULT_REPLAY_DATE
from app.scope import RoleScope, get_role_scope, require_role

router = APIRouter()


@router.get("/equipment/{tag}/diagnosis-review")
def get_diagnosis_review(tag: str, conn: sqlite3.Connection = Depends(get_connection)):
    row = conn.execute(
        "SELECT * FROM diagnosis_reviews WHERE equipment_tag = ? ORDER BY ts DESC LIMIT 1",
        (tag,),
    ).fetchone()
    return dict(row) if row else None


class DiagnosisReviewRequest(BaseModel):
    status: str  # "confirmed" | "rejected"
    reason: str | None = None
    replay_date: str = DEFAULT_REPLAY_DATE


@router.post("/equipment/{tag}/diagnosis-review")
def post_diagnosis_review(
    tag: str,
    body: DiagnosisReviewRequest,
    conn: sqlite3.Connection = Depends(get_connection),
    scope: RoleScope = Depends(get_role_scope),
):
    require_role(scope, "Engineer")
    if body.status not in ("confirmed", "rejected"):
        raise HTTPException(status_code=422, detail="status must be 'confirmed' or 'rejected'")
    if body.status == "rejected" and not (body.reason or "").strip():
        raise HTTPException(status_code=422, detail="A reason is required to reject the diagnosis")

    current = diagnose(conn, tag, body.replay_date)
    now = datetime.utcnow().isoformat()
    conn.execute(
        "INSERT INTO diagnosis_reviews (equipment_tag, rule_name, status, reason, actor_role, ts) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (tag, current["rule_name"], body.status, body.reason, scope.role, now),
    )
    write_audit_log(
        conn,
        f"diagnosis_{body.status}",
        {"equipment_tag": tag, "rule_name": current["rule_name"], "reason": body.reason},
        scope.role,
    )
    conn.commit()

    row = conn.execute(
        "SELECT * FROM diagnosis_reviews WHERE equipment_tag = ? ORDER BY ts DESC LIMIT 1",
        (tag,),
    ).fetchone()
    return dict(row)
