"""Ingestion entrypoint: rebuild db/plantpulse.sqlite from data/raw/ and print the acceptance report.

Invoked by `npm run ingest` (see scripts/ingest.js).
"""

import json
import re
import sys
import traceback
from datetime import datetime

sys.path.insert(0, str(__file__.rsplit("backend", 1)[0] + "backend"))

from app.config import (  # noqa: E402
    DATA_SEED_DIR,
    EQUIPMENT_PERFORMANCE_DIR,
    INCIDENT_DB_PATH,
    PRODUCTION_DATA_DIR,
    RCA_EQUIPMENT,
    RCA_PPTX_DIR,
    ROOT_DIR,
    SENSOR_PLANTS,
)
from app.db import build_fresh_db, insert_many, publish_built_db  # noqa: E402
from app.ingest import dq_checks  # noqa: E402
from app.ingest.acceptance import print_report, run_acceptance_checks  # noqa: E402
from app.ingest.readers.equipment_performance import read_equipment_performance_file  # noqa: E402
from app.ingest.readers.incidents import read_incidents  # noqa: E402
from app.ingest.readers.production import read_production_file  # noqa: E402
from app.ingest.readers.rca_pptx import load_manual_seed, read_rca_deck  # noqa: E402
from app.ingest.transforms.limits import infer_direction, parse_alarm_trip  # noqa: E402
from app.ingest.transforms.normalize import (  # noqa: E402
    TAG_PREFIX_TO_EQ_TYPE,
    component_family,
    eq_type_family,
    mechanism_norm,
    tag_prefix,
)
from app.ingest.transforms.text_cleanup import display_text  # noqa: E402

PLANT_UNIT_RE = re.compile(r"^(.*?)\s*\(([A-Za-z0-9]+)\)\s*$")


def parse_plant_unit(raw: str) -> tuple[str, str]:
    match = PLANT_UNIT_RE.match(raw)
    if not match:
        raise ValueError(f"Cannot parse Plant / Unit: {raw!r}")
    return match.group(1).strip(), match.group(2).strip()


def parse_failure_date(raw: str) -> str:
    return datetime.strptime(raw, "%d-%b-%Y").strftime("%Y-%m-%d")


