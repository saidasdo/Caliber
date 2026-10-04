-- PlantPulse SQLite schema
-- Source of truth for db/plantpulse.sqlite. Rebuilt from scratch on every `npm run ingest`.

PRAGMA foreign_keys = ON;

CREATE TABLE plants (
    plant_code             TEXT PRIMARY KEY,
    plant_name             TEXT,
    has_sensor_equipment   INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE equipment (
    tag                     TEXT PRIMARY KEY,
    name                    TEXT NOT NULL,
    eq_type                 TEXT,
    eq_type_family          TEXT,
    eq_class                TEXT,
    plant_code              TEXT REFERENCES plants(plant_code),
    discipline              TEXT,
    criticality              TEXT,
    design_life             TEXT,
    monitoring_method       TEXT,
    linked_ar_no            TEXT,
    failure_date            TEXT,
    dominant_failure_mode   TEXT,
    has_sensor_data         INTEGER NOT NULL DEFAULT 0,
    rca_id                  INTEGER
);

CREATE TABLE param_limits (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    equipment_tag   TEXT NOT NULL REFERENCES equipment(tag),
    parameter       TEXT NOT NULL,
    unit            TEXT,
    alarm           REAL,
    trip            REAL,
    direction       TEXT NOT NULL CHECK (direction IN ('higher_is_worse', 'lower_is_worse'))
);

CREATE TABLE pi_tag_meta (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    equipment_tag   TEXT NOT NULL REFERENCES equipment(tag),
    signal          TEXT NOT NULL,
    pi_name         TEXT,
    description     TEXT,
    unit            TEXT,
    span            REAL,
    zero            REAL,
    typicalvalue    REAL,
    instrumenttag   TEXT,
    UNIQUE (equipment_tag, signal)
);

CREATE TABLE sensor_hourly (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    equipment_tag   TEXT NOT NULL REFERENCES equipment(tag),
    ts              TEXT NOT NULL,
    signal          TEXT NOT NULL,
    value           REAL,
    run_status      TEXT,
    UNIQUE (equipment_tag, ts, signal)
);
CREATE INDEX idx_sensor_hourly_tag_ts ON sensor_hourly(equipment_tag, ts);

CREATE TABLE condition_weekly (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    equipment_tag   TEXT NOT NULL REFERENCES equipment(tag),
    week            INTEGER NOT NULL,
    week_date       TEXT NOT NULL,
    parameter       TEXT NOT NULL,
    unit            TEXT,
    value           REAL,
    remark_raw      TEXT,
    remark_display  TEXT,
    UNIQUE (equipment_tag, week, parameter)
);
CREATE INDEX idx_condition_weekly_tag_week ON condition_weekly(equipment_tag, week);

CREATE TABLE health_weekly (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    equipment_tag   TEXT NOT NULL REFERENCES equipment(tag),
    week            INTEGER NOT NULL,
    week_date       TEXT NOT NULL,
    health_status   TEXT NOT NULL CHECK (health_status IN ('NORMAL', 'ALARM', 'TRIP')),
    UNIQUE (equipment_tag, week)
);

CREATE TABLE performance_summary (
    equipment_tag               TEXT PRIMARY KEY REFERENCES equipment(tag),
    monitoring_period_weeks     INTEGER,
    total_downtime_hours        REAL,
    period_hours                INTEGER,
    availability_pct            REAL,
    failures_period              INTEGER,
    mtbf_hours                  REAL,
    mttr_hours                  REAL,
    alarm_readings               INTEGER,
    trip_readings                INTEGER,
    normal_readings              INTEGER,
    pm_compliance_pct           REAL,
    production_loss_ton         REAL,
    estimated_loss_kusd         REAL
);

CREATE TABLE incidents (
    serial_no               INTEGER PRIMARY KEY,
    mto_no                  TEXT,
    ar_no                   TEXT,
    plant_code               TEXT REFERENCES plants(plant_code),
    tag_number               TEXT,
    eq_class                 TEXT,
    date_of_occur            TEXT,
    risk_case_title_raw      TEXT,
    risk_case_title_display  TEXT,
    highest_impact            TEXT,
    pre_risk                  TEXT,
    risk_score                INTEGER,
    pic_rca                   TEXT,
    overall_status             TEXT,
    discipline                 TEXT,
    eq_type                    TEXT,
    eq_type_family              TEXT,
    component                  TEXT,
    component_family            TEXT,
    f_mechanism                 TEXT,
    mechanism_norm               TEXT,
    downtime_hrs                 REAL,
    act_loss_kusd                REAL,
    pot_loss_kusd                 REAL,
    total_loss_kusd                REAL,
    rca_due_date                    TEXT,
    month_year                        TEXT
);
CREATE INDEX idx_incidents_tag ON incidents(tag_number);
CREATE INDEX idx_incidents_plant ON incidents(plant_code);

CREATE TABLE rca_reports (
    rca_id                INTEGER PRIMARY KEY,
    equipment_tag         TEXT NOT NULL REFERENCES equipment(tag),
    ar_no                 TEXT,
    source_file           TEXT,
    problem_statement     TEXT,
    chronology_json       TEXT,
    root_cause            TEXT,
    four_p_json           TEXT,
    four_m_1e_json        TEXT,
    loss_summary_json     TEXT
);

CREATE TABLE capa_actions (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    rca_id            INTEGER NOT NULL REFERENCES rca_reports(rca_id),
    equipment_tag     TEXT NOT NULL REFERENCES equipment(tag),
    action_category   TEXT NOT NULL CHECK (action_category IN
                        ('corrective', 'pro_active', 'preventive', 'risk_countermeasure', 'pm_schedule')),
    item_code         TEXT,
    action_text       TEXT NOT NULL,
    plan_date         TEXT,
    pic               TEXT,
    status            TEXT,
    extra_json        TEXT,
    source            TEXT NOT NULL DEFAULT 'pptx_extraction'
);

CREATE TABLE problems (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    source_type       TEXT NOT NULL CHECK (source_type IN ('alert', 'incident', 'rca')),
    source_ref        TEXT,
    title             TEXT NOT NULL,
    opened_date       TEXT,
    status            TEXT NOT NULL DEFAULT 'open',
    priority_label    TEXT
);

CREATE TABLE actions (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    problem_id        INTEGER REFERENCES problems(id),
    equipment_tag     TEXT,
    source            TEXT NOT NULL CHECK (source IN ('capa_preload', 'diagnosis_suggestion', 'manual')),
    capa_action_id    INTEGER REFERENCES capa_actions(id),
    action_text       TEXT NOT NULL,
    pic               TEXT,
    due_date          TEXT,
    -- Phase 10 role flow: Proposed (engineer) -> Open (plant manager approved, assigned PIC/
    -- due date) -> In progress / Done (engineer) -> Closed (plant manager). Rejected can
    -- happen straight from Proposed (plant manager) or, as before, as a direct reject of a
    -- suggestion that was never proposed. 'Open'/'In progress'/'Done'/'Rejected' are the
    -- original phase 6 values and existing rows/tests depend on them unchanged.
    status            TEXT NOT NULL DEFAULT 'Open' CHECK (status IN
                        ('Proposed', 'Open', 'In progress', 'Done', 'Closed', 'Rejected')),
    reject_reason     TEXT,
    progress_note     TEXT,
    proposed_by_role  TEXT,
    approved_by_role  TEXT,
    closed_by_role    TEXT,
    escalated         INTEGER NOT NULL DEFAULT 0,
    approved_at       TEXT,
    closed_at         TEXT,
    created_at        TEXT,
    -- Replay rule: the date the action became known (the RCA failure date for a CAPA preload,
    -- the replay date the user was on when they created it otherwise). Lists show an action
    -- only when this is on or before the replay date. NULL only for rows made before this column.
    as_of_date        TEXT
);

-- Phase 10: engineer's confirm/reject of the current rule-based diagnosis for an equipment,
-- ahead of proposing an action. Latest row per equipment_tag is the current state; re-review
-- (e.g. after the replay date moves and the diagnosis changes) just inserts a new row.
CREATE TABLE diagnosis_reviews (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    equipment_tag   TEXT NOT NULL,
    rule_name       TEXT,
    status          TEXT NOT NULL CHECK (status IN ('confirmed', 'rejected')),
    reason          TEXT,
    actor_role      TEXT,
    ts              TEXT NOT NULL
);
CREATE INDEX idx_diagnosis_reviews_tag ON diagnosis_reviews(equipment_tag);

-- Phase 10: Executive comments on an action (their one write right besides Escalate).
CREATE TABLE action_comments (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    action_id   INTEGER NOT NULL REFERENCES actions(id),
    comment     TEXT NOT NULL,
    actor_role  TEXT,
    ts          TEXT NOT NULL
);
CREATE INDEX idx_action_comments_action ON action_comments(action_id);

CREATE TABLE dq_issues (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    dq_id                  TEXT NOT NULL,
    severity               TEXT NOT NULL,
    source_location        TEXT,
    observed               TEXT,
    expected               TEXT,
    applied_assumption     TEXT,
    status                 TEXT NOT NULL DEFAULT 'Open' CHECK (status IN ('Open', 'Accepted'))
);
CREATE INDEX idx_dq_issues_dqid ON dq_issues(dq_id);

CREATE TABLE kpi_dictionary (
    kpi_name             TEXT PRIMARY KEY,
    definition           TEXT NOT NULL,
    formula              TEXT,
    source               TEXT,
    refresh_frequency    TEXT,
    owner                TEXT
);

CREATE TABLE assumptions (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    area              TEXT NOT NULL,
    assumption_text   TEXT NOT NULL,
    rationale         TEXT,
    created_at        TEXT
);

CREATE TABLE audit_log (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    ts             TEXT NOT NULL,
    actor_role     TEXT,
    action_type    TEXT NOT NULL,
    detail_json    TEXT
);
