"""GET /api/data-quality, /api/process-flags (SPEC section 5.9 / section 6)."""

import sqlite3

from fastapi import APIRouter, Depends, Query

from app.db import get_connection, rows_to_dicts
from app.engine.process_flags import get_process_flags
from app.engine.replay import DEFAULT_REPLAY_DATE

router = APIRouter()

# Weights are not specified in SPEC; documented here as an assumption pending product feedback.
SEVERITY_WEIGHT = {"Error": 5, "Warning": 2, "Info": 1}


@router.get("/data-quality")
def get_data_quality(conn: sqlite3.Connection = Depends(get_connection)):
    issues = rows_to_dicts(conn.execute("SELECT * FROM dq_issues ORDER BY dq_id").fetchall())
    penalty = sum(SEVERITY_WEIGHT.get(i["severity"], 1) for i in issues if i["status"] == "Open")
    score = max(0, 100 - penalty)
    by_dq_id = {}
    for issue in issues:
        by_dq_id.setdefault(issue["dq_id"], []).append(issue)

    not_errors = rows_to_dicts(
        conn.execute("SELECT * FROM assumptions WHERE area = 'not_error' ORDER BY id").fetchall()
    )

    return {
        "score": score,
        "score_formula": "100 - sum(severity weight) over Open issues; Error=5, Warning=2, Info=1",
        "issue_count": len(issues),
        "issues": issues,
        "by_dq_id": by_dq_id,
        "not_errors": not_errors,
    }


@router.get("/process-flags")
def get_process_flags_endpoint(
    replay_date: str = Query(DEFAULT_REPLAY_DATE),
    conn: sqlite3.Connection = Depends(get_connection),
):
    """SPEC section 6: "Process flags (real data, shown in a separate 'Follow-up health'
    section, not as data errors)."""
    return get_process_flags(conn, replay_date)