def ingest_equipment_and_sensors(conn):
    """Equipment Performance + Production Data for the 5 RCA equipment. Returns pi span info."""
    plants_seen = {}

    for entry in RCA_EQUIPMENT:
        tag, rca_id = entry["tag"], entry["rca_id"]

        eq_file = next(EQUIPMENT_PERFORMANCE_DIR.glob(f"*RCA{rca_id}*{tag}*.xlsx"))
        perf = read_equipment_performance_file(eq_file)
        info = perf.info
        plant_name, plant_code = parse_plant_unit(info["plant_unit_raw"])
        plants_seen[plant_code] = plant_name
        conn.execute(
            "INSERT OR IGNORE INTO plants (plant_code, plant_name, has_sensor_equipment) VALUES (?, ?, 1)",
            (plant_code, plant_name),
        )

        insert_many(
            conn,
            "equipment",
            [
                {
                    "tag": tag,
                    "name": info.get("name"),
                    "eq_type": info.get("eq_type_text"),
                    "eq_type_family": None,  # set below once we know the Incident Database Eq. Type code
                    "eq_class": info.get("eq_class"),
                    "plant_code": plant_code,
                    "discipline": info.get("discipline"),
                    "criticality": info.get("criticality"),
                    "design_life": info.get("design_life"),
                    "monitoring_method": info.get("monitoring_method"),
                    "linked_ar_no": info.get("linked_ar_no"),
                    "failure_date": parse_failure_date(info["failure_date_raw"]),
                    "dominant_failure_mode": info.get("dominant_failure_mode"),
                    "has_sensor_data": 1,
                    "rca_id": rca_id,
                }
            ],
        )

        limit_rows = []
        for limit in perf.limits:
            alarm, trip = parse_alarm_trip(limit["alarm_trip_raw"])
            direction = infer_direction(limit["parameter"], alarm, trip)
            limit_rows.append(
                {
                    "equipment_tag": tag,
                    "parameter": limit["parameter"],
                    "unit": limit["unit"],
                    "alarm": alarm,
                    "trip": trip,
                    "direction": direction,
                }
            )
        insert_many(conn, "param_limits", limit_rows)

        condition_rows, health_rows, seen_weeks = [], [], set()
        for row in perf.condition_weekly:
            condition_rows.append(
                {
                    "equipment_tag": tag,
                    "week": row["week"],
                    "week_date": row["date"],
                    "parameter": row["parameter"],
                    "unit": row["unit"],
                    "value": row["value"],
                    "remark_raw": row["remark"],
                    "remark_display": display_text(row["remark"]),
                }
            )
            if row["week"] not in seen_weeks:
                seen_weeks.add(row["week"])
                health_rows.append(
                    {
                        "equipment_tag": tag,
                        "week": row["week"],
                        "week_date": row["date"],
                        "health_status": row["health_status"],
                    }
                )
        insert_many(conn, "condition_weekly", condition_rows)
        insert_many(conn, "health_weekly", health_rows)

        ps = dict(perf.performance_summary)
        ps["equipment_tag"] = tag
        insert_many(conn, "performance_summary", [ps])

        prod_file = next(PRODUCTION_DATA_DIR.glob(f"*RCA{rca_id}*{tag}*.xlsx"))
        prod = read_production_file(prod_file, tag)

        pi_rows = []
        for _, pi_row in prod.pi_tags.iterrows():
            name = str(pi_row["Name"])
            signal = None
            if name.endswith("_FEED"):
                signal = "feed"
            elif name.endswith("_DISP"):
                signal = "discharge_pressure"
            elif name.endswith("_VIB"):
                signal = "vibration"
            elif name.endswith("_TEMP"):
                signal = "temperature"
            elif name.endswith("_AMP"):
                signal = "motor_current"
            elif name == "PLANT_RATE":
                signal = "plant_rate"
            else:
                continue  # RUN_STATUS: categorical, tracked via sensor_hourly.run_status instead
            pi_rows.append(
                {
                    "equipment_tag": tag,
                    "signal": signal,
                    "pi_name": name,
                    "description": pi_row["Description"],
                    "unit": pi_row["engunits"],
                    "span": pi_row["span"],
                    "zero": pi_row["zero"],
                    "typicalvalue": pi_row["typicalvalue"],
                    "instrumenttag": pi_row["instrumenttag"],
                }
            )
        insert_many(conn, "pi_tag_meta", pi_rows)
        insert_many(conn, "sensor_hourly", prod.hourly_long.to_dict("records"))

    return plants_seen


