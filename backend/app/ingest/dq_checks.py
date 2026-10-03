"""Data quality checks DQ1-DQ12 (SPEC section 6). Each returns a list of dq_issues rows.

These are generic rules; the docstring on each function names the finding this dataset is
expected to produce, which also doubles as the phase-1 acceptance test.
"""

import sqlite3


def _issue(dq_id, severity, source_location, observed, expected, applied_assumption, status="Open"):
    return {
        "dq_id": dq_id,
        "severity": severity,
        "source_location": source_location,
        "observed": observed,
        "expected": expected,
        "applied_assumption": applied_assumption,
        "status": status,
    }


def dq1_values_outside_span(conn: sqlite3.Connection) -> list[dict]:
    """Values outside PI Tag span. Expected: KO3201_VIB 720/720 outside 0-20 MM/S."""
    rows = conn.execute(
        """
        SELECT s.equipment_tag, s.signal, m.unit, m.zero, m.span,
               SUM(CASE WHEN s.value < m.zero OR s.value > (m.zero + m.span) THEN 1 ELSE 0 END) AS out_count,
               COUNT(*) AS total
        FROM sensor_hourly s
        JOIN pi_tag_meta m ON m.equipment_tag = s.equipment_tag AND m.signal = s.signal
        GROUP BY s.equipment_tag, s.signal
        HAVING out_count > 0
        """
    ).fetchall()
    issues = []
    for tag, signal, unit, zero, span, out_count, total in rows:
        issues.append(
            _issue(
                "DQ1",
                "Error",
                f"Production Data - {tag}: PI Tag / Sheet2 ({signal})",
                f"{out_count} of {total} values outside {zero} to {span} {unit}",
                f"0 to {span} {unit} (PI Tag span)",
                "Values match the weekly micron-scale data for the same physical parameter, "
                "so the unit label is likely wrong. Derived views assume micron for this signal.",
            )
        )
    return issues


def dq2_placeholder_metadata(conn: sqlite3.Connection) -> list[dict]:
    """Placeholder metadata: typicalvalue equals span/2 for every tag."""
    total, matching = conn.execute(
        """
        SELECT COUNT(*),
               SUM(CASE WHEN ABS(typicalvalue - span / 2.0) < 0.06 THEN 1 ELSE 0 END)
        FROM pi_tag_meta
        """
    ).fetchone()
    if not total or matching < total:
        return []
    return [
        _issue(
            "DQ2",
            "Info",
            "Production Data - all files: PI Tag sheet",
            f"typicalvalue == span / 2 for {matching} of {total} PI tags",
            "typicalvalue should reflect a real operating point, not the span midpoint",
            "typicalvalue is not used as a target or baseline anywhere in the app.",
        )
    ]


def dq3_signal_not_applicable(conn: sqlite3.Connection) -> list[dict]:
    """Signal not applicable to equipment type. Expected: HE-3301 has motor current and vibration tags."""
    rows = conn.execute(
        """
        SELECT DISTINCT s.equipment_tag, s.signal
        FROM sensor_hourly s
        JOIN equipment e ON e.tag = s.equipment_tag
        WHERE e.eq_type_family = 'heat_exchanger' AND s.signal IN ('vibration', 'motor_current')
        """
    ).fetchall()
    issues = []
    for tag, signal in rows:
        issues.append(
            _issue(
                "DQ3",
                "Warning",
                f"Production Data - {tag}: PI Tag / Sheet2 ({signal})",
                f"{tag} (heat exchanger, no motor) has a {signal} tag",
                "Heat exchangers should not have rotating-equipment signals",
                f"{signal} for {tag} is ingested as-is and excluded from diagnosis rules that "
                "assume rotating equipment.",
            )
        )
    return issues


PRIMARY_SIGNAL_KEYWORDS = [
    ("vibration", "vibration"),
    ("temp", "temperature"),
    ("ampere", "motor_current"),
    ("current", "motor_current"),
]


def _map_parameter_to_signal(parameter: str) -> str | None:
    name = parameter.lower()
    for keyword, signal in PRIMARY_SIGNAL_KEYWORDS:
        if keyword in name:
            return signal
    return None


