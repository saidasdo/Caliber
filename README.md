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
those changes; the raw files under `data/raw/` are never modified by the app itself.

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
just hidden in the browser.

## A 3-minute demo script

Story: on 8 Apr 2026, KO-3201 is the top priority alert. Its diagnosis points at
water in the lube oil, weeks before the compressor actually trips, and the same
alert reads differently depending on who is looking at it. An engineer proposes the
fix, a plant manager approves it, and the backtest shows the warning was available
11 weeks before the trip.

1. **Start as Executive** (the default role switch to click first). You land on the
   Overview page: point out the priority queue on the right, KO-3201 is #1 and
   pulsing red for Critical. Below, "Top alerts" has the same alert in business
   language: "Cracked Gas Compressor KO-3201 at risk of trip. Possible impact: risk
   of trip, about 1.58 M USD." Click into KO-3201: the whole page is one Impact
   summary card plus a one-line diagnosis, everything else collapsed, because an
   executive does not need the sensor detail.

2. **Switch to Plant manager** (equipment stays open). The same page now shows the
   full gauges, a diagnosis summary line, and the suggested actions list, with the
   sensor charts collapsed behind "Show sensor detail" toggles. Follow the ZCU
   breadcrumb to the plant page: point out the downtime-by-cause chart, the RCA
   summaries, and that loss in USD is visible here because ZCU is this manager's own
   plant (switch the asset tree to another plant to show the money disappears there
   too).

3. **Switch to Engineer** (equipment stays open again). Now every sensor chart is
   expanded, the Root cause hint panel shows all 4 of 4 conditions with their
   value/limit/trend rows, and the alert queue strip at the top lists the other live
   alerts to jump between. Click "Confirm diagnosis", then in Suggested actions
   click "Propose" on "Repair leaking lube-oil cooler tube". No PIC or due date yet;
   that is the plant manager's step.

4. **Back to Plant manager**, ZCU page: a "Pending your approval" banner now shows
   the proposed action. Click Approve, fill in a PIC and due date, confirm. Mention
   every step so far (confirm, propose, approve) is in the audit log with role,
   timestamp and note.

5. **Engineer again**: open the action's detail drawer and move it to In progress,
   then Done with a short note. **Plant manager**: the same action now has a Close
   button; click it.

6. **Open the Backtest page**. Find the KO-3201 row: "Warning was available 11 weeks
   before the trip (weekly ALARM to TRIP)." Point at its lane in the swimlane chart
   and the blue marker for the first hourly anomaly.

7. **Close as Executive**: back on Overview, the "Overdue escalations" list is where
   an executive would press Escalate on anything overdue and add a comment, the one
   write action this role has. Mention the Data page has the full source map, KPI
   dictionary and all 12 data quality checks for anyone who wants to verify a
   number.

## Project layout

- `data/raw/` - the provided source files, never modified.
- `db/schema.sql`, `db/plantpulse.sqlite` - the SQLite schema and the built database.
- `backend/app/ingest/` - readers, transforms, data quality checks, the acceptance
  report (`npm run ingest`).
- `backend/app/engine/` - rule-based logic only (priority, diagnosis, anomaly
  detection, similar incidents, backtest, gauges, energy proxy), with no cloud
  services or external models.
- `backend/app/api/` - the FastAPI routes.
- `frontend/src/` - the React + Vite + TypeScript app.

## Stack

Python 3.11+/FastAPI/SQLite on the backend, React/Vite/TypeScript with Tailwind
(custom tokens only) and Apache ECharts on the frontend. Diagnosis is rule-based
(if/else), lives in `backend/app/engine/diagnosis.py`, and can be replaced later
without touching the rest of the app.
