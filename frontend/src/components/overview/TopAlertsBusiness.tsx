import { Link } from "react-router-dom";
import type { PriorityRow } from "../../lib/types";
import { PriorityChip } from "../ui/StatusChip";
import { Money } from "../ui/Money";
import { alertWordingExecutive } from "../../lib/alertWording";

// Phase 10 section 2 (Executive Overview): "top 5 alerts in business language." Led by the
// number an executive actually scans for (estimated impact), not a read-the-sentence list;
// the generated sentence is still there as a tooltip for anyone who wants the full wording.
export function TopAlertsBusiness({ rows }: { rows: PriorityRow[] }) {
  const top5 = rows.slice(0, 5);
  return (
    <div className="border border-line bg-paper">
      <div className="border-b border-line px-2 py-1.5 text-12 font-semibold uppercase tracking-wide text-mute">
        Top alerts
      </div>
      <ul className="divide-y divide-line">
        {top5.map((row) => (
          <li key={row.equipment_tag}>
            <Link
              to={`/equipment/${row.equipment_tag}`}
              title={alertWordingExecutive(row)}
              className="flex items-center justify-between gap-2 px-2 py-1.5 hover:bg-canvas"
            >
              <div className="flex items-center gap-1.5">
                <PriorityChip label={row.priority_label} />
                <span className="tabular font-display text-15 font-bold text-ink">{row.equipment_tag}</span>
                <span className="text-12 text-mute">{row.plant_code}</span>
              </div>
              <div className="text-right">
                <div className="tabular font-display text-20 font-bold text-ink">
                  <Money kusd={row.estimated_loss_kusd} fallback="-" />
                </div>
                <div className="text-12 text-mute">
                  {row.health_status === "TRIP" ? "production stop" : "trip risk"}
                </div>
              </div>
            </Link>
          </li>
        ))}
        {top5.length === 0 && <li className="px-2 py-2 text-13 text-mute">No alerts on this replay date.</li>}
      </ul>
    </div>
  );
}
