# Build PlantPulse: local prototype for CALIBER 2026, Case 2

You are building a local, working prototype of a unified manufacturing dashboard for a petrochemical company. Competition case: "Intelligent Manufacturing Unified Dashboard with root cause insight and follow-up action recommendation". The judges explicitly said they do not want a UI-only mockup: every screen must be driven by the real provided data, end to end (input to output). All UI text must be in English.

"PlantPulse" is a placeholder product name. Keep it in one constant so it can be renamed.

## 0. Before writing any code

1. Inspect every file in `data/raw/` and the screenshots in `docs/reference/`. Print sheet names, header rows, column names and row counts. Compare with section 2 and report any difference before continuing.
2. Propose the folder structure and SQLite schema, then build in the phases of section 10. After each phase: run it, verify the acceptance checks in section 9, and summarize what works and what does not.

## 1. Stack (local only)

- Backend: Python 3.11+, FastAPI, SQLite in one file `db/plantpulse.sqlite`, pandas + openpyxl for Excel, python-pptx for the RCA decks, pytest for tests.
- Frontend: React + Vite + TypeScript. Tailwind is allowed only with the custom tokens in section 7 (disable or ignore the default palette). Charts: Apache ECharts (gauges, heatmap, timelines, line charts).
- Fonts self-hosted with @fontsource so the app works offline.
- Root `package.json`: `npm run ingest` rebuilds the database from `data/raw/`; `npm run dev` starts backend and frontend together (use `concurrently`). Must work on Windows and macOS.
- No cloud services, no API keys, no external language model. The diagnosis logic is rule-based (if/else) and lives in its own module (`backend/engine/`) so it can be replaced later.
- Never modify raw source values. Corrections and assumptions go into derived views, and every assumption is documented.

## 2. Input data (`data/raw/`)

Five equipment, one RCA case each:

| RCA | Tag | Equipment | Plant | Failure date | Failure mode |
|---|---|---|---|---|---|
| 1 | PU-2101B | Feed charge pump | ARP | 12 Mar 2026 | Mechanical seal leakage |
| 2 | KO-3201 | Cracked gas compressor | ZCU | 29 Apr 2026 | High radial vibration trip (bearing distress, water in lube oil) |
| 3 | PM-4405B | Cooling water pump motor | NUP | 8 Jul 2026 | Motor bearing failure (overheating) |
| 4 | HE-3301 | Feed/effluent heat exchanger | ZCU | 21 May 2026 | Fouling, duty loss, high dP |
| 5 | BL-5702 | Product blower | OPP | 17 Jun 2026 | High vibration (coupling misalignment) |

Files:

- `Production_Data_-_RCA{n}_{TAG}.xlsx`
  - Sheet `PI Tag`: tag metadata (Name, Description, engunits, span, zero, typicalvalue, digitalset, instrumenttag).
  - Sheet `Sheet2`: hourly rows, 720 per file (30 days around the failure). Columns: `Timestamp`, `{TAG}_FEED`, `{TAG}_DISP`, `{TAG}_VIB`, `{TAG}_TEMP`, `{TAG}_AMP`, `PLANT_RATE`, `RUN_STATUS` (ON/OFF). The tag in column names has no hyphen (KO3201 means KO-3201). Normalize to long format with generic signal names (feed, discharge_pressure, vibration, temperature, motor_current, plant_rate).
- `Equipment_Performance_-_RCA{n}_{TAG}.xlsx`
  - Sheet `Equipment Info`: key/value block in columns A:B (Equipment Tag, Name, Type, Class, Plant / Unit, Discipline, Criticality, Design Life, Monitoring Method, Linked RCA / AR No., Failure Date, Dominant Failure Mode) and a limits block in columns C:D (Parameter, "Alarm / Trip" stored as text like "45 / 75").
  - Sheet `Condition History`: 26 weekly rows. Week, Date, four parameter columns (unit inside the header, with line breaks), Health Status (NORMAL/ALARM/TRIP), Remark.
  - Sheet `Performance Summary`: key/value KPIs (availability, MTBF, MTTR, PM compliance, total downtime, production loss, estimated loss).
- `Incident_Database.xlsx`
  - Sheet `Incident Database`: header on the third row (pandas `header=2`), 380 rows, 12 plants, Jan 2024 to Jul 2026. Columns: Serial No, MTO No., AR No., Plant, Tag Number, Eq. Class, Date of Occur., Risk Case Title, Highest Impact, Pre-Risk, Risk Score, PIC (RCA), Overall Status, Discipline, Eq. Type, Component, F Mechanism, Downtime (hrs), Act. Loss (k US$), Pot. Loss (k US$), Total Loss (k US$), RCA Due Date, Month - Year. Rows 1 to 5 are the five RCA cases.
  - Sheet `Dashboard`: an existing summary. Reference only.
