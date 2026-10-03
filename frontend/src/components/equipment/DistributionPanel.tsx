import type { StatusDistribution, StatusLane } from "../../lib/types";
import { NoHourlyData } from "./NoHourlyData";

const LANE_LABEL: Record<StatusLane, string> = {
  running: "Running",
  alarm: "Alarm",
  trip_off: "Trip / Off",
  no_data: "No data",
};
const LANE_TEXT_CLASS: Record<StatusLane, string> = {
  running: "text-green",
  alarm: "text-amber",
  trip_off: "text-red",
  no_data: "text-mute",
};

// SPEC section 5.3: status timeline "...with a distribution panel (duration and occurrences)."
export function DistributionPanel({
  distribution,
  hasHourlyCoverage,
}: {
  distribution: StatusDistribution[];
  hasHourlyCoverage: boolean;
}) {
  if (!hasHourlyCoverage || distribution.length === 0) {
    return (
      <div className="h-full border border-line bg-paper">
        <div className="border-b border-line px-2 py-1.5 text-12 font-semibold uppercase tracking-wide text-mute">
          Distribution
        </div>
        <NoHourlyData height={180} />
      </div>
    );
  }

  return (
    <div className="h-full border border-line bg-paper">
      <div className="border-b border-line px-2 py-1.5 text-12 font-semibold uppercase tracking-wide text-mute">
        Distribution
      </div>
      <ul className="divide-y divide-line">
        {distribution.map((d) => (
          <li key={d.lane} className="px-2 py-1.5">
            <div className="flex items-center justify-between">
              <span className={`text-13 font-medium ${LANE_TEXT_CLASS[d.lane]}`}>
                {LANE_LABEL[d.lane]}
              </span>
              <span className="tabular text-13 text-ink">{d.duration_hours} h</span>
            </div>
            <div className="text-12 text-mute">
              {d.occurrences} occurrence{d.occurrences === 1 ? "" : "s"}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
