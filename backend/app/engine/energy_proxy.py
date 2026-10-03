"""Energy proxy (SPEC section 5.10, low priority, built last).

"No metered energy data exists. Daily sum of motor current per equipment as a 'Motor load
index', 7-day moving average forecast for the next 7 days. Always labeled 'Proxy derived
from motor current, not metered energy'."
"""

import sqlite3
import statistics
from datetime import date, timedelta

LABEL = "Proxy derived from motor current, not metered energy"
MOVING_AVERAGE_DAYS = 7
FORECAST_DAYS = 7


def get_energy_proxy(conn: sqlite3.Connection, tag: str) -> dict:
    rows = conn.execute(
        "SELECT substr(ts, 1, 10) AS day, SUM(value) AS daily_sum FROM sensor_hourly "
        "WHERE equipment_tag = ? AND signal = 'motor_current' AND value IS NOT NULL "
        "GROUP BY day ORDER BY day",
        (tag,),
    ).fetchall()

    if not rows:
        return {"label": LABEL, "history": [], "moving_average": [], "forecast": []}

    days = [r[0] for r in rows]
    daily_sums = [r[1] for r in rows]

    moving_average = []
    for i in range(len(daily_sums)):
        window = daily_sums[max(0, i - MOVING_AVERAGE_DAYS + 1) : i + 1]
        moving_average.append(round(statistics.mean(window), 2))

    # Forecast: the last 7-day moving average held flat for the next 7 days. Documented
    # assumption, not a real forecasting model, since the dataset has no seasonality to learn
    # from beyond this one 30-day window.
    last_value = moving_average[-1]
    last_day = date.fromisoformat(days[-1])
    forecast = [
        {"day": (last_day + timedelta(days=i)).isoformat(), "value": last_value}
        for i in range(1, FORECAST_DAYS + 1)
    ]

    return {
        "label": LABEL,
        "history": [{"day": d, "motor_load_index": round(v, 2)} for d, v in zip(days, daily_sums)],
        "moving_average": [{"day": d, "value": v} for d, v in zip(days, moving_average)],
        "forecast": forecast,
        "assumption": (
            f"Forecast is the final {MOVING_AVERAGE_DAYS}-day moving average held flat for the "
            f"next {FORECAST_DAYS} days, not a fitted model: the 30-day hourly window has no "
            "seasonality to learn a real trend from."
        ),
    }
