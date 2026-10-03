import type { ActionStatus, TrackedAction } from "../../lib/types";

const STATUS_CLASS: Record<ActionStatus, string> = {
  Proposed: "border border-line text-mute",
  Open: "bg-line text-ink",
  "In progress": "bg-amber text-ink",
  Done: "bg-green text-white",
  Closed: "bg-ink text-white",
  Rejected: "bg-canvas text-mute",
};

const SOURCE_LABEL: Record<string, string> = {
  capa_preload: "CAPA (RCA)",
  diagnosis_suggestion: "Diagnosis",
  manual: "Manual",
};

// SPEC section 7: "9-column dense table". SPEC 5.7: "Dense, filterable table view, not a
// card board."
export function ActionsTable({
  actions,
  selectedId,
  onSelect,
}: {
  actions: TrackedAction[];
  selectedId: number | null;
  onSelect: (action: TrackedAction) => void;
}) {
  return (
    <div className="border border-line bg-paper">
      <table className="w-full text-13">
        <thead>
          <tr className="border-b border-line text-left text-12 text-mute">
            <th className="px-2 py-1 font-medium">Equipment</th>
            <th className="px-2 py-1 font-medium">Action</th>
            <th className="px-2 py-1 font-medium">Source</th>
            <th className="px-2 py-1 font-medium">PIC</th>
            <th className="px-2 py-1 font-medium">Due date</th>
            <th className="px-2 py-1 font-medium">Status</th>
            <th className="px-2 py-1 font-medium text-right">Overdue</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {actions.map((a) => (
            <tr
              key={a.id}
              onClick={() => onSelect(a)}
              className={`cursor-pointer ${selectedId === a.id ? "bg-canvas" : "hover:bg-canvas"}`}
            >
              <td className="tabular px-2 py-1.5 font-medium text-ink">
                {a.escalated === 1 && (
                  <span
                    className="mr-1 inline-block rounded bg-red px-1 py-0.5 text-12 font-semibold text-white"
                    title="Escalated by Executive"
                  >
                    !
                  </span>
                )}
                {a.equipment_tag ?? "-"}
              </td>
              <td className="max-w-[360px] truncate px-2 py-1.5 text-ink" title={a.action_text}>
                {a.action_text}
              </td>
              <td className="px-2 py-1.5 text-mute">{SOURCE_LABEL[a.source] ?? a.source}</td>
              <td className="px-2 py-1.5 text-mute">{a.pic ?? "-"}</td>
              <td className="tabular px-2 py-1.5 text-mute">{a.due_date ?? "-"}</td>
              <td className="px-2 py-1.5">
                <span className={`rounded px-1 py-0.5 text-12 font-semibold ${STATUS_CLASS[a.status]}`}>
                  {a.status}
                </span>
              </td>
              <td className="tabular px-2 py-1.5 text-right">
                {a.overdue_days ? <span className="text-red">{a.overdue_days} d</span> : <span className="text-mute">-</span>}
              </td>
            </tr>
          ))}
          {actions.length === 0 && (
            <tr>
              <td colSpan={7} className="px-2 py-3 text-center text-mute">
                No actions match this filter.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