def ingest_incidents(conn, sensor_plant_names: dict):
    df = read_incidents(INCIDENT_DB_PATH)

    plant_codes = sorted(df["plant_code"].dropna().unique())
    conn.executemany(
        "INSERT OR IGNORE INTO plants (plant_code, plant_name, has_sensor_equipment) VALUES (?, ?, ?)",
        [
            (code, sensor_plant_names.get(code), 1 if code in SENSOR_PLANTS else 0)
            for code in plant_codes
        ],
    )

    incident_rows = []
    for _, row in df.iterrows():
        eq_type = row["eq_type"]
        resolved_eq_type = TAG_PREFIX_TO_EQ_TYPE.get(tag_prefix(row["tag_number"]) if row["tag_number"] else "", eq_type)
        incident_rows.append(
            {
                "serial_no": int(row["serial_no"]),
                "mto_no": row["mto_no"],
                "ar_no": row["ar_no"],
                "plant_code": row["plant_code"],
                "tag_number": row["tag_number"],
                "eq_class": row["eq_class"],
                "date_of_occur": row["date_of_occur"],
                "risk_case_title_raw": row["risk_case_title_raw"],
                "risk_case_title_display": display_text(row["risk_case_title_raw"]),
                "highest_impact": row["highest_impact"],
                "pre_risk": row["pre_risk"],
                "risk_score": row["risk_score"],
                "pic_rca": row["pic_rca"],
                "overall_status": row["overall_status"],
                "discipline": row["discipline"],
                "eq_type": eq_type,
                "eq_type_family": eq_type_family(eq_type),
                "component": row["component"],
                "component_family": component_family(row["component"]),
                "f_mechanism": row["f_mechanism"],
                "mechanism_norm": mechanism_norm(row["tag_number"], row["f_mechanism"]),
                "downtime_hrs": row["downtime_hrs"],
                "act_loss_kusd": row["act_loss_kusd"],
                "pot_loss_kusd": row["pot_loss_kusd"],
                "total_loss_kusd": row["total_loss_kusd"],
                "rca_due_date": row["rca_due_date"],
                "month_year": row["month_year"],
            }
        )
    insert_many(conn, "incidents", incident_rows)

    # Backfill equipment.eq_type_family from the Incident Database's Eq. Type for the 5 sensor equipment.
    for entry in RCA_EQUIPMENT:
        match = conn.execute(
            "SELECT eq_type, eq_type_family FROM incidents WHERE tag_number = ? LIMIT 1", (entry["tag"],)
        ).fetchone()
        if match:
            conn.execute(
                "UPDATE equipment SET eq_type_family = ? WHERE tag = ?", (match[1], entry["tag"])
            )


def ingest_rca_decks(conn):
    manual_seed = load_manual_seed(DATA_SEED_DIR / "rca_manual.json")
    manual_by_tag = {}
    for row in manual_seed:
        manual_by_tag.setdefault(row["equipment_tag"], []).append(row)

    extractions = {}
    for entry in RCA_EQUIPMENT:
        tag, rca_id = entry["tag"], entry["rca_id"]
        pptx_file = next(RCA_PPTX_DIR.glob(f"RCA{rca_id}*.pptx"))
        try:
            result = read_rca_deck(pptx_file, rca_id, tag)
        except Exception:
            print(f"  ! RCA deck extraction failed for {tag}, using manual seed only:")
            traceback.print_exc()
            result = {
                "problem_statement": None, "chronology": [], "four_p": [], "four_m_1e": [],
                "root_cause": None, "capa_actions": [], "loss_summary": {},
            }
        extractions[tag] = result

        ar_no = conn.execute("SELECT linked_ar_no FROM equipment WHERE tag = ?", (tag,)).fetchone()[0]
        insert_many(
            conn,
            "rca_reports",
            [
                {
                    "rca_id": rca_id,
                    "equipment_tag": tag,
                    "ar_no": ar_no,
                    "source_file": pptx_file.name,
                    "problem_statement": result["problem_statement"],
                    "chronology_json": json.dumps(result["chronology"]),
                    "root_cause": result["root_cause"],
                    "four_p_json": json.dumps(result["four_p"]),
                    "four_m_1e_json": json.dumps(result["four_m_1e"]),
                    "loss_summary_json": json.dumps(result["loss_summary"]),
                }
            ],
        )

        capa_rows = list(result["capa_actions"])
        if not capa_rows and tag in manual_by_tag:
            capa_rows = manual_by_tag[tag]
        insert_many(conn, "capa_actions", capa_rows)

    return extractions


def ingest_dq_issues(conn, rca_extractions):
    issues = dq_checks.run_all_checks(conn, rca_extractions)
    insert_many(conn, "dq_issues", issues)
    return issues


