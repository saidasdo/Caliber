import type { ReactNode } from "react";
import type { FollowUpPipeline as FollowUpPipelineData } from "../../lib/types";

// SPEC section 5.1: "Follow-up pipeline: incident counts per Overall Status (...) plus
// overdue counts." Order follows the process flow, not the count.
const STATUS_ORDER = [
  "NEW REGISTERED",
  "RCA PROCESS",
  "CA/PA EXECUTION",
  "MONITORING RESULT",
  "RISK CLOSED",
  "RISK CANCELED",
];

export function FollowUpPipeline({
  data,
  headerAction,
}: {
  data: FollowUpPipelineData;
  headerAction?: ReactNode;
}) {
  const max = Math.max(...Object.values(data.by_status), 1);

  return (
    <div className="flex h-full flex-col border border-line bg-paper">
      <div className="flex items-center justify-between border-b border-line px-2 py-1.5 text-12 font-semibold uppercase tracking-wide text-mute">
        Follow-up pipeline
        {headerAction}
      </div>
      <ul className="divide-y divide-line">
        {STATUS_ORDER.map((status) => {
          const count = data.by_status[status] ?? 0;
          return (
            <li key={status} className="px-2 py-1">
              <div className="flex items-center justify-between text-12">
                <span className="text-mute">{status}</span>
                <span className="tabular font-medium text-ink">{count}</span>
              </div>
              <div className="mt-0.5 h-0.5 bg-canvas">
                <div className="h-full bg-blue" style={{ width: `${(count / max) * 100}%` }} />
              </div>
            </li>
          );
        })}
      </ul>
      <div className="mt-auto border-t border-line px-2 py-1.5">
        <div className="flex items-center justify-between">
          <span className="text-12 text-mute">RCA PROCESS overdue</span>
          <span className="tabular text-15 font-display font-bold text-orange">
            {data.rca_process_overdue}
          </span>
        </div>
      </div>
    </div>
  );
}