- `RCA{n}_-_{TAG}_*.pptx`: 11 slides each. Problem identification, chronology, historical data, 4P analysis (G/NG), 4M+1E analysis, CAPA table (action, PIC, due date, status), loss summary. Extract CAPA actions into structured rows. If a table cannot be parsed reliably, create `data/seed/rca_manual.json` by reading the slide text yourself and mark those rows `source = manual_extraction`.

Keys:
- `Tag Number` links production data, equipment performance and incidents (it is the equipment ID).
- `AR No.` links an incident to its RCA report. 226 of 380 incidents have no AR No., so use `Serial No` as the incident primary key.

Text cleanup: some `Remark` and `Risk Case Title` values contain the em dash character (Unicode U+2014). Store the raw value, but the display value must replace it with ": " or " - ". The em dash must never appear on screen.

Limit direction: parse "Alarm / Trip". If alarm > trip, lower is worse (seal flush flow, discharge pressure, lube oil supply pressure, heat duty, cold outlet temperature). All alert and gauge logic must respect direction.

## 3. Data model (SQLite)

At minimum: `plants`, `equipment`, `param_limits` (equipment, parameter, unit, alarm, trip, direction), `sensor_hourly` (long format), `condition_weekly` (long format: one row per parameter per week), `health_weekly`, `performance_summary`, `incidents`, `rca_reports`, `capa_actions`, `problems` (Problem Tank), `actions` (tracked actions, including approved suggestions), `dq_issues`, `kpi_dictionary`, `assumptions`, `audit_log`.

Also create normalized helper columns: `component_family` (Journal Bearing and Motor Bearing map to Bearing), `mechanism_norm` (non-standard values flagged, see DQ10), `eq_type_family`.

## 4. Replay clock (drives the whole app)

The data is historical, so the app runs on a simulated "now".
- Global replay date in the top bar. Default: 8 Apr 2026 (KO-3201 is in ALARM, three weeks before it trips).
- Presets: "1 week before failure" for each of the five equipment.
- Weekly status uses the latest week on or before the replay date. Incidents and actions only count if dated on or before it.
- Play button on the equipment page steps through hourly rows (1 hour per 0.5 s, adjustable) so the demo video shows values rising, status changing and a diagnosis appearing.
- When the replay date is outside an equipment's hourly window (each file covers a different month), show a clear gray "No hourly data for this date" state. Never show zeros for missing data.

## 5. Features

### 5.1 Overview (level 1: all plants)
- KPI band: incidents, downtime (h), loss, open follow-ups, equipment in ALARM, each with previous-period delta.
- Priority queue: ranked list of current alerts (section 5.4) with priority chip, tag, plant, one-line reason. Click opens the equipment page.
- Loss by plant for all 12 plants, sorted. Mark the 4 plants that have sensor-level equipment (ARP, ZCU, NUP, OPP). Click a plant opens level 2.
- Heatmap: plant x month (incident count, toggle to loss), inspired by the "Workload" heatmap in reference 2.
- Follow-up pipeline: incident counts per Overall Status (NEW REGISTERED, RCA PROCESS, CA/PA EXECUTION, MONITORING RESULT, RISK CLOSED, RISK CANCELED) plus overdue counts.

### 5.2 Plant view (level 2)
- Plant KPIs, equipment table (status chip, class, worst parameter vs limit, priority), incident history, open actions.
- Equipment without sensor data is listed as "Incident history only".

### 5.3 Equipment detail (level 3)
- Identity strip: tag, name, type, plant, class, status chip.
- Gauges like reference 1 (value, previous period, small sparkline): Availability, Health margin (distance of worst parameter to its trip limit), Production vs normal (PLANT_RATE vs median of ON hours in the first 7 days of the window). Side list "Other KPIs": MTTR, MTBF, downtime, loss.
- Machine status timeline like reference 1: lanes Running (green), Alarm (amber), Trip/Off (red), No data (gray), with a distribution panel (duration and occurrences).
- Weekly parameters: four small charts with alarm and trip lines, replay date marker.
- Hourly trend with anomaly markers (section 5.5).
- Diagnosis panel, similar incidents, suggested actions (sections 5.5 to 5.7).
- Linked RCA summary: chronology, root cause, CAPA list with status.

