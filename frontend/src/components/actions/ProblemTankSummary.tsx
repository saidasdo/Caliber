import type { Problem } from "../../lib/types";

const SOURCE_LABEL: Record<string, string> = {
  alert: "Alerts",
  incident: "Incidents in progress",
  rca: "RCA cases",
};
const SOURCE_DOT: Record<string, string> = {
  alert: "bg-red",
  incident: "bg-amber",
  rca: "bg-blue",
};

// SPEC section 5.7: "Problem Tank: backlog of open problems (from alerts, incidents in
// progress, RCA cases)."
export function ProblemTankSummary({
  counts,
  problems,
}: {
  counts: Record<string, number>;
  problems: Problem[];
}) {
  const total = Object.values(counts).reduce((a, b) => a + b, 0);

  return (
    <div className="border border-line bg-paper">
      <div className="flex items-center justify-between border-b border-line px-2 py-1.5">
        <span className="text-12 font-semibold uppercase tracking-wide text-mute">
          Problem Tank
        </span>
        <span className="tabular text-12 text-mute">{total} open</span>
      </div>
      <div className="flex divide-x divide-line">
        {(["alert", "rca", "incident"] as const).map((key) => (
          <div key={key} className="flex-1 px-2 py-1.5">
            <div className="flex items-center gap-1 text-12 text-mute">
              <span className={`h-1 w-1 rounded-full ${SOURCE_DOT[key]}`} />
              {SOURCE_LABEL[key]}
            </div>
            <div className="tabular font-display text-20 font-bold text-ink">
              {counts[key] ?? 0}
            </div>
          </div>
        ))}
      </div>
      <ul className="max-h-[220px] divide-y divide-line overflow-y-auto border-t border-line">
        {problems.slice(0, 20).map((p) => (
          <li key={p.id} className="flex items-center justify-between gap-2 px-2 py-1 text-12">
            <span className="flex items-center gap-1 truncate text-ink">
              <span className={`h-1 w-1 shrink-0 rounded-full ${SOURCE_DOT[p.source_type]}`} />
              {p.plant_code && <span className="tabular shrink-0 text-mute">{p.plant_code}</span>}
              <span className="truncate">{p.title}</span>
            </span>
            {p.priority_label && <span className="shrink-0 text-mute">{p.priority_label}</span>}
          </li>
        ))}
      </ul>
    </div>
  );
}
