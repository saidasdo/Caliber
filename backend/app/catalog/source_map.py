"""Source map (SPEC section 5.9): "which file, sheet and column feeds which table and which
KPI, and which key links them." This mirrors backend/app/ingest/readers/*.py and run.py; if
an ingestion reader changes, this list should change with it.
"""

JOIN_KEYS = [
    {
        "key": "Tag Number / Equipment Tag",
        "links": ["equipment.tag", "sensor_hourly.equipment_tag", "incidents.tag_number",
                  "param_limits.equipment_tag", "condition_weekly.equipment_tag"],
        "notes": "The equipment id. Only 5 of 380 incidents' tag_number values resolve to a "
                 "row in equipment (the 5 RCA-linked equipment); the rest are tracked by "
                 "tag_number as free text only.",
    },
    {
        "key": "AR No.",
        "links": ["equipment.linked_ar_no", "incidents.ar_no", "rca_reports.ar_no"],
        "notes": "Links an incident to its RCA report. 226 of 380 incidents have no AR No. "
                 "(DQ: see process flags), so Serial No is the incident primary key instead.",
    },
    {
        "key": "Serial No",
        "links": ["incidents.serial_no (primary key)"],
        "notes": "Used as the incident primary key because AR No. is frequently missing.",
    },
    {
        "key": "RCA id",
        "links": ["equipment.rca_id", "rca_reports.rca_id", "capa_actions.rca_id"],
        "notes": "1:1 with the 5 equipment; assigned at ingestion from the RCA deck filename.",
    },
]