def ingest_assumptions(conn):
    from app import config

    now = datetime.utcnow().isoformat()
    insert_many(
        conn,
        "assumptions",
        [
            {
                "area": "replay / estimated impact",
                "assumption_text": "Estimated impact for a replay date is the median total loss of earlier incidents "
                "for the same eq_type_family (fallback: same eq_class, then all), dated before the replay date. "
                "It is never the equipment's own RCA loss.",
                "rationale": "Replay rule: nothing shown for a replay date may use information dated after it. "
                "The RCA loss includes failures after the replay date, so it is not used before the RCA is known.",
                "created_at": now,
            },
            {
                "area": "replay / similar incidents",
                "assumption_text": "Similar incidents are scored from the diagnosis for the replay date (failure mode "
                "mapped to eq_type_family, component_family, mechanism_norm; DIAGNOSIS_PROFILES), using only "
                "incidents dated before the replay date. Discipline is not scored.",
                "rationale": "The equipment's own later failure must never appear as its own similar case.",
                "created_at": now,
            },
            {
                "area": "replay / suggested actions",
                "assumption_text": "CAPA actions are suggested only from an RCA whose equipment failure date is before "
                "the replay date. Otherwise the generic action library (2 corrective, 2 preventive per rule) is used.",
                "rationale": "Before the failure date the RCA's actions were not yet known. The library is written from "
                "general maintenance practice, not copied from the RCA decks.",
                "created_at": now,
            },
            {
                "area": "replay / RCA evidence",
                "assumption_text": "An RCA is shown only on or after its failure date (equipment.failure_date <= replay "
                "date). Before that, the panel lists RCAs of similar past incidents dated before the replay date.",
                "rationale": "Replay rule (see estimated impact above).",
                "created_at": now,
            },
            {
                "area": "gauges / health margin",
                "assumption_text": "Health margin baseline = median of each parameter over the first 6 weeks of "
                "condition_weekly for the equipment. Margin = (trip - value) / (trip - baseline) for higher-is-worse, "
                "(value - trip) / (baseline - trip) for lower-is-worse. 100% = at baseline, 0% = at trip, negative = "
                "beyond trip. Bands: red below 0, amber from 0 to the highest alarm margin across the monitored parameters, green above.",
                "rationale": "The previous formula measured distance to trip relative to the trip limit, so a healthy "
                "machine could show a low margin. The baseline is fixed per parameter, so it does not move with the "
                "replay date.",
                "created_at": now,
            },
            {
                "area": "reliability / MTBF and MTTR",
                "assumption_text": "Failures = TRIP episodes in health_weekly on or before the replay date (consecutive "
                "TRIP weeks count as one). MTBF = observed hours (hourly record up to the replay date) / failures. "
                "MTTR = OFF hours (run_status) up to the replay date / failures. No failure yet: 'No failure in period'.",
                "rationale": "Computed only from data up to the replay date; performance_summary covers the whole "
                "monitoring period and so includes later failures.",
                "created_at": now,
            },
            {
                "area": "emission estimate (motor-driven equipment)",
                "assumption_text": "Per ON hour: kW = sqrt(3) x MOTOR_VOLTAGE_KV x motor current (A) x POWER_FACTOR; "
                f"kWh per day = sum over ON hours; kg CO2e = kWh x GRID_EMISSION_FACTOR_KG_PER_KWH. Current factors: "
                f"MOTOR_VOLTAGE_KV = {config.MOTOR_VOLTAGE_KV}, POWER_FACTOR = {config.POWER_FACTOR}, "
                f"GRID_EMISSION_FACTOR_KG_PER_KWH = {config.GRID_EMISSION_FACTOR_KG_PER_KWH}. "
                "THESE ARE PLACEHOLDERS: the team must replace them with official values (nameplate voltage, measured or "
                "nameplate power factor, official grid emission factor) before any figure is used.",
                "rationale": "No metered energy exists in the dataset. Heat exchangers (no motor drive) are excluded. "
                "Labeled as an estimate from motor current, not metered energy.",
                "created_at": now,
            },
            {
                "area": "display unit / KO-3201 vibration",
                "assumption_text": "The hourly chart and API response show KO-3201 vibration as 'µm (assumed, see DQ1)'. "
                "Raw values are unchanged.",
                "rationale": "DQ1: the PI Tag label says mm/s, but the values match the micron weekly data.",
                "created_at": now,
            },

            {
                "area": "sensor_hourly / KO-3201 vibration",
                "assumption_text": "KO3201_VIB is treated as micron, not mm/s as its PI Tag engunits label states.",
                "rationale": "DQ1: 720/720 hourly values fall outside the labeled 0-20 mm/s span, but match "
                "the weekly DE Radial Vibration data, which is in micron.",
                "created_at": datetime.utcnow().isoformat(),
            },
            {
                "area": "param_limits.direction",
                "assumption_text": "Direction is inferred per-parameter from alarm vs trip (alarm > trip => "
                "lower is worse), not hardcoded by parameter name.",
                "rationale": "SPEC section 2: seal flush flow, discharge pressure, lube oil supply pressure, "
                "heat duty and cold outlet temperature are lower-is-worse; the numeric comparison generalizes "
                "this without a hardcoded parameter list.",
                "created_at": datetime.utcnow().isoformat(),
            },
            {
                "area": "capa_actions extraction",
                "assumption_text": "RCA deck tables are reconstructed from shape geometry (row = shapes "
                "sharing an identical `top`, column = left-to-right order), not python-pptx table objects, "
                "because the decks draw tables as textbox/rectangle grids.",
                "rationale": "shape.has_table is False on every slide in every deck; the grid layout is "
                "consistent enough across decks to cluster reliably.",
                "created_at": datetime.utcnow().isoformat(),
            },
            {
                "area": "incidents.mechanism_norm",
                "assumption_text": "The five RCA incident rows' non-standard F Mechanism values (High, "
                "Mechanical, Motor) are normalized using each equipment's own Risk Case Title.",
                "rationale": "DQ10: these values are not descriptive; the Risk Case Title gives a specific, "
                "consistent term for similar-incident scoring while the raw value is kept unchanged.",
                "created_at": datetime.utcnow().isoformat(),
            },
        ],
    )
    ingest_not_error_notes(conn)


