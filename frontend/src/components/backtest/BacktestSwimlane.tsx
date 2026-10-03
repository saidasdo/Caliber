import { Link } from "react-router-dom";
import type { BacktestRow, HealthStatus } from "../../lib/types";

const STATUS_CLASS: Record<NonNullable<HealthStatus>, string> = {
  NORMAL: "bg-green",
  ALARM: "bg-amber",
  TRIP: "bg-red",
};

const TOTAL_WEEKS = 26;
const LABEL_WIDTH = "80px";
const TRAILING_WIDTH = "64px";

function weekToPercent(week: number): number {
  return ((week - 1) / (TOTAL_WEEKS - 1)) * 100;
}

// SPEC section 5.8: "Swimlane timeline chart plus a table." One lane per equipment, built
// from each week's real recorded health_status (section 6 condition history), not a 3-point
// interpolation, so a post-trip recovery (e.g. PU-2101B returning to NORMAL) shows correctly.
//
// The tick header and every row share the same [label][gap][track][gap][trailing] flex
// structure so that a given week lines up at the same x position in the header and every
// lane (percentage `left` offsets are relative to the track's own box, not the page).
export function BacktestSwimlane({ rows }: { rows: BacktestRow[] }) {
  const weekTicks = [1, 5, 9, 13, 17, 21, 26];

  return (
    <div className="border border-line bg-paper">
      <div className="border-b border-line px-2 py-1.5 text-12 font-semibold uppercase tracking-wide text-mute">
        Swimlane: weekly health status, with the first hourly anomaly marked
      </div>
      <div className="p-2">
        <div className="flex items-center gap-2">
          <span style={{ width: LABEL_WIDTH }} className="shrink-0" />
          <div className="relative h-2 min-w-0 flex-1 overflow-hidden">
            {weekTicks.map((w) => (
              <span
                key={w}
                className="tabular absolute top-0 -translate-x-1/2 text-12 text-mute"
                style={{ left: `${weekToPercent(w)}%` }}
              >
                wk {w}
              </span>
            ))}
          </div>
          <span style={{ width: TRAILING_WIDTH }} className="shrink-0" />
        </div>
        <ul className="mt-2 space-y-2">
          {rows.map((row) => (
            <SwimlaneRow key={row.equipment_tag} row={row} />
          ))}
        </ul>
        <div className="mt-2 flex items-center gap-3 text-12 text-mute">
          <Legend swatch="bg-green" label="Normal" />
          <Legend swatch="bg-amber" label="Alarm" />
          <Legend swatch="bg-red" label="Trip" />
          <Legend swatch="bg-blue" label="First hourly anomaly" diamond />
        </div>
      </div>
    </div>
  );
}

function SwimlaneRow({ row }: { row: BacktestRow }) {
  const segments = toSegments(row.weekly_health);
  const anomalyLeft =
    row.first_hourly_anomaly_week != null ? weekToPercent(row.first_hourly_anomaly_week) : null;

  return (
    <li className="flex items-center gap-2">
      <Link
        to={`/equipment/${row.equipment_tag}`}
        style={{ width: LABEL_WIDTH }}
        className="tabular shrink-0 truncate text-13 font-medium text-blue"
      >
        {row.equipment_tag}
      </Link>
      <div className="relative h-2 min-w-0 flex-1 overflow-hidden bg-canvas">
        {segments.map((s, i) => (
          <div
            key={i}
            title={`Week ${s.startWeek}-${s.endWeek}: ${s.status}`}
            className={`absolute inset-y-0 ${STATUS_CLASS[s.status]}`}
            style={{
              left: `${weekToPercent(s.startWeek)}%`,
              width: `${((s.endWeek - s.startWeek + 1) / (TOTAL_WEEKS - 1)) * 100}%`,
            }}
          />
        ))}
        {anomalyLeft != null && (
          <div
            title={`First hourly anomaly: week ${row.first_hourly_anomaly_week} (${row.first_hourly_anomaly_ts})`}
            className="absolute top-1/2 h-2 w-2 -translate-x-1/2 -translate-y-1/2 rotate-45 border border-paper bg-blue"
            style={{ left: `${anomalyLeft}%` }}
          />
        )}
      </div>
      <span
        style={{ width: TRAILING_WIDTH }}
        className="tabular shrink-0 text-12 text-mute"
        title={row.message ?? undefined}
      >
        {row.lead_time_weeks != null ? `${row.lead_time_weeks}w lead` : "-"}
      </span>
    </li>
  );
}

function Legend({ swatch, label, diamond }: { swatch: string; label: string; diamond?: boolean }) {
  return (
    <span className="flex items-center gap-1">
      <span className={`h-1.5 w-1.5 ${swatch} ${diamond ? "rotate-45" : ""}`} />
      {label}
    </span>
  );
}

function toSegments(weeks: BacktestRow["weekly_health"]) {
  const segments: { status: NonNullable<HealthStatus>; startWeek: number; endWeek: number }[] = [];
  for (const w of weeks) {
    if (!w.health_status) continue;
    const last = segments[segments.length - 1];
    if (last && last.status === w.health_status && last.endWeek === w.week - 1) {
      last.endWeek = w.week;
    } else {
      segments.push({ status: w.health_status, startWeek: w.week, endWeek: w.week });
    }
  }
  return segments;
}