### 5.4 Alert priority
For each equipment on the replay date: `priority_score = 0.4 * severity + 0.3 * class + 0.3 * loss_exposure`, each normalized 0 to 1.
- severity: TRIP 1.0, ALARM 0.7, rising trend toward alarm 0.4, normal 0.
- class: A 1.0, B 0.6, C 0.3.
- loss_exposure: RCA or historical loss for the same equipment type, normalized over the set.
Labels: Critical, High, Medium, Low. Show the breakdown on hover so the ranking is explainable.

### 5.5 Diagnosis engine (rule-based)
Rules keyed on failure-mode family and parameter names, not on tag names, so they also work for other equipment of the same type. Each condition is evaluated on the replay date using weekly values vs limits and the 4-week trend (slope).
- Seal leakage (pump): seal flush flow falling toward or below alarm; vibration rising; bearing temperature rising; discharge pressure falling.
- Lube oil water ingress, bearing distress (compressor): water content above alarm; oil supply pressure falling; radial vibration rising; bearing metal temperature rising.
- Motor bearing lubrication failure: DE bearing temperature above alarm; motor vibration rising; motor current rising; winding temperature rising.
- Exchanger fouling: tube-side dP above alarm; heat duty below alarm; cold outlet temperature falling; feed heavy-ends rising.
- Coupling misalignment: coupling offset above alarm; 2X harmonic rising; overall vibration rising; bearing temperature rising.
Confidence: 4/4 High, 3/4 Medium, 2/4 Low, below that no hint. Show every condition as a row: parameter, value, limit, trend, pass/fail. Label the panel "Root cause hint" with the note "Suggested, needs engineer review".

Hourly anomaly detection: rolling 24 h mean vs a baseline (first 7 days of the window, ON hours only). Flag when deviation exceeds 3 standard deviations for 3 consecutive hours. Ignore OFF hours.

### 5.6 Similar incidents
Score each row of the incident database: +3 same Eq. Type, +3 same component_family, +2 same mechanism_norm, +1 same plant, +1 same discipline. Top 5 with AR No., date, downtime, loss, status, link to RCA if present. Rows flagged by DQ9 appear with a warning tag, and the score explanation is visible.

### 5.7 Problem Tank and action tracking
- Problem Tank: backlog of open problems (from alerts, incidents in progress, RCA cases).
- Actions: corrective and preventive, with PIC, due date, status (Open, In progress, Done, Rejected), overdue days relative to the replay date. Pre-load CAPA actions from the five RCA decks.
- Suggested actions from the diagnosis (mapped per rule, taken from CAPA of the RCA with the same failure mode first, then generic defaults) only become tracked actions after an engineer clicks Approve (with PIC and due date). Reject needs a reason. Everything goes to `audit_log`.
- Dense, filterable table view, not a card board.

### 5.8 Backtest
For each of the five equipment: first ALARM week, TRIP week, lead time in weeks; first hourly anomaly before the first OFF hour, lead time in hours; downtime and loss from the RCA. Swimlane timeline chart plus a table. Show the message "Warning was available X weeks before the trip" with the assumption stated. Compute everything, do not hardcode.

### 5.9 Data foundation
- Source map: which file, sheet and column feeds which table and which KPI, and which key links them.
- KPI dictionary: name, definition, formula, source, refresh frequency, owner. Include Availability, MTBF, MTTR, Downtime (one agreed definition), Production loss (t), Loss (USD), Health status, Alarm lead time, Open incidents, CAPA overdue rate, Data quality score, Energy proxy.
- Data quality: table of all `dq_issues` (section 6) with severity, source location, observed vs expected, applied assumption, status (Open/Accepted), plus a data quality score.

### 5.10 Energy proxy (low priority, build last)
No metered energy data exists. Daily sum of motor current per equipment as a "Motor load index", 7-day moving average forecast for the next 7 days. Always labeled "Proxy derived from motor current, not metered energy".

### 5.11 Roles (no login, prototype)
Role switch in the top bar:
- Executive: sees all money values.
- Plant manager: pick a plant; money visible only for that plant.
- Engineer: no money values; impact shown as tons, hours and priority labels.
Log role switches and views of money values to `audit_log`.

## 6. Data quality checks

Implement each as a generic rule. The examples are the expected findings in this dataset and double as test cases.