def ingest_not_error_notes(conn):
    """SPEC section 6, "Not errors (document in the KPI dictionary, do not flag)". Stored as
    assumptions (area='not_error') rather than literal kpi_dictionary rows, since none of the
    five describe a KPI; the Data Quality page reads them from here to show them clearly
    separated from the DQ1-DQ12 findings they are explicitly not part of.
    """
    now = datetime.utcnow().isoformat()
    insert_many(
        conn,
        "assumptions",
        [
            {
                "area": "not_error",
                "assumption_text": "Tag prefix differs from Eq. Type code but maps consistently: "
                "PM to EM, HE to HB, FN to FA, CV to VA, AZ to SX.",
                "rationale": "Documented naming convention, not a data error; incidents.eq_type_family "
                "is derived from this mapping.",
                "created_at": now,
            },
            {
                "area": "not_error",
                "assumption_text": "RCA Due Date is empty only for RISK CLOSED, RISK CANCELED and "
                "MONITORING RESULT incidents.",
                "rationale": "Those statuses have no pending RCA, so an empty due date is expected, "
                "not missing data.",
                "created_at": now,
            },
            {
                "area": "not_error",
                "assumption_text": "HE-3301 shows 13 OFF hours vs 12 h reported (same effect for "
                "PU-2101B: 18 rows vs 18.5 h).",
                "rationale": "Hourly resolution cannot represent a half-hour outage exactly; the RCA's "
                "own downtime figure (used for KPIs) is kept as the source of truth.",
                "created_at": now,
            },
            {
                "area": "not_error",
                "assumption_text": "Downtime 0 with loss above 0 occurs for repair cost without stopping.",
                "rationale": "A valid incident outcome: cost was incurred without a production stop.",
                "created_at": now,
            },
            {
                "area": "not_error",
                "assumption_text": "HE-3301 is OFF but still has about 12 T/H flow: a bypass rate cut, "
                "not a full stop.",
                "rationale": "RUN_STATUS OFF does not always mean zero production; never zero-fill this "
                "in derived views.",
                "created_at": now,
            },
        ],
    )


