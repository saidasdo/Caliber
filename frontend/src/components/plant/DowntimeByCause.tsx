import type { PlantDetail } from "../../lib/types";

// Phase 10 section 2 (plant manager page): "downtime causes (from incidents of this plant
// grouped by F Mechanism and Component)." Backend: app/api/plants.py _downtime_by_cause.
export function DowntimeByCause({ rows }: { rows: PlantDetail["downtime_by_cause"] }) {
  const max = Math.max(...rows.map((r) => r.downtime_hrs), 1);
  return (
    <div className="border border-line bg-paper">
      <div className="border-b border-line px-2 py-1.5 text-12 font-semibold uppercase tracking-wide text-mute">
        Downtime by cause
      </div>
      <ul className="divide-y divide-line">
        {rows.map((row) => (
          <li key={`${row.component}-${row.mechanism}`} className="flex items-center gap-2 px-2 py-1.5">
            <span className="w-[200px] shrink-0 truncate text-13 text-ink" title={`${row.component} / ${row.mechanism}`}>
              {row.component} <span className="text-mute">/ {row.mechanism}</span>
            </span>
            <span className="relative h-2 flex-1 bg-canvas">
              <span
                className="absolute inset-y-0 left-0 bg-blue"
                style={{ width: `${(row.downtime_hrs / max) * 100}%` }}
              />
            </span>
            <span className="tabular w-[70px] shrink-0 text-right text-13 text-ink">
              {row.downtime_hrs.toFixed(1)} h
            </span>
          </li>
        ))}
        {rows.length === 0 && (
          <li className="px-2 py-2 text-13 text-mute">No incidents with downtime on or before the replay date.</li>
        )}
      </ul>
    </div>
  );
}