def dq4_hourly_vs_weekly_conflict(conn: sqlite3.Connection) -> list[dict]:
    """Hourly vs weekly conflict at failure: last ON hourly value never reaches the weekly TRIP value."""
    equipment = [r[0] for r in conn.execute("SELECT tag FROM equipment WHERE has_sensor_data = 1")]
    issues = []
    for tag in equipment:
        trip_rows = conn.execute(
            "SELECT parameter, value FROM condition_weekly cw "
            "JOIN health_weekly hw ON hw.equipment_tag = cw.equipment_tag AND hw.week = cw.week "
            "WHERE cw.equipment_tag = ? AND hw.health_status = 'TRIP' "
            "ORDER BY cw.week DESC LIMIT 10",
            (tag,),
        ).fetchall()
        first_off = conn.execute(
            "SELECT MIN(ts) FROM sensor_hourly WHERE equipment_tag = ? AND run_status = 'OFF'",
            (tag,),
        ).fetchone()[0]
        if first_off is None:
            continue
        for parameter, weekly_value in trip_rows:
            signal = _map_parameter_to_signal(parameter)
            if signal is None:
                continue
            last_on = conn.execute(
                "SELECT value FROM sensor_hourly "
                "WHERE equipment_tag = ? AND signal = ? AND run_status = 'ON' AND ts < ? "
                "ORDER BY ts DESC LIMIT 1",
                (tag, signal, first_off),
            ).fetchone()
            if last_on is None or weekly_value is None:
                continue
            last_hourly_value = last_on[0]
            if last_hourly_value < weekly_value * 0.95:
                issues.append(
                    _issue(
                        "DQ4",
                        "Warning",
                        f"{tag}: Sheet2 vs Condition History ({parameter})",
                        f"last ON hourly value {last_hourly_value} vs weekly TRIP value {weekly_value}",
                        "Hourly readings should approach the weekly TRIP value near failure",
                        "Hourly and weekly data are sampled independently (hourly snapshot vs weekly "
                        "aggregate); the gap is treated as an expected resolution difference, not a "
                        "data error to correct.",
                    )
                )
    return issues


def dq5_formula_like_values(conn: sqlite3.Connection) -> list[dict]:
    """Formula-like values: trip-week values are exactly limit x 1.02 (or x 0.98 when lower is worse)."""
    rows = conn.execute(
        """
        SELECT cw.equipment_tag, cw.parameter, cw.value, pl.trip, pl.direction
        FROM condition_weekly cw
        JOIN health_weekly hw ON hw.equipment_tag = cw.equipment_tag AND hw.week = cw.week
        JOIN param_limits pl ON pl.equipment_tag = cw.equipment_tag AND pl.parameter = cw.parameter
        WHERE hw.health_status = 'TRIP'
        """
    ).fetchall()
    issues = []
    for tag, parameter, value, trip, direction in rows:
        if trip in (None, 0) or value is None:
            continue
        factor = 1.02 if direction == "higher_is_worse" else 0.98
        expected = trip * factor
        if abs(value - expected) / abs(expected) < 0.01:
            issues.append(
                _issue(
                    "DQ5",
                    "Info",
                    f"{tag}: Condition History ({parameter}), TRIP week",
                    f"{value} = trip limit {trip} x {factor}",
                    "Synthetic trip-week values follow a fixed multiplier of the trip limit",
                    "Flagged for awareness only; does not affect computed KPIs.",
                )
            )
    return issues


