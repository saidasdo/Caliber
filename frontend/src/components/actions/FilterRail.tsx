import type { ActionStatus } from "../../lib/types";

const STATUSES: ActionStatus[] = ["Open", "In progress", "Done", "Rejected"];

// SPEC section 7: "narrow 3-column filter and count rail".
export function FilterRail({
  counts,
  status,
  onStatusChange,
  overdueOnly,
  onOverdueOnlyChange,
}: {
  counts: Record<string, number>;
  status: ActionStatus | null;
  onStatusChange: (s: ActionStatus | null) => void;
  overdueOnly: boolean;
  onOverdueOnlyChange: (v: boolean) => void;
}) {
  const total = Object.values(counts).reduce((a, b) => a + b, 0);

  return (
    <div className="border border-line bg-paper">
      <div className="border-b border-line px-2 py-1.5 text-12 font-semibold uppercase tracking-wide text-mute">
        Filter
      </div>
      <ul className="divide-y divide-line">
        <FilterRow label="All" count={total} active={status === null} onClick={() => onStatusChange(null)} />
        {STATUSES.map((s) => (
          <FilterRow
            key={s}
            label={s}
            count={counts[s] ?? 0}
            active={status === s}
            onClick={() => onStatusChange(s)}
          />
        ))}
      </ul>
      <label className="flex items-center gap-1.5 border-t border-line px-2 py-1.5 text-13 text-ink">
        <input
          type="checkbox"
          checked={overdueOnly}
          onChange={(e) => onOverdueOnlyChange(e.target.checked)}
        />
        Overdue only
      </label>
    </div>
  );
}

function FilterRow({
  label,
  count,
  active,
  onClick,
}: {
  label: string;
  count: number;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <li>
      <button
        type="button"
        onClick={onClick}
        className={`flex w-full items-center justify-between px-2 py-1.5 text-13 ${
          active ? "bg-ink text-white" : "text-ink hover:bg-canvas"
        }`}
      >
        <span>{label}</span>
        <span className="tabular">{count}</span>
      </button>
    </li>
  );
}