KPI_DICTIONARY = [
    {
        "kpi_name": "Availability",
        "definition": "Share of period hours the equipment was able to run.",
        "formula": "(Period Hours - Total Downtime Hours) / Period Hours",
        "source": "Equipment Performance: Performance Summary",
        "refresh_frequency": "Weekly",
        "owner": "Reliability Engineer",
    },
    {
        "kpi_name": "MTBF",
        "definition": "Mean time between failures, as of the replay date. Shown on the plant page equipment table. "
        "'No failure in period' until the first failure.",
        "formula": "Observed hours (hourly record up to replay date) / TRIP episodes up to replay date (health_weekly)",
        "source": "Computed: health_weekly, sensor_hourly (run_status). Not performance_summary, which includes later failures.",
        "refresh_frequency": "Live (per replay date)",
        "owner": "Reliability Engineer",
    },
    {
        "kpi_name": "MTTR",
        "definition": "Mean time to repair, as of the replay date: OFF hours per failure.",
        "formula": "OFF hours (run_status) up to replay date / TRIP episodes up to replay date",
        "source": "Computed: sensor_hourly (run_status), health_weekly. Not performance_summary.",
        "refresh_frequency": "Live (per replay date)",
        "owner": "Reliability Engineer",
    },
    {
        "kpi_name": "Downtime",
        "definition": "Hours the equipment was stopped due to the linked failure/incident.",
        "formula": "Sum of Downtime (hrs) for the equipment or scope in view",
        "source": "Equipment Performance: Performance Summary; Incident Database: Downtime (hrs)",
        "refresh_frequency": "Weekly",
        "owner": "Reliability Engineer",
    },
    {
        "kpi_name": "Production loss (t)",
        "definition": "Tons of product not made because of downtime, from the linked RCA.",
        "formula": "From RCA: Downtime x rate loss",
        "source": "Equipment Performance: Performance Summary (Production Loss)",
        "refresh_frequency": "Per incident",
        "owner": "Production Engineer",
    },
    {
        "kpi_name": "Loss (USD)",
        "definition": "Financial impact of an incident or period, actual plus potential.",
        "formula": "Total Loss (k US$) = Act. Loss + Pot. Loss",
        "source": "Incident Database: Act./Pot./Total Loss (k US$)",
        "refresh_frequency": "Per incident",
        "owner": "Plant Manager",
    },
    {
        "kpi_name": "Health status",
        "definition": "Weekly condition-monitoring status against alarm and trip limits.",
        "formula": "As recorded per week: NORMAL / ALARM / TRIP",
        "source": "Equipment Performance: Condition History",
        "refresh_frequency": "Weekly",
        "owner": "Reliability Engineer",
    },
    {
        "kpi_name": "Alarm lead time",
        "definition": "How far in advance a warning (weekly ALARM or hourly anomaly) preceded the TRIP/failure.",
        "formula": "First TRIP week - first ALARM week (weeks); first OFF hour - first hourly anomaly (hours)",
        "source": "Computed: health_weekly, sensor_hourly (section 5.8 backtest)",
        "refresh_frequency": "Per equipment, on demand",
        "owner": "Reliability Engineer",
    },
    {
        "kpi_name": "Open incidents",
        "definition": "Incidents not yet in a closed/canceled status, dated on or before the replay date.",
        "formula": "COUNT(*) WHERE overall_status NOT IN ('RISK CLOSED', 'RISK CANCELED')",
        "source": "Incident Database: Overall Status",
        "refresh_frequency": "Live (per replay date)",
        "owner": "Plant Manager",
    },
    {
        "kpi_name": "CAPA overdue rate",
        "definition": "Share of RCA PROCESS incidents past their RCA Due Date as of the replay date.",
        "formula": "COUNT(RCA PROCESS AND RCA Due Date < replay date) / COUNT(RCA PROCESS)",
        "source": "Incident Database: Overall Status, RCA Due Date",
        "refresh_frequency": "Live (per replay date)",
        "owner": "Reliability Engineer",
    },
    {
        "kpi_name": "Data quality score",
        "definition": "Composite score reflecting open data-quality findings (DQ1-DQ12).",
        "formula": "100 - sum(severity weight) over Open dq_issues; Error=5, Warning=2, Info=1",
        "source": "Computed: dq_issues",
        "refresh_frequency": "Per ingestion run",
        "owner": "Data Owner",
    },
    {
        "kpi_name": "Energy proxy",
        "definition": "Motor load index used as a stand-in for metered energy (none exists in this dataset).",
        "formula": "Daily sum of motor current per equipment; 7-day moving average forecast for the next 7 days",
        "source": "Production Data: Sheet2 (motor_current signal)",
        "refresh_frequency": "Daily",
        "owner": "Energy/Reliability Engineer",
    },
    {
        "kpi_name": "Health margin to trip",
        "definition": "How far the worst monitored parameter is from its trip limit, measured against its own healthy "
        "baseline (median of its first 6 weeks). 100% = at baseline, 0% = at trip, negative = beyond trip. "
        "Amber band ends at the highest alarm margin across parameters.",
        "formula": "Higher-is-worse: (trip - value) / (trip - baseline) x 100; lower-is-worse: (value - trip) / (baseline - trip) x 100",
        "source": "Condition History (condition_weekly, param_limits)",
        "refresh_frequency": "Weekly, per replay date",
        "owner": "Reliability Engineer",
    },
    {
        "kpi_name": "Estimated impact",
        "definition": "Estimate of what a failure like this has cost, from earlier similar incidents. Never a known amount.",
        "formula": "Median total_loss_kusd of incidents dated before the replay date, same eq_type_family (fallback eq_class, then all)",
        "source": "Incident Database: Total Loss, Eq. Type Family",
        "refresh_frequency": "Live (per replay date)",
        "owner": "Plant Manager",
    },
    {
        "kpi_name": "Emission estimate",
        "definition": "Estimated CO2e from motor-driven equipment, from motor current. An estimate, not metered energy.",
        "formula": "Per ON hour: sqrt(3) x MOTOR_VOLTAGE_KV x current x POWER_FACTOR (kWh); x GRID_EMISSION_FACTOR_KG_PER_KWH (kg CO2e). Factors are placeholders until set from official sources.",
        "source": "Production Data: motor_current; config factors",
        "refresh_frequency": "Daily",
        "owner": "HSE",
    },
]


