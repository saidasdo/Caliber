import type { WeeklySeriesParameter } from "../../lib/types";
import { WeeklyParameterChart } from "./WeeklyParameterChart";

// SPEC section 7: "weekly small multiples 2 x 2 in 7 columns". Weeks stop at the replay date.
export function WeeklySmallMultiples({
  parameters,
  axisWeeks,
}: {
  parameters: WeeklySeriesParameter[];
  axisWeeks: number;
}) {
  return (
    <div className="grid grid-cols-2 gap-2">
      {parameters.map((p) => (
        <WeeklyParameterChart key={p.parameter} series={p} axisWeeks={axisWeeks} />
      ))}
    </div>
  );
}
