import type { StatusLane, StatusSegment } from "../../lib/types";
import { NoHourlyData } from "./NoHourlyData";

// SPEC section 5.3 / 7: "Machine status timeline like reference 1: lanes Running (green),
// Alarm (amber), Trip/Off (red), No data (gray)."
const LANE_ORDER: StatusLane[] = ["running", "alarm", "trip_off", "no_data"];
const LANE_LABEL: Record<StatusLane, string> = {
  running: "Running",
  alarm: "Alarm",
  trip_off: "Trip / Off",
  no_data: "No data",
};
const LANE_CLASS: Record<StatusLane, string> = {
  running: "bg-green",
  alarm: "bg-amber",
  trip_off: "bg-red",
  no_data: "bg-line",
};

export function MachineStatusTimeline({
  segments,
  hasHourlyCoverage,
  compact,
}: {
  segments: StatusSegment[];
  hasHourlyCoverage: boolean;
  // Just the single "Overview" lane, no border/header/per-lane breakdown: the real color bar
  // for a summary tile, not a bare number standing in for it. Click opens the full version.
  compact?: boolean;
}) {
  if (!hasHourlyCoverage || segments.length === 0) {
    return compact ? (
      <NoHourlyData height={32} />
    ) : (
      <div className="border border-line bg-paper">
        <div className="border-b border-line px-2 py-1.5 text-12 font-semibold uppercase tracking-wide text-mute">
          Machine status timeline
        </div>
        <NoHourlyData height={180} />
      </div>
    );
  }

  const totalHours = segments.reduce((sum, s) => sum + s.hours, 0);
  let cursor = 0;
  const positioned = segments.map((s) => {
    const left = (cursor / totalHours) * 100;
    cursor += s.hours;
    return { ...s, left, width: (s.hours / totalHours) * 100 };
  });

  if (compact) {
    return (
      <div className="flex h-full flex-col justify-center gap-1">
        <Lane label="" segments={positioned} filterLane={null} />
      </div>
    );
  }

  return (
    <div className="border border-line bg-paper">
      <div className="flex items-center justify-between border-b border-line px-2 py-1.5">
        <span className="text-12 font-semibold uppercase tracking-wide text-mute">
          Machine status timeline
        </span>
        <span className="tabular text-12 text-mute">
          {segments[0].start_ts.slice(0, 10)} to {segments[segments.length - 1].end_ts.slice(0, 10)}
        </span>
      </div>
      <div className="space-y-1 p-2">
        <Lane label="Overview" segments={positioned} filterLane={null} />
        {LANE_ORDER.map((lane) => (
          <Lane key={lane} label={LANE_LABEL[lane]} segments={positioned} filterLane={lane} />
        ))}
      </div>
    </div>
  );
}

function Lane({
  label,
  segments,
  filterLane,
}: {
  label: string;
  segments: (StatusSegment & { left: number; width: number })[];
  filterLane: StatusLane | null;
}) {
  return (
    <div className="flex items-center gap-2">
      {label && <span className="w-[72px] shrink-0 text-12 text-mute">{label}</span>}
      <div className="relative h-2 flex-1 bg-canvas">
        {segments
          .filter((s) => filterLane === null || s.lane === filterLane)
          .map((s, i) => (
            <div
              key={i}
              title={`${LANE_LABEL[s.lane]}: ${s.start_ts} to ${s.end_ts} (${s.hours}h)`}
              className={`absolute inset-y-0 ${LANE_CLASS[s.lane]}`}
              style={{ left: `${s.left}%`, width: `${Math.max(s.width, 0.15)}%` }}
            />
          ))}
      </div>
    </div>
  );
}
