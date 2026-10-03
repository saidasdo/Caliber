"""Shared audit_log writer (SPEC: "Everything goes to audit_log")."""

import json
import sqlite3
from datetime import datetime


def write_audit_log(conn: sqlite3.Connection, action_type: str, detail: dict, actor_role: str | None) -> None:
    conn.execute(
        "INSERT INTO audit_log (ts, actor_role, action_type, detail_json) VALUES (?, ?, ?, ?)",
        (datetime.utcnow().isoformat(), actor_role, action_type, json.dumps(detail)),
    )
