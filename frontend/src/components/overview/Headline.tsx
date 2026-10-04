import type { PriorityRow } from "../../lib/types";

// One generated sentence from the priority queue on the replay date. Counts only what is in alarm
// or trip; the critical count is the priority label, so it can differ from the alarm count.
export function headlineFor(rows: PriorityRow[]): string {
  // Medium or above needs attention; Critical is the subset that needs it first.
  const attention = rows.filter((r) => r.priority_label !== "Normal").length;
  const critical = rows.filter((r) => r.priority_label === "Critical").length;
  if (attention === 0) return "All machines normal";
  const machines = `${attention} machine${attention === 1 ? "" : "s"} need${attention === 1 ? "s" : ""} attention`;
  return critical > 0 ? `${machines}, ${critical} critical` : `${machines}`;
}

export function Headline({ rows }: { rows: PriorityRow[] }) {
  return <h1 className="font-display stretch-semi-expanded text-20 font-bold text-ink">{headlineFor(rows)}</h1>;
}