| ID | Check | Expected finding |
|---|---|---|
| DQ1 | Values outside PI Tag span | KO3201_VIB: 720 of 720 values outside 0 to 20 MM/S. Values match the weekly micron data, so the unit label is likely wrong. Derived view assumes micron. |
| DQ2 | Placeholder metadata | `typicalvalue` equals span / 2 for every tag. Do not use it as a target. |
| DQ3 | Signal not applicable to equipment type | HE-3301 (heat exchanger, no motor) has motor current and vibration tags. |
| DQ4 | Hourly vs weekly conflict at failure | Last hourly values before OFF never reach the weekly TRIP value (PU-2101B vibration 6.3 vs 11.2; PM-4405B bearing temp about 83 vs 91.8 and current about 137 vs 168.3; BL-5702 vibration 9.9 vs 11.2; KO-3201 72.7 vs 76.5). |
| DQ5 | Formula-like values | Trip-week values are exactly limit x 1.02 (or x 0.98 when lower is worse). Info severity. |
| DQ6 | Document vs data conflict | RCA2 states KO-3201 lube oil pressure normal at 1.8 barg, weekly data shows 1.078 (below trip). RCA2 states water 1800 ppm, weekly 1530. RCA2 says vibration rose over 5 days, weekly shows about 11 weeks. RCA3 states PM-4405B current 132 A, weekly 168.3 A. RCA3 says the standby pump took over, but PLANT_RATE is 0 during OFF. Also compare alarm limits written in RCA decks vs Equipment Info. Use extracted numbers where possible, otherwise seed as manual review entries. |
| DQ7 | Duplicate tag across plants | CV-5846 in BRP and OP3. |
| DQ8 | Duplicate MTO No. | BL-5702 and KO-6912A share one MTO No. |
| DQ9 | Implausible component for equipment type | 18 of 21 "Exchanger Fouling" / Tube Bundle incidents are on non heat exchanger equipment (pumps, blowers, transformers, tanks). Build a plausibility matrix of component vs Eq. Type. |
| DQ10 | Non-standard vocabulary | F Mechanism values "High", "Mechanical", "Motor" (the five RCA rows). Component singletons "Journal Bearing", "Motor Bearing". |
| DQ11 | Risk label vs impact | 14 incidents with Pre-Risk IV (lowest) and total loss above 500 k US$ (example TX-5187B: 32.6 h, 972 k US$). |
| DQ12 | Identical template metadata | Design Life, Monitoring Method and PM Compliance (92%) identical for all five equipment. |

Process flags (real data, shown in a separate "Follow-up health" section, not as data errors): RCA PROCESS items past RCA Due Date (69 of 71 as of 31 Jul 2026); NEW REGISTERED items older than 90 days (oldest from Jan 2024); incidents without AR No. (226).

Not errors (document in the KPI dictionary, do not flag):
- Tag prefix differs from Eq. Type code but maps consistently: PM to EM, HE to HB, FN to FA, CV to VA, AZ to SX.
- RCA Due Date is empty only for RISK CLOSED, RISK CANCELED and MONITORING RESULT.
- HE-3301 shows 13 OFF hours vs 12 h reported because of hourly resolution (same effect for PU-2101B: 18 rows vs 18.5 h).
- Downtime 0 with loss above 0 (repair cost without stopping).
- HE-3301 is OFF but still has about 12 T/H flow: a bypass rate cut, not a full stop. RUN_STATUS OFF does not always mean zero production.

## 7. Visual design

Reference: `docs/reference/` (Siemens Performance Insight). Take the structure, not a copy: asset tree, breadcrumb, gauges with previous period, machine status timeline with distribution panel, heatmap.

Shell:
- Slim black icon rail on the far left (48 px), asset tree panel (plants, then equipment, with count badges, 240 px), breadcrumb bar, page tabs (Overview, Diagnosis, Actions, Backtest, Data), replay clock and role switch at top right.

Color tokens (bold and restrained: white, ink and blue dominate; status colors only for status and data):
- `--ink #0E1116` (text, icon rail), `--paper #FFFFFF`, `--canvas #F1F2F4`, `--line #D3D6DB`, `--mute #5F6670`
- `--blue #0A5CD6` (primary, selection, links)
- `--green #1E9E3A` (running, normal), `--amber #F2B300` (alarm), `--orange #E8650F` (high priority), `--red #D7191C` (trip, fault, critical), `--black #000000` (off)
- Status chips are solid fills (red with white text, amber with black text, green with white text).

Typography (sans only):
- Display and big numbers: "Archivo" (use the width axis: semi-expanded for numbers, semi-condensed for dense labels), weights 700 to 800.
- Body and tables: "IBM Plex Sans" 400/500/600, `font-variant-numeric: tabular-nums` for all numbers and tags.
- Scale: 12, 13, 15, 20, 28, 44 px. Tight line heights for data, generous only for page titles.