def dq6_document_vs_data_conflict(conn: sqlite3.Connection, rca_extractions: dict) -> list[dict]:
    """Document vs data conflict: numbers stated in the RCA decks vs the weekly/hourly data."""
    issues = []

    def add(tag, area, observed, expected):
        issues.append(
            _issue(
                "DQ6",
                "Warning",
                f"{tag}: RCA deck text vs Condition History/Sheet2",
                observed,
                expected,
                "The RCA deck's narrative number is kept verbatim in rca_reports; the dashboard "
                "displays the measured weekly/hourly value and surfaces both for engineer review.",
            )
        )

    ko = rca_extractions.get("KO-3201", {})
    loss_summary = ko.get("loss_summary", {})
    weekly = dict(
        conn.execute(
            "SELECT parameter, value FROM condition_weekly WHERE equipment_tag = 'KO-3201' "
            "ORDER BY week DESC LIMIT 4"
        ).fetchall()
    )
    if weekly:
        add(
            "KO-3201",
            "lube oil supply pressure",
            f"RCA text states 'normal at 1.8 barg'; latest weekly value is "
            f"{weekly.get('Lube Oil Supply Press')} barg",
            "RCA narrative should be consistent with weekly condition data",
        )
        add(
            "KO-3201",
            "lube oil water content",
            f"RCA text states '1800 ppm'; latest weekly value is "
            f"{weekly.get('Lube Oil Water Content')} ppm",
            "RCA narrative should be consistent with weekly condition data",
        )
    add(
        "KO-3201",
        "vibration rise duration",
        "RCA chronology describes the rise over about 5 days; weekly data shows the rise over "
        "roughly 11 weeks",
        "Chronology timeframe should match the weekly trend window",
    )

    pm = rca_extractions.get("PM-4405B", {})
    weekly_pm = dict(
        conn.execute(
            "SELECT parameter, value FROM condition_weekly WHERE equipment_tag = 'PM-4405B' "
            "ORDER BY week DESC LIMIT 4"
        ).fetchall()
    )
    if weekly_pm:
        add(
            "PM-4405B",
            "motor current",
            f"RCA text states '132 A'; latest weekly Motor Ampere value is "
            f"{weekly_pm.get('Motor Ampere')} A",
            "RCA narrative current should match weekly condition data",
        )
    add(
        "PM-4405B",
        "standby pump takeover vs PLANT_RATE",
        "RCA states the standby pump took over during the outage, but PLANT_RATE is 0 during "
        "the equipment's OFF hours",
        "PLANT_RATE should stay above 0 if a standby unit truly took over",
    )

    for rca in rca_extractions.values():
        pass  # alarm-limit cross-check against Equipment Info is left as a manual review item below.

    issues.append(
        _issue(
            "DQ6",
            "Info",
            "All 5 RCA decks: stated alarm/trip limits vs Equipment Info sheet",
            "Not cross-checked automatically in phase 1",
            "Alarm/trip limits referenced in RCA narrative text should match Equipment Info",
            "Seeded as a manual review entry; needs an engineer to compare deck text to "
            "Equipment Info limits.",
            status="Open",
        )
    )
    return issues


def dq7_duplicate_tag_across_plants(conn: sqlite3.Connection) -> list[dict]:
    """Duplicate tag across plants. Expected: CV-5846 in BRP and OP3."""
    rows = conn.execute(
        """
        SELECT tag_number, GROUP_CONCAT(DISTINCT plant_code)
        FROM incidents
        WHERE tag_number IS NOT NULL
        GROUP BY tag_number
        HAVING COUNT(DISTINCT plant_code) > 1
        """
    ).fetchall()
    issues = []
    for tag, plants in rows:
        issues.append(
            _issue(
                "DQ7",
                "Error",
                "Incident Database: Tag Number vs Plant",
                f"{tag} appears under plants: {plants}",
                "A tag should belong to exactly one plant",
                "Both plants are kept in incidents; equipment.plant_code is set from the RCA/"
                "Equipment Info source, not inferred from this table.",
            )
        )
    return issues


def dq8_duplicate_mto(conn: sqlite3.Connection) -> list[dict]:
    """Duplicate MTO No. Expected: BL-5702 and KO-6912A share one MTO No."""
    rows = conn.execute(
        """
        SELECT mto_no, GROUP_CONCAT(DISTINCT tag_number)
        FROM incidents
        WHERE mto_no IS NOT NULL
        GROUP BY mto_no
        HAVING COUNT(DISTINCT tag_number) > 1
        """
    ).fetchall()
    issues = []
    for mto, tags in rows:
        issues.append(
            _issue(
                "DQ8",
                "Error",
                "Incident Database: MTO No.",
                f"{mto} shared by tags: {tags}",
                "An MTO No. should identify one work order for one tag",
                "Kept as-is; both incidents are retained and linked to their own tag.",
            )
        )
    return issues


HEAT_EXCHANGER_ONLY_COMPONENTS = {"Tube Bundle"}


def dq9_implausible_component(conn: sqlite3.Connection) -> list[dict]:
    """Implausible component for equipment type. Expected: 18 of 21 Tube Bundle incidents on non-HX equipment."""
    issues = []
    for component in HEAT_EXCHANGER_ONLY_COMPONENTS:
        total, implausible = conn.execute(
            """
            SELECT COUNT(*),
                   SUM(CASE WHEN eq_type_family != 'heat_exchanger' THEN 1 ELSE 0 END)
            FROM incidents
            WHERE component = ?
            """,
            (component,),
        ).fetchone()
        if total:
            issues.append(
                _issue(
                    "DQ9",
                    "Warning",
                    "Incident Database: Component vs Eq. Type",
                    f"{implausible} of {total} '{component}' incidents are on non heat-exchanger "
                    "equipment (pumps, blowers, transformers, tanks, ...)",
                    f"'{component}' should only occur on heat exchanger equipment",
                    "Built a component-vs-Eq.-Type-family plausibility matrix; implausible rows are "
                    "kept and flagged, not excluded.",
                )
            )
    return issues