def ingest_kpi_dictionary(conn):
    insert_many(conn, "kpi_dictionary", KPI_DICTIONARY)


# Open-ish statuses: not yet RISK CLOSED or RISK CANCELED (SPEC 5.7: "incidents in progress").
OPEN_INCIDENT_STATUSES = ("NEW REGISTERED", "RCA PROCESS", "CA/PA EXECUTION", "MONITORING RESULT")

# CAPA status text as written in the RCA decks -> the actions table's canonical status set.
# Rows with no status in the source deck (preventive, risk countermeasure, PM schedule items)
# default to "Open": they are pending maintenance/engineering items, not yet started or closed.
CAPA_STATUS_MAP = {"Open": "Open", "In Progress": "In progress", "Closed": "Done", None: "Open"}


def ingest_problems(conn):
    """Problem Tank backlog (SPEC 5.7): "from alerts, incidents in progress, RCA cases."
    Alerts are replay-date-dependent (computed live from health_weekly) and are not stored
    here; RCA cases and incidents-in-progress are real historical records and are stored.
    """
    rca_rows = []
    for row in conn.execute(
        "SELECT tag, plant_code, failure_date, dominant_failure_mode FROM equipment"
    ).fetchall():
        tag, plant_code, failure_date, failure_mode = row
        rca_rows.append(
            {
                "source_type": "rca",
                "source_ref": tag,
                "title": f"{tag}: {failure_mode}",
                "opened_date": failure_date,
                "status": "open",
                "priority_label": None,  # computed live from the priority engine, see api/problems.py
            }
        )
    insert_many(conn, "problems", rca_rows)

    placeholders = ", ".join("?" for _ in OPEN_INCIDENT_STATUSES)
    incident_rows = []
    for row in conn.execute(
        f"SELECT serial_no, risk_case_title_display, date_of_occur, pre_risk "
        f"FROM incidents WHERE overall_status IN ({placeholders})",
        OPEN_INCIDENT_STATUSES,
    ).fetchall():
        serial_no, title, date_of_occur, pre_risk = row
        incident_rows.append(
            {
                "source_type": "incident",
                "source_ref": str(serial_no),
                "title": title,
                "opened_date": date_of_occur,
                "status": "open",
                "priority_label": pre_risk,
            }
        )
    insert_many(conn, "problems", incident_rows)

    return len(rca_rows), len(incident_rows)


