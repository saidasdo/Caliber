# PlantPulse

A local, working prototype of a unified manufacturing dashboard for a petrochemical
company, built for CALIBER 2026 Case 2: "Intelligent Manufacturing Unified Dashboard
with root cause insight and follow-up action recommendation."

"PlantPulse" is a placeholder product name.

Every screen is driven by the real data in `data/raw/`: 5 equipment with hourly sensor
data, weekly condition monitoring, a 380-row incident database across 12 plants, and
5 RCA/CAPA decks. The app runs on a simulated "now" (the replay clock in the top bar)
so the demo can show an alert developing before a failure, instead of only the
after-the-fact outcome.

## Prerequisites

- Node.js 18 or later
- Python 3.11 or later
- No internet access or API keys needed once dependencies are installed; everything
  (including the fonts) runs fully offline.

## Setup

From the repository root:

```
npm install
npm install --prefix frontend
pip install -r backend/requirements.txt
```

Build the database from `data/raw/` (rebuilds `db/plantpulse.sqlite` from scratch and
prints the section 9 acceptance checks):

```
npm run ingest
```

Start the backend and frontend together:

```
npm run dev
```

Open http://localhost:5173. The API alone is at http://localhost:8000 (interactive
docs at http://localhost:8000/docs).

### Running tests

```
cd backend
python -m pytest
```

### Resetting demo data

If you have proposed, approved, rejected or closed any actions, or changed an
action's status during a session, click the gear icon at the bottom of the left icon
rail and confirm "Reset demo data". This re-runs ingestion in place and discards
those changes; the raw files under `data/raw/` are never modified by the app itself. The rebuild is written beside the live database and swapped in only when it is complete, so a request made during a reset never reads a half-built database.

## Replay rules

The app behaves as if today is the replay date. Nothing shown for a replay date uses
information dated after that date, and every live view is filtered by it:

- **Charts end at the replay date.** The weekly and hourly trends, the status timeline,
  the energy proxy and the emission estimate stop there. The x-axis keeps the full record
  width, so the chart does not change size; the area after the replay date is a light grey
  band with no label. The replay marker line is gone, because the right
  edge of the chart is the replay date.
- **Energy forecast.** The 7-day forecast starts the day after the replay date and uses only
  data up to it. It is the only thing the live views return with a date after the replay date,
  and it is labelled as a forecast.
- **Actions.** An action is shown once it is known: a CAPA action from the day its RCA failed,
  a user-made action from the replay date it was made on (the app sends the replay date with
  every request).
- **Retrospective views keep the full history and say so.** The Backtest page shows
  "Retrospective view: compares warnings with what happened later." The Data page says its
  data quality checks run on the full dataset.
- **Incident status** is shown with the note "Status as of the data extract, Jul 2026":
  the data has no status history.

Automated checks (`backend/tests/test_replay_visibility.py`) go through every live endpoint
for KO-3201 on 8 Apr 2026 and PM-4405B on 1 Jul 2026, and fail if any returns a date after the
replay date (the forecast excepted) or a TRIP week before the replay date.

Earlier rules, still in force:

- **Estimated impact** is the median total loss of earlier incidents for the same
  equipment family (fallback: same class, then all), dated before the replay date. It is
  an estimate of what a failure like this has cost, never a known amount. The
  equipment's own RCA loss is not used before its failure date.
- **Similar incidents** are scored from the diagnosis for the replay date, using only
  incidents dated before it.
- **Suggested actions** come from the equipment's own RCA corrective actions only once
  that RCA's failure date is before the replay date. Before that, the generic action
  library is used (two corrective and two preventive actions per diagnosis rule). Each
  suggestion says where it came from: "From the equipment's own RCA" or "Generic action
  (library)".
- **RCA evidence** is shown only from the failure date on. Before it, the panel says
  "No RCA yet for this event" and lists RCAs of similar past incidents, if any.
- **Backtest** downtime and loss are labeled "Actual outcome (after the trip)": the
  backtest is an after-the-fact analysis by design.

The full list of assumptions, with rationale, is on the Data page under **Assumptions**.

## Roles

The role switch is the popup pinned to the bottom of the screen. Each role is a
different lens on the same underlying data and the same replay date, not a separate
app: switching roles while an equipment page is open keeps that equipment open, so
you can show the same situation from three angles without navigating away.

