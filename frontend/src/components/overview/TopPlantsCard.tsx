import type { PlantLoss } from "../../lib/types";
import { formatHours } from "../../lib/format";
import { Money } from "../ui/Money";

// Tier 3, left: the three plants with the most loss. Loss is money, so it is absent for roles that
// can't see it; the card then falls back to downtime, as the plant chart does.
export function TopPlantsCard({ plants, onShowAll }: { plants: PlantLoss[]; onShowAll: () => void }) {
  const top = plants.slice(0, 3);
  return (
    <div className="flex h-full flex-col border border-line bg-paper">
      <div className="flex items-center justify-between border-b border-line px-2 py-1.5">
        <span className="text-12 font-semibold uppercase tracking-wide text-mute">Top plants by loss</span>
        <button type="button" onClick={onShowAll} className="text-12 text-blue">
          All {plants.length} plants
        </button>
      </div>
      <ul className="flex-1 divide-y divide-line">
        {top.map((p, i) => (
          <li key={p.plant_code} className="flex items-center justify-between px-2 py-2">
            <div className="flex items-baseline gap-2">
              <span className="tabular text-12 text-mute">#{i + 1}</span>
              <span className="tabular font-display text-15 font-bold text-ink">{p.plant_code}</span>
            </div>
            <span className="tabular font-display text-20 font-bold text-ink">
              {p.loss_kusd != null ? <Money kusd={p.loss_kusd} plantCode={p.plant_code} /> : formatHours(p.downtime_hrs)}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
