import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import type { PriorityRow, WorstParameter } from "../../lib/types";
import { PriorityChip } from "../ui/StatusChip";
import { BulletBar } from "../ui/BulletBar";
import { priorityCardStyle } from "../../lib/priorityCardStyle";

// Direction-aware: a value only reads as "at or past the line" once it's actually crossed
// its alarm in the bad direction, not just whenever a number happens to be large.
function isAtOrPastAlarm(p: WorstParameter): boolean {
  if (p.alarm == null || p.value == null) return false;
  return p.direction === "lower_is_worse" ? p.value <= p.alarm : p.value >= p.alarm;
}

// SPEC section 5.1: "Priority queue: ranked list of current alerts (section 5.4) with
// priority chip, tag, plant, one-line reason. Click opens the equipment page."
export function PriorityQueue({
  rows,
  headerAction,
}: {
  rows: PriorityRow[];
  headerAction?: ReactNode;
}) {
  return (
    <div className="flex h-full flex-col border border-line bg-paper">
      <div className="flex items-center justify-between border-b border-line px-2 py-1.5 text-12 font-semibold uppercase tracking-wide text-mute">
        Priority queue
        {headerAction}
      </div>
      <ul className="flex-1 divide-y divide-line overflow-y-auto">
        {rows.map((row, i) => {
          const style = priorityCardStyle(row.priority_label);
          return (
            <li key={row.equipment_tag}>
              <Link
                to={`/equipment/${row.equipment_tag}`}
                className={`flex flex-col gap-0.5 px-2 py-1.5 ${style.container} ${
                  style.container ? "hover:brightness-95" : "hover:bg-canvas"
                }`}
                title={`severity ${row.breakdown.severity} x0.4 + class ${row.breakdown.class_score} x0.3 + loss exposure ${row.breakdown.loss_exposure} x0.3 = ${row.priority_score}`}
              >
                <div className="flex items-center justify-between gap-1">
                  <span className={`tabular text-12 ${style.body}`}>#{i + 1}</span>
                  <PriorityChip label={row.priority_label} inverted={style.invertedChip} />
                </div>
                <div className="flex items-baseline gap-1">
                  <span className={`tabular font-display text-15 font-bold ${style.heading}`}>
                    {row.equipment_tag}
                  </span>
                  <span className={`text-12 ${style.body}`}>{row.plant_code}</span>
                </div>
                {row.worst_parameter && (
                  <>
                    <div className={`flex items-center justify-between text-12 ${style.body}`}>
                      <span>{row.worst_parameter.parameter}</span>
                      <span className="tabular">
                        {row.worst_parameter.value}
                        {row.worst_parameter.alarm != null && <> / {row.worst_parameter.alarm}</>}
                      </span>
                    </div>
                    <BulletBar
                      value={row.worst_parameter.value}
                      limit={row.worst_parameter.alarm}
                      danger={isAtOrPastAlarm(row.worst_parameter)}
                      inverted={style.invertedChip}
                    />
                  </>
                )}
                <div className="mt-0.5 flex items-center gap-1">
                  <div className="relative h-1 flex-1 bg-canvas/60">
                    <div
                      className={style.invertedChip ? "absolute inset-y-0 left-0 bg-white" : "absolute inset-y-0 left-0 bg-ink"}
                      style={{ width: `${Math.round(row.priority_score * 100)}%` }}
                    />
                  </div>
                  <span className={`tabular text-12 ${style.body}`}>
                    {Math.round(row.priority_score * 100)}%
                  </span>
                </div>
              </Link>
            </li>
          );
        })}
        {rows.length === 0 && (
          <li className="px-2 py-2 text-12 text-mute">No alerts on this replay date.</li>
        )}
      </ul>
    </div>
  );
}