| | Executive | Plant manager | Engineer |
|---|---|---|---|
| Main question | Is the business performing, and where is the risk? | Where is the problem in my plant and what needs attention? | What exactly is wrong and how do I fix it? |
| Scope | All plants | One selected plant (defaults to ZCU) | All equipment, with an optional plant filter |
| Landing page | Overview | The selected plant's page | The top alert's equipment page |
| Money | Visible everywhere | Visible only for the selected plant | Never visible; shown as tons, hours and priority labels instead |
| Action rights | View, comment, escalate overdue actions | Approve or reject proposed actions (assigning PIC and due date), close finished actions | Confirm or reject the diagnosis, propose actions, update progress |

A role only sees the buttons for its own rights; the backend enforces the same
rule server-side (a disallowed request gets HTTP 403, not just a hidden button), and
money fields the role shouldn't see are stripped from the API response itself, not
just hidden in the browser. The estimated impact is money, so it follows the same rule.

The machine page layout is the same for all three roles. The only difference is the
impact card (estimated impact in USD), which Executive and Plant manager see and
Engineer does not.

## Alert priority

One urgency score is both the rank and the number shown:

    urgency = 0.6 x proximity + 0.4 x alarm share        (TRIP = 1.0)

- **Proximity** = `1 - health margin / 100`, clipped to 0 to 1. The margin is the worst
  monitored parameter against its healthy baseline (see the health margin section).
- **Alarm share** = parameters past their alarm limit / parameters monitored.

**Rank** is urgency, highest first. Only exact ties are broken, by Criticality (High, then
Medium, then Low), then by estimated impact.

**Labels** come from urgency and status alone. Critical if urgency is at least 0.7 or the
machine has tripped; High if at least 0.5; Medium if at least 0.25 or the machine is in ALARM;
otherwise Normal. Class and loss never change a label, and a machine in NORMAL status is never
labelled above Normal.

Each card shows the urgency, the margin to trip, and the estimated impact. The hover breakdown
shows proximity, alarm share, the parameter count, and the tie-break terms. Nothing in the engine
names an equipment; the order is derived on each request. The tests check that the order is
the urgency order on every date and that the dominance rule holds for every pair on the test
dates (`backend/tests/test_priority_dominance.py`).

Result for each date (rank, label, urgency):

| Replay date | Order |
|---|---|
| 8 Apr 2026 (default) | 1 KO-3201 Critical 0.83; 2 HE-3301 High 0.55; 3 BL-5702 Medium 0.24; 4 PM-4405B Normal 0.06; 5 PU-2101B Normal 0.04 |
| 22 Apr 2026 (KO-3201 preset) | 1 KO-3201 Critical 0.98; 2 HE-3301 Critical 0.74; 3 BL-5702 Medium 0.32; 4 PM-4405B Normal 0.12; 5 PU-2101B Normal 0.01 |
| 5 Mar 2026 (PU-2101B preset) | 1 PU-2101B Critical 0.94; 2 KO-3201 Medium 0.44; 3 BL-5702 Medium 0.14; 4 HE-3301 Normal 0.13; 5 PM-4405B Normal 0.00 |
| 14 May 2026 (HE-3301 preset) | 1 HE-3301 Critical 0.95; 2 BL-5702 High 0.63; 3 PM-4405B Normal 0.22; 4 KO-3201 Normal 0.09; 5 PU-2101B Normal 0.01 |
| 1 Jul 2026 (PM-4405B preset) | 1 PM-4405B Critical 0.95; 2 HE-3301 Normal 0.10; 3 KO-3201 Normal 0.05; 4 PU-2101B Normal 0.01; 5 BL-5702 Normal 0.00 |
| 10 Jun 2026 (BL-5702 preset) | 1 BL-5702 Critical 0.95; 2 PM-4405B Critical 0.78; 3 HE-3301 Normal 0.09; 4 KO-3201 Normal 0.05; 5 PU-2101B Normal 0.01 |

On 8 Apr the headline reads "3 machines need attention, 1 critical". On 22 Apr it reads
"3 machines need attention, 2 critical". Machines labelled Normal are listed under "Show all",
not in "Needs attention now".

## Machine page