SOURCE_MAP = [
    # --- Production Data -------------------------------------------------------------
    {
        "source_file": "Production Data - RCA{n}_{TAG}.xlsx", "sheet": "PI Tag",
        "column": "Name, Description, engunits, span, zero, typicalvalue, instrumenttag",
        "target_table": "pi_tag_meta", "target_column": "pi_name, description, unit, span, zero, typicalvalue, instrumenttag",
        "feeds": ["DQ1 (values outside PI Tag span)", "DQ2 (placeholder typicalvalue)"],
    },
    {
        "source_file": "Production Data - RCA{n}_{TAG}.xlsx", "sheet": "Sheet2",
        "column": "Timestamp, {TAG}_FEED/_DISP/_VIB/_TEMP/_AMP, PLANT_RATE, RUN_STATUS",
        "target_table": "sensor_hourly", "target_column": "ts, signal, value, run_status",
        "feeds": ["Availability gauge", "Production vs normal gauge", "Machine status timeline",
                  "Hourly trend + anomaly markers", "Backtest (first OFF hour, hourly anomaly lead time)"],
    },
    # --- Equipment Performance --------------------------------------------------------
    {
        "source_file": "Equipment Performance - RCA{n}_{TAG}.xlsx", "sheet": "Equipment Info (A:B)",
        "column": "Equipment Tag, Name, Type, Class, Plant/Unit, Discipline, Criticality, "
                  "Design Life, Monitoring Method, Linked RCA/AR No., Failure Date, Dominant Failure Mode",
        "target_table": "equipment",
        "target_column": "tag, name, eq_type, eq_class, plant_code, discipline, criticality, "
                          "design_life, monitoring_method, linked_ar_no, failure_date, dominant_failure_mode",
        "feeds": ["Identity strip", "Priority (class score)", "DQ12 (identical template metadata)"],
    },
    {
        "source_file": "Equipment Performance - RCA{n}_{TAG}.xlsx", "sheet": "Equipment Info (C:D)",
        "column": "Parameter, Alarm / Trip", "target_table": "param_limits",
        "target_column": "parameter, unit, alarm, trip, direction",
        "feeds": ["Diagnosis (level_worse conditions)", "Health margin gauge", "Weekly parameter alarm/trip lines",
                  "DQ5 (formula-like trip-week values)"],
    },
    {
        "source_file": "Equipment Performance - RCA{n}_{TAG}.xlsx", "sheet": "Condition History",
        "column": "Week, Date, 4 parameter columns, Health Status, Remark",
        "target_table": "condition_weekly, health_weekly",
        "target_column": "week, week_date, parameter, value, remark_display / health_status",
        "feeds": ["Diagnosis", "Health margin gauge", "Weekly small multiples", "Machine status timeline (weekly coloring)",
                  "Backtest (first ALARM/TRIP week)", "DQ4 (hourly vs weekly conflict)", "DQ5"],
    },
    {
        "source_file": "Equipment Performance - RCA{n}_{TAG}.xlsx", "sheet": "Performance Summary",
        "column": "Monitoring Period, Total Downtime, Availability, MTBF, MTTR, ALARM/TRIP/NORMAL "
                  "readings, PM Compliance, Production Loss, Estimated Loss",
        "target_table": "performance_summary", "target_column": "(1:1 with the sheet's KPI rows)",
        "feeds": ["Availability", "MTBF", "MTTR", "Downtime", "Production loss (t)", "Loss (USD)",
                  "Other KPIs list", "Backtest (downtime, loss)"],
    },
    # --- Incident Database --------------------------------------------------------------
    {
        "source_file": "Incident Database.xlsx", "sheet": "Incident Database (header row 3)",
        "column": "Serial No, MTO No., AR No., Plant, Tag Number, Eq. Class, Date of Occur., "
                  "Risk Case Title, Highest Impact, Pre-Risk, Risk Score, PIC, Overall Status, "
                  "Discipline, Eq. Type, Component, F Mechanism, Downtime, Act./Pot./Total Loss, "
                  "RCA Due Date, Month - Year",
        "target_table": "incidents", "target_column": "(1:1 with the sheet's columns, plus component_family/"
                        "mechanism_norm/eq_type_family normalized helper columns)",
        "feeds": ["Open incidents", "CAPA overdue rate", "Loss by plant", "Heatmap", "Follow-up pipeline",
                  "Similar incidents", "Problem Tank (incidents in progress)", "Process flags",
                  "DQ7, DQ8, DQ9, DQ10, DQ11"],
    },
    {
        "source_file": "Incident Database.xlsx", "sheet": "Dashboard",
        "column": "(whole sheet)", "target_table": None, "target_column": None,
        "feeds": ["Reference only, not ingested (SPEC section 2)"],
    },
    # --- RCA decks ------------------------------------------------------------------
    {
        "source_file": "RCA{n} - {TAG}_*.pptx", "sheet": "slide: AR Details & Problem Statement",
        "column": "problem statement text box", "target_table": "rca_reports", "target_column": "problem_statement",
        "feeds": ["Linked RCA summary"],
    },
    {
        "source_file": "RCA{n} - {TAG}_*.pptx", "sheet": "slide: Chronology of Events",
        "column": "date / event text pairs", "target_table": "rca_reports", "target_column": "chronology_json",
        "feeds": ["Linked RCA summary", "DQ6 (document vs data conflict)"],
    },
    {
        "source_file": "RCA{n} - {TAG}_*.pptx", "sheet": "slide: 4M + 1E Verification",
        "column": "ROOT CAUSE: text line", "target_table": "rca_reports", "target_column": "root_cause",
        "feeds": ["Linked RCA summary"],
    },
    {
        "source_file": "RCA{n} - {TAG}_*.pptx", "sheet": "slide: Corrective & Pro-Active Action (CAPAA)",
        "column": "RC/item code, action text, Plan Date, PIC, Status (geometry-reconstructed grid, section 2)",
        "target_table": "capa_actions, actions", "target_column": "action_category=corrective/pro_active, ...",
        "feeds": ["Suggested actions", "Problem Tank", "Action tracking (capa_preload)"],
    },
    {
        "source_file": "RCA{n} - {TAG}_*.pptx", "sheet": "slide: Preventive & Risk Analysis",
        "column": "Preventive Action / Risk Countermeasure / PM Schedule grids",
        "target_table": "capa_actions, actions", "target_column": "action_category=preventive/risk_countermeasure/pm_schedule, ...",
        "feeds": ["Action tracking (capa_preload)"],
    },
    {
        "source_file": "RCA{n} - {TAG}_*.pptx", "sheet": "slide: Downtime & Closure Summary",
        "column": "Downtime, Production Loss, Estimated Loss tiles", "target_table": "rca_reports",
        "target_column": "loss_summary_json",
        "feeds": ["DQ6 (cross-check against performance_summary)"],
    },
]