Surfaces:
- Flat white panels separated by 1 px `--line` rules. Radius 0 to 3 px. No shadows except popovers and menus. No gradients.
- Group related KPIs in one continuous band divided by vertical rules instead of separate cards.

Layout:
- 12-column grid, 16 px gutter, 8 px spacing unit. Asymmetric and offset compositions, different per page:
  - Overview: KPI band spans 8 columns, priority queue is a tall 4-column column on the right spanning three rows; loss-by-plant spans 8; below it a 5-column heatmap next to a 3-column follow-up pipeline.
  - Equipment: identity strip full width; three gauges (3 columns each) plus a 3-column "Other KPIs" list; status timeline 9 columns plus 3-column distribution; weekly small multiples 2 x 2 in 7 columns next to a 5-column hourly trend; bottom row diagnosis 5, similar incidents 4, suggested actions 3.
  - Actions: narrow 3-column filter and count rail plus 9-column dense table, detail drawer on the right.
- Tight spatial rhythm, clear hierarchy, whitespace only where it separates meaning.

Explicit bans:
- NO purple-to-blue or violet gradients.
- NO Inter, Roboto or system-default sans-serif fonts.
- NO uniform `rounded-2xl` identical cards in a 3-column grid.
- NO timid, evenly distributed pastel colors.
- NO low-opacity tinted boxes with a colored outline (for example `bg-red-500/10` with `border-red-500`), no glassmorphism, no blur.

## 8. Copy rules

- English only. Short, specific labels with units ("Vibration 60.5 µm, alarm 45, trip 75").
- Never use the em dash character anywhere: UI strings, code comments, README, generated text. Use a colon, comma or hyphen.
- Do not label features with "AI". Use "Diagnosis", "Root cause hint", "Rule engine", "Similar incidents". The term may appear at most once, in the About section, if at all.
- Money: "226 k USD", "1.58 M USD". Dates: "8 Apr 2026".
- Every suggestion shows its evidence and the note "Suggested, needs engineer review".

## 9. Acceptance checks (print these after ingestion and assert them in tests)

- 380 incidents, 12 plants, 5 equipment with sensor data.
- Incidents per plant: ZCU 62, ARP 49, OPP 42, SMX 42, OP2 37, OP3 32, BRP 26, CRP 25, NUP 24, BDX 20, OPU 14, TKX 7.
- Overall Status: RISK CLOSED 113, CA/PA EXECUTION 92, RCA PROCESS 71, RISK CANCELED 47, MONITORING RESULT 37, NEW REGISTERED 20.
- Total downtime about 2,261 h; total loss about 67.2 M USD (sum of Total Loss).
- OFF hours in hourly data: PU-2101B 18, KO-3201 32, PM-4405B 8, HE-3301 13, BL-5702 14.
- First ALARM to TRIP lead time (weeks): PU-2101B 6, KO-3201 11, PM-4405B 6, HE-3301 10, BL-5702 15.
- RCA actual loss (k USD): 226.44, 1584.00, 112.00, 183.60, 478.80 (total 2,584.84).
- On 8 Apr 2026: KO-3201, HE-3301 and BL-5702 in ALARM; PU-2101B and PM-4405B NORMAL.
- On 8 Apr 2026 the KO-3201 diagnosis returns "Lube oil water ingress" with High or Medium confidence, and the top similar incidents include a compressor bearing case.
- All DQ1 to DQ12 findings in section 6 are detected.
- No em dash character in any file under `frontend/src`, `backend/` or `README.md` (add a test that greps for U+2014).

## 10. Build phases

1. Ingestion, schema, text cleanup, acceptance report.
2. FastAPI endpoints (overview, plant, equipment, series, diagnosis, similar incidents, actions, backtest, data quality, KPI dictionary, replay).
3. App shell, design tokens, fonts, Overview page, replay clock.
4. Plant and Equipment pages with gauges, status timeline, trends.
5. Priority, diagnosis rules, hourly anomaly detection, similar incidents (with pytest tests).
6. Problem Tank, action tracking, approve and reject flow, audit log.
7. Backtest page.
8. Data foundation pages and all data quality checks.
9. Roles, energy proxy, polish, "Reset demo data" button, README with setup steps and a 3-minute demo script (story: 8 Apr 2026, KO-3201 is Top 1 priority, diagnosis shows water in lube oil, engineer approves an action, backtest shows the warning came 11 weeks before the trip).