An equipment page has two tabs:

- **Overview**: the three main gauges (availability, health margin to trip, production
  vs normal), the status timeline, a weekly trend and an hourly trend panel that cycle
  through their charts every few seconds (arrows and dots switch them by hand), the
  energy proxy, and the emission estimate. The page scrolls: every block has room for its
  numbers. Click any chart for the full detail in a pop-up.
- **Status timeline** shows three states only: Running (green), Alarm (amber) and Trip / Off
  (red). A tick every three days lets you read the bar against dates. It stops at the replay
  date.
- **Action**: when the machine is in ALARM or TRIP, everything about the problem sits in
  one red "A problem occurred" group: root cause hint (with confirm/reject for the
  engineer), similar incidents, suggested actions (propose, approve, reject), and RCA
  evidence. The group scrolls when the panels run longer than the window. When the
  machine is healthy, the tab says there is nothing to act on.

The Action tab beeps red while an alarm is waiting for someone to act: the machine is
in ALARM or TRIP, and at least one suggested action has no tracked action yet. The beep
goes away once the suggestion is proposed or rejected, and it is shown to the roles that
can propose or approve actions (Engineer and Plant manager).

### Health margin to trip

Each monitored parameter is measured against its own healthy baseline: the median of its
first 6 weeks of condition data. 100% means at that baseline, 0% means at the trip limit,
and negative means beyond trip. The gauge shows the worst parameter. Its colour bands are
red below 0, amber from 0 up to the highest alarm margin across the parameters, and green
above that. So a healthy week reads green, and the last alarm week before a trip reads
amber or red.

### Emission estimate

Shown for the motor-driven equipment only (a heat exchanger has no motor drive). It is
estimated from motor current on each ON hour: kWh = sqrt(3) x voltage (kV) x current (A)
x power factor, then kg CO2e = kWh x grid emission factor. It is labeled "estimate from
motor current, not metered".

**The three factors are placeholders** (`backend/app/config.py`: `MOTOR_VOLTAGE_KV`,
`POWER_FACTOR`, `GRID_EMISSION_FACTOR_KG_PER_KWH`). Set them from official sources (the
nameplate voltage, a measured or nameplate power factor, and the official grid factor for
the plant's location) before any figure leaves the prototype. The current values are
written to the assumptions table and shown on the Data page, and the emission pop-up
states they are placeholders.

### MTBF and MTTR

Shown in the equipment table on the plant page, as of the replay date. Failures are TRIP
episodes in the weekly health data up to that date. MTBF is observed hours divided by
failures; MTTR is OFF hours divided by failures. Until the first failure the table says
"No failure in period". The whole-period figures in the source file are not used, since
they include failures after the replay date.

## Executive overview

The all-plants overview fits one 1440 x 900 screen with no page scroll, in three tiers:

0. **Headline**, one generated sentence from the priority queue on the replay date:
   "3 machines need attention, 1 critical" (Medium or above counts as needing attention), or "All machines normal".
1. **Needs attention now** (two thirds): the top five machines labelled Medium or above, each with its rank,
   tag, plant, equipment type, a plain-words reason with the health margin left, estimated
   impact, and an action status chip ("No owner yet", "Proposed", "Open", "In progress"). The
   left rule carries the priority. "Show all" opens the full queue. **Follow-up health** (one
   third): RCA overdue, awaiting approval, open follow-ups with the change, and "Review
   escalations".
2. **Four KPI tiles**, one status line each: production vs normal, downtime, loss (Executive
   only), and energy and emission (labeled as an estimate). Production and energy/emission open
   their breakdown per machine.
3. **Top plants by loss** (top three, "All 12 plants" opens the full list), the plant-by-month
   heatmap and the follow-up pipeline, shown in full. Each has an "Open" button for a larger
   pop-up.

## Executive KPI band

Eight cells across the top of the all-plants overview: incidents, downtime, loss (Executive
only), open follow-ups, production vs normal, energy proxy, emission estimate and equipment in
alarm.

- **Production vs normal**: the average of the equipment that have hourly data on the replay
  date, shown as "No hourly data" when none do. Click for the per-equipment breakdown.
- **Energy proxy (week)**: total motor load index for the 7 days up to the replay date, against
  the 7 days before, with the direction of the 7-day forecast. Click for the per-equipment
  breakdown. The two weeks are compared only over the machines that have data in both.
- **Emission estimate (4 motor-driven)**: the same comparison for the CO2e estimate. The
  heat exchanger is excluded because it has no motor drive. Click for the breakdown.

## A 3-minute demo script

Story: on 8 Apr 2026, KO-3201 is in ALARM with a root cause hint that points at water in
the lube oil, weeks before the compressor trips. KO-3201 ranks first on the priority
queue: all four parameters are past alarm and its margin is the lowest. An engineer proposes the fix, a plant manager approves it, and the backtest
shows the warning was available 11 weeks before the trip.

1. **Start as Executive** (the default role switch to click first). You land on the
   Overview page: KO-3201 ranks first (Critical, urgency 0.83), HE-3301 second (High, 0.55)
   and BL-5702 third (Medium, 0.24). "Needs attention now" lists the same alerts with their health margin,
   estimated impact and action status. Click into KO-3201: the machine page shows the gauges,
   timeline, trends, energy proxy and emission estimate, plus the impact card: "Estimated
   impact: about 93 k USD, median of 18 similar past incidents". Point out the Action tab:
   as an executive you can comment and escalate there, not propose.

2. **Switch to Plant manager** (equipment stays open). The machine page looks the same,
   and the Action tab beeps red because a suggested action is still waiting for an
   engineer. Follow the ZCU breadcrumb to the plant page: point out the downtime-by-cause
   chart, the RCA summaries (only those whose failure date has passed), the MTBF and MTTR
   columns, and the "Pending your approval" section. Loss in USD is visible here because
   ZCU is this manager's own plant (switch the asset tree to another plant to show the
   money disappears there too).

