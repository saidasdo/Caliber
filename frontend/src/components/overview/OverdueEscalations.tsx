import { useState } from "react";
import { Link } from "react-router-dom";
import { useAppState } from "../../state/AppStateContext";
import { getActions, escalateAction } from "../../lib/api";
import { useFetch } from "../../lib/useFetch";

// Phase 10 section 2 (Executive Overview) / section 4 (action rights: "Executive: ... press
// Escalate on overdue actions; escalated items appear at the top of the plant manager's
// page"). Lists every overdue action across all plants so the executive doesn't have to go
// plant by plant to find what to escalate.
export function OverdueEscalations() {
  const { replayDate } = useAppState();
  const [refreshKey, setRefreshKey] = useState(0);
  const actions = useFetch(() => getActions({ replayDate }), [replayDate, refreshKey]);
  const [busyId, setBusyId] = useState<number | null>(null);

  const overdue =
    actions.status === "ready" ? actions.data.results.filter((a) => a.overdue_days) : [];

  async function escalate(id: number) {
    setBusyId(id);
    try {
      await escalateAction(id, replayDate);
      setRefreshKey((k) => k + 1);
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="border border-line bg-paper">
      <div className="border-b border-line px-2 py-1.5 text-12 font-semibold uppercase tracking-wide text-mute">
        Overdue escalations
      </div>
      <ul className="divide-y divide-line">
        {overdue.map((a) => (
          <li key={a.id} className="flex items-center justify-between gap-1 px-2 py-1.5">
            <div className="min-w-0">
              {a.equipment_tag && (
                <Link to={`/equipment/${a.equipment_tag}`} className="tabular text-13 font-medium text-blue">
                  {a.equipment_tag}
                </Link>
              )}
              <p className="truncate text-12 text-mute" title={a.action_text}>
                {a.action_text} &middot; {a.overdue_days} d overdue
              </p>
            </div>
            {a.escalated === 1 ? (
              <span className="shrink-0 rounded bg-red px-1 py-0.5 text-12 font-semibold text-white">
                Escalated
              </span>
            ) : (
              <button
                type="button"
                disabled={busyId === a.id}
                onClick={() => escalate(a.id)}
                className="shrink-0 border border-red px-1.5 py-0.5 text-12 font-medium text-red disabled:opacity-50"
              >
                {busyId === a.id ? "..." : "Escalate"}
              </button>
            )}
          </li>
        ))}
        {overdue.length === 0 && (
          <li className="px-2 py-2 text-13 text-mute">Nothing overdue on this replay date.</li>
        )}
      </ul>
    </div>
  );
}
