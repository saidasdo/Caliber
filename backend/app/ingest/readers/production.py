"""Read `Production Data - RCA{n}_{TAG}.xlsx`: PI Tag metadata + hourly Sheet2, normalized to long format."""

from dataclasses import dataclass

import pandas as pd

from app.config import SIGNAL_MAP
from app.ingest.transforms.normalize import dehyphenate


@dataclass
class ProductionData:
    tag: str
    pi_tags: pd.DataFrame       # Name, Description, digitalset, engunits, span, typicalvalue, zero, instrumenttag
    hourly_long: pd.DataFrame   # equipment_tag, ts, signal, value, run_status


def read_production_file(path, tag: str) -> ProductionData:
    pi_tags = pd.read_excel(path, sheet_name="PI Tag")
    hourly = pd.read_excel(path, sheet_name="Sheet2")

    prefix = dehyphenate(tag)
    rename = {f"{prefix}_{suffix}": name for suffix, name in SIGNAL_MAP.items()}
    hourly = hourly.rename(columns=rename)

    signal_cols = list(SIGNAL_MAP.values()) + ["plant_rate"]
    hourly = hourly.rename(columns={"PLANT_RATE": "plant_rate", "RUN_STATUS": "run_status"})

    long_rows = []
    for _, row in hourly.iterrows():
        ts = row["Timestamp"]
        run_status = row["run_status"]
        for signal in signal_cols:
            long_rows.append(
                {
                    "equipment_tag": tag,
                    "ts": str(ts),
                    "signal": signal,
                    "value": row[signal],
                    "run_status": run_status,
                }
            )
    hourly_long = pd.DataFrame(long_rows)

    return ProductionData(tag=tag, pi_tags=pi_tags, hourly_long=hourly_long)