3. **Switch to Engineer** (equipment stays open again). The machine page is unchanged,
   except the impact card is gone. Open the Action tab and point at the root cause hint:
   4 of 4 conditions met, each with its value, limit and trend. The suggested actions are
   generic library actions, because the KO-3201 RCA is not known until 29 Apr 2026, and the
   RCA evidence panel says "No RCA yet for this event". Click "Confirm diagnosis", then
   propose one of the suggested actions. No PIC or due date yet; that is the plant
   manager's step. The beep stops.

4. **Back to Plant manager**, ZCU page: the "Pending your approval" section now shows
   the proposed action. Click Approve, fill in a PIC and due date, confirm. Mention
   every step so far (confirm, propose, approve) is in the audit log with role,
   timestamp and note.

5. **Engineer again**: open the action's detail drawer on the Actions page and move it
   to In progress, then Done with a short note. **Plant manager**: the same action now
   has a Close button; click it.

6. **Open the Backtest page**. Find the KO-3201 row: "Warning was available 11 weeks
   before the trip (weekly ALARM to TRIP)." Downtime and loss are labeled as actual
   outcomes. Point at its lane in the swimlane chart and the blue marker for the first
   hourly anomaly.

7. **Close as Executive**: back on Overview, "Review escalations" in Follow-up health is where
   an executive would press Escalate on anything overdue and add a comment, the one
   write action this role has. Mention the Data page has the full source map, KPI
   dictionary, assumptions and all 12 data quality checks for anyone who wants to verify
   a number.

## Project layout

- `data/raw/` - the provided source files, never modified.
- `db/schema.sql`, `db/plantpulse.sqlite` - the SQLite schema and the built database.
- `backend/app/ingest/` - readers, transforms, data quality checks, the acceptance
  report (`npm run ingest`).
- `backend/app/engine/` - rule-based logic only (priority, impact, diagnosis, anomaly
  detection, similar incidents, suggested actions, backtest, gauges, reliability,
  emission and energy proxy, status timeline), with no cloud services or external models.
- `backend/app/catalog/` - the generic action library used before an RCA is known.
- `backend/app/api/` - the FastAPI routes.
- `frontend/src/` - the React + Vite + TypeScript app.

## Stack

Python 3.11+/FastAPI/SQLite on the backend, React/Vite/TypeScript with Tailwind
(custom tokens only) and Apache ECharts on the frontend. Diagnosis is rule-based
(if/else), lives in `backend/app/engine/diagnosis.py`, and can be replaced later
without touching the rest of the app.
