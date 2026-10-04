"""Estimated impact of an equipment's failure, as known on the replay date (SPEC 5.4 loss
exposure, and the executive impact card).

Replay rule: nothing shown for a replay date may use information dated after that date. So
this never reads the equipment's own RCA loss (performance_summary) or any incident dated on or
after the replay date. It is the median of the total loss of earlier incidents for similar
equipment, which is an estimate of what a failure like this has cost, never a known amount.
"""

import sqlite3
from statistics import median


def _median_loss(conn: sqlite3.Connection, replay_date: str, where: str, params: tuple) -> tuple[float | None, int]:
    rows = conn.execute(
        "SELECT total_loss_kusd FROM incidents "
        f"WHERE date_of_occur < ? AND total_loss_kusd IS NOT NULL AND {where}",
        (replay_date, *params),
    ).fetchall()
    values = [r[0] for r in rows]
    if not values:
        return None, 0
    return median(values), len(values)


def estimate_impact(conn: sqlite3.Connection, tag: str, replay_date: str) -> dict:
    equipment = conn.execute(
        "SELECT eq_type_family, eq_class FROM equipment WHERE tag = ?", (tag,)
    ).fetchone()
    if equipment is None:
        return {"value_kusd": None, "basis": None, "n_incidents": 0}
    eq_type_family, eq_class = equipment

    for basis, where, params in (
        ("eq_type_family", "eq_type_family = ?", (eq_type_family,)),
        ("eq_class", "eq_class = ?", (eq_class,)),
        ("all", "1 = 1", ()),
    ):
        value, count = _median_loss(conn, replay_date, where, params)
        if count:
            return {"value_kusd": round(value, 2), "basis": basis, "n_incidents": count}
    return {"value_kusd": None, "basis": None, "n_incidents": 0}