def _parse_capa_date(raw: str | None) -> str | None:
    if not raw:
        return None
    return parse_failure_date(raw)  # same "24-Apr-2026" format as Equipment Info's Failure Date


def ingest_capa_preload_actions(conn):
    """Pre-load CAPA actions from the five RCA decks as tracked actions (SPEC 5.7)."""
    problem_id_by_tag = dict(
        conn.execute("SELECT source_ref, id FROM problems WHERE source_type = 'rca'").fetchall()
    )
    created_at = datetime.utcnow().isoformat()
    # A CAPA action is known from its RCA's failure date (replay rule, see schema actions.as_of_date).
    failure_by_tag = dict(conn.execute("SELECT tag, failure_date FROM equipment").fetchall())

    rows = conn.execute(
        "SELECT id, rca_id, equipment_tag, action_text, plan_date, pic, status "
        "FROM capa_actions ORDER BY id"
    ).fetchall()

    action_rows = []
    for capa_id, rca_id, tag, action_text, plan_date, pic, status in rows:
        action_rows.append(
            {
                "problem_id": problem_id_by_tag.get(tag),
                "equipment_tag": tag,
                "source": "capa_preload",
                "capa_action_id": capa_id,
                "action_text": action_text,
                "pic": pic,
                "due_date": _parse_capa_date(plan_date),
                "status": CAPA_STATUS_MAP.get(status, "Open"),
                "created_at": created_at,
                "as_of_date": failure_by_tag.get(tag),
            }
        )
    insert_many(conn, "actions", action_rows)
    return len(action_rows)


def run_ingestion(verbose: bool = True):
    """Rebuild db/plantpulse.sqlite from data/raw/ and return the section 9 acceptance
    results. Shared by the `npm run ingest` CLI and the "Reset demo data" API endpoint
    (SPEC section 10 phase 9), so both go through exactly one ingestion code path.
    """

    def log(msg: str) -> None:
        if verbose:
            print(msg)

    log(f"Building database at {ROOT_DIR / 'db' / 'plantpulse.sqlite'} ...")
    conn = build_fresh_db()

    log("Ingesting Equipment Performance + Production Data (5 equipment)...")
    sensor_plant_names = ingest_equipment_and_sensors(conn)

    log("Ingesting Incident Database (380 rows)...")
    ingest_incidents(conn, sensor_plant_names)

    log("Extracting RCA decks (5 pptx files)...")
    rca_extractions = ingest_rca_decks(conn)

    log("Running data quality checks DQ1-DQ12...")
    issues = ingest_dq_issues(conn, rca_extractions)
    log(f"  {len(issues)} dq_issues rows inserted.")

    log("Recording ingestion assumptions...")
    ingest_assumptions(conn)

    log("Seeding KPI dictionary...")
    ingest_kpi_dictionary(conn)

    log("Building the Problem Tank backlog...")
    rca_count, incident_count = ingest_problems(conn)
    log(f"  {rca_count} RCA-case problems, {incident_count} incident-in-progress problems.")

    log("Pre-loading CAPA actions from the RCA decks as tracked actions...")
    action_count = ingest_capa_preload_actions(conn)
    log(f"  {action_count} actions inserted.")

    conn.commit()

    results = run_acceptance_checks(conn, ROOT_DIR)
    conn.close()
    publish_built_db()
    return results


def main():
    results = run_ingestion(verbose=True)
    all_pass = print_report(results)
    if not all_pass:
        sys.exit(1)


if __name__ == "__main__":
    main()
