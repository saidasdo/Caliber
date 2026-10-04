import type { StatusLane, StatusSegment } from "../../lib/types";
import { HOUR_MS, TICK_EVERY_HOURS, dayLabel, hourIndex, replayEndIndex, tsToMs } from "../../lib/replayAxis";
import { NoHourlyData } from "./NoHourlyData";

// SPEC section 5.3 / 7: Running (green), Alarm (amber) and Trip / Off (red), one lane each, so every
// state reads on its own row. A tick every three days lets you read a lane against dates. The area
// after the replay date stays empty as a grey band (replay rule, SPEC 4).
const LANES: { lane: StatusLane; label: string; className: string }[] = [
  { lane: "running", label: "Running", className: "bg-green" },
  { lane: "alarm", label: "Alarm", className: "bg-amber" },
  { lane: "trip_off", label: "Trip / Off", className: "bg-red" },
];

export function MachineStatusTimeline({
  segments,
  windowStart,
  axisHours,
  replayDate,
  hasHourlyCoverage,
  compact,
}: {
  segments: StatusSegment[];
  windowStart: string | null;
  axisHours: number;
  replayDate: string;
  hasHourlyCoverage: boolean;
  // Overview tile: the same three lanes, shorter. The pop-up uses taller lanes.
  compact?: boolean;
}) {
  if (!hasHourlyCoverage || !windowStart || axisHours === 0) {
    return <NoHourlyData height={compact ? 32 : 180} />;
  }

  const startMs = tsToMs(windowStart);
  const lastIndex = Math.min(axisHours - 1, replayEndIndex(windowStart, replayDate));
  const pct = (hours: number) => (hours / axisHours) * 100;

  const bars = segments
    .filter((s) => s.lane !== "no_data")
    .map((s) => ({ ...s, left: pct(hourIndex(windowStart, s.start_ts)), width: pct(s.hours) }));

  const ticks: { left: number; label: string }[] = [];
  for (let h = 0; h <= lastIndex; h += TICK_EVERY_HOURS) {
    ticks.push({ left: pct(h), label: dayLabel(startMs + h * HOUR_MS) });
  }

  // Explicit heights: the custom palette has no spacing scale for these sizes.
  const laneHeight = compact ? 14 : 22;

  return (
    <div className="flex h-full flex-col justify-center gap-1">
      {LANES.map((l) => (
        <div key={l.lane} className="flex items-center gap-2">
          <span className="w-16 shrink-0 text-12 text-mute">{l.label}</span>
          <div className="relative w-full bg-canvas" style={{ height: laneHeight }}>
            {ticks.map((t, i) => (
              <div key={i} className="absolute inset-y-0 w-px bg-line" style={{ left: `${t.left}%` }} />
            ))}
            {bars
              .filter((s) => s.lane === l.lane)
              .map((s, i) => (
                <div
                  key={i}
                  title={`${l.label}: ${s.start_ts} to ${s.end_ts} (${s.hours}h)`}
                  className={`absolute inset-y-0 ${l.className}`}
                  style={{ left: `${s.left}%`, width: `${Math.max(s.width, 0.15)}%` }}
                />
              ))}
            {lastIndex < axisHours - 1 && (
              <div
                className="absolute inset-y-0 border-l border-dashed border-mute"
                style={{
                  left: `${pct(lastIndex + 1)}%`,
                  width: `${pct(axisHours - lastIndex - 1)}%`,
                  backgroundColor: "#E4E6EA",
                }}
              />
            )}
          </div>
        </div>
      ))}
      <div className="flex items-start gap-2">
        <div className="w-16 shrink-0" />
        <div className="relative h-4 w-full">
          {ticks.map((t, i) => (
            <span
              key={i}
              className="tabular absolute top-0 whitespace-nowrap text-12 text-mute"
              style={{ left: `${t.left}%`, transform: t.left > 0 ? "translateX(-50%)" : undefined }}
            >
              {t.label}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
