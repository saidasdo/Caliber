"""Process flags (SPEC section 6): "real data, shown in a separate 'Follow-up health'
section, not as data errors." Computed relative to the replay date, same rule as everywhere
else in the app (section 4: "Incidents ... only count if dated on or before it").
"""

import sqlite3
from datetime import date

NEW_REGISTERED_STALE_DAYS = 90


def get_process_flags(conn: sqlite3.Connection, replay_date: str) -> dict:
    rca_process_total, rca_process_overdue = conn.execute(
        "SELECT COUNT(*), SUM(CASE WHEN rca_due_date IS NOT NULL AND rca_due_date < ? THEN 1 ELSE 0 END) "
        "FROM incidents WHERE overall_status = 'RCA PROCESS' AND date_of_occur <= ?",
        (replay_date, replay_date),
    ).fetchone()

    new_registered_total = conn.execute(
        "SELECT COUNT(*) FROM incidents WHERE overall_status = 'NEW REGISTERED' AND date_of_occur <= ?",
        (replay_date,),
    ).fetchone()[0]
    stale_rows = conn.execute(
        "SELECT date_of_occur FROM incidents WHERE overall_status = 'NEW REGISTERED' "
        "AND date_of_occur <= ?",
        (replay_date,),
    ).fetchall()
    today = date.fromisoformat(replay_date[:10])
    stale_dates = [
        d[0] for d in stale_rows if (today - date.fromisoformat(d[0][:10])).days > NEW_REGISTERED_STALE_DAYS
    ]
    stale_dates.sort()

    no_ar_total, no_ar_count = conn.execute(
        "SELECT COUNT(*), SUM(CASE WHEN ar_no IS NULL THEN 1 ELSE 0 END) "
        "FROM incidents WHERE date_of_occur <= ?",
        (replay_date,),
    ).fetchone()

    return {
        "replay_date": replay_date,
        "rca_process_overdue": {
            "count": rca_process_overdue or 0,
            "of_total": rca_process_total or 0,
            "description": f"RCA PROCESS items past their RCA Due Date, as of {replay_date}",
        },
        "new_registered_stale": {
            "count": len(stale_dates),
            "of_total": new_registered_total,
            "oldest_date": stale_dates[0] if stale_dates else None,
            "description": f"NEW REGISTERED items older than {NEW_REGISTERED_STALE_DAYS} days",
        },
        "incidents_without_ar_no": {
            "count": no_ar_count or 0,
            "of_total": no_ar_total or 0,
            "description": "Incidents with no AR No. (Serial No is the primary key instead, per SPEC section 2)",
        },
    }