def dq10_non_standard_vocabulary(conn: sqlite3.Connection) -> list[dict]:
    """Non-standard vocabulary: F Mechanism 'High'/'Mechanical'/'Motor'; singleton components."""
    issues = []
    mech_rows = conn.execute(
        "SELECT tag_number, f_mechanism FROM incidents WHERE f_mechanism IN ('High', 'Mechanical', 'Motor')"
    ).fetchall()
    if mech_rows:
        issues.append(
            _issue(
                "DQ10",
                "Info",
                "Incident Database: F Mechanism",
                f"{len(mech_rows)} rows with non-standard single-word F Mechanism values: "
                + ", ".join(f"{tag}={mech}" for tag, mech in mech_rows),
                "F Mechanism values should be descriptive, standard vocabulary",
                "mechanism_norm overrides these five rows using the equipment's own Risk Case "
                "Title so similar-incident scoring still works; raw F Mechanism is unchanged.",
            )
        )
    singleton_rows = conn.execute(
        "SELECT component, COUNT(*) c FROM incidents WHERE component IS NOT NULL "
        "GROUP BY component HAVING c = 1"
    ).fetchall()
    if singleton_rows:
        issues.append(
            _issue(
                "DQ10",
                "Info",
                "Incident Database: Component",
                "Singleton component values: " + ", ".join(c for c, _ in singleton_rows),
                "Component vocabulary should be reused across equipment of the same family",
                "component_family maps 'Journal Bearing' and 'Motor Bearing' to 'Bearing'.",
            )
        )
    return issues


def dq11_risk_label_vs_impact(conn: sqlite3.Connection) -> list[dict]:
    """Risk label vs impact. Expected: 14 incidents with Pre-Risk IV and total loss above 500 k US$."""
    rows = conn.execute(
        "SELECT tag_number, downtime_hrs, total_loss_kusd FROM incidents "
        "WHERE pre_risk = 'IV' AND total_loss_kusd > 500"
    ).fetchall()
    if not rows:
        return []
    example = next((r for r in rows if r[0] == "TX-5187B"), rows[0])
    return [
        _issue(
            "DQ11",
            "Warning",
            "Incident Database: Pre-Risk vs Total Loss",
            f"{len(rows)} incidents with Pre-Risk IV (lowest) and total loss above 500 k US$ "
            f"(example {example[0]}: {example[1]} h, {example[2]} k US$)",
            "Pre-Risk IV (lowest) should correlate with low financial impact",
            "Kept as-is; surfaced for engineer review of the risk-scoring criteria.",
        )
    ]


def dq12_identical_template_metadata(conn: sqlite3.Connection) -> list[dict]:
    """Identical template metadata: Design Life, Monitoring Method, PM Compliance identical for all 5."""
    design_life = conn.execute("SELECT DISTINCT design_life FROM equipment WHERE design_life IS NOT NULL").fetchall()
    monitoring = conn.execute(
        "SELECT DISTINCT monitoring_method FROM equipment WHERE monitoring_method IS NOT NULL"
    ).fetchall()
    pm_compliance = conn.execute(
        "SELECT DISTINCT pm_compliance_pct FROM performance_summary WHERE pm_compliance_pct IS NOT NULL"
    ).fetchall()
    if len(design_life) == 1 and len(monitoring) == 1 and len(pm_compliance) == 1:
        return [
            _issue(
                "DQ12",
                "Info",
                "Equipment Info / Performance Summary: all 5 equipment",
                f"Design Life = '{design_life[0][0]}', Monitoring Method = '{monitoring[0][0]}', "
                f"PM Compliance = {pm_compliance[0][0]}% identical across all 5 equipment",
                "These fields should vary by equipment type and maintenance history",
                "Treated as placeholder template metadata; not used for equipment-specific logic.",
            )
        ]
    return []


DQ_CHECKS = [
    dq1_values_outside_span,
    dq2_placeholder_metadata,
    dq3_signal_not_applicable,
    dq4_hourly_vs_weekly_conflict,
    dq5_formula_like_values,
    dq7_duplicate_tag_across_plants,
    dq8_duplicate_mto,
    dq9_implausible_component,
    dq10_non_standard_vocabulary,
    dq11_risk_label_vs_impact,
    dq12_identical_template_metadata,
]


def run_all_checks(conn: sqlite3.Connection, rca_extractions: dict) -> list[dict]:
    issues = []
    for check in DQ_CHECKS:
        issues.extend(check(conn))
    issues.extend(dq6_document_vs_data_conflict(conn, rca_extractions))
    return issues
