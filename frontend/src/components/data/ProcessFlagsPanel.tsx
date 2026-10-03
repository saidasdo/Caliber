import type { ProcessFlagsResponse } from "../../lib/types";
import { formatDate } from "../../lib/format";

// SPEC section 6: "Process flags (real data, shown in a separate 'Follow-up health' section,
// not as data errors)."
export function ProcessFlagsPanel({ data }: { data: ProcessFlagsResponse }) {
  const metrics = [
    {
      label: "RCA PROCESS past due date",
      count: data.rca_process_overdue.count,
      ofTotal: data.rca_process_overdue.of_total,
      detail: null as string | null,
    },
    {
      label: "NEW REGISTERED older than 90 days",
      count: data.new_registered_stale.count,
      ofTotal: data.new_registered_stale.of_total,
      detail: data.new_registered_stale.oldest_date
        ? `Oldest: ${formatDate(data.new_registered_stale.oldest_date)}`
        : null,
    },
    {
      label: "Incidents without AR No.",
      count: data.incidents_without_ar_no.count,
      ofTotal: data.incidents_without_ar_no.of_total,
      detail: null,
    },
  ];

  return (
    <div className="border border-line bg-paper">
      <div className="flex items-center justify-between border-b border-line px-2 py-1.5">
        <span className="text-12 font-semibold uppercase tracking-wide text-mute">
          Follow-up health
        </span>
        <span className="text-12 text-mute">as of {formatDate(data.replay_date)}, not data errors</span>
      </div>
      <div className="flex divide-x divide-line">
        {metrics.map((m) => (
          <div key={m.label} className="flex-1 px-2 py-1.5">
            <div className="text-12 text-mute">{m.label}</div>
            <div className="tabular font-display stretch-semi-expanded text-28 text-orange">
              {m.count}
              <span className="text-15 text-mute"> / {m.ofTotal}</span>
            </div>
            {m.detail && <div className="text-12 text-mute">{m.detail}</div>}
          </div>
        ))}
      </div>
    </div>
  );
}
