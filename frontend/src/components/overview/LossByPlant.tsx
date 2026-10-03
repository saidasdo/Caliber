import { Link } from "react-router-dom";
import type { PlantLoss } from "../../lib/types";
import { formatHours } from "../../lib/format";
import { useAppState } from "../../state/AppStateContext";
import { Money } from "../ui/Money";

// SPEC section 5.1: "Loss by plant for all 12 plants, sorted. Mark the 4 plants that have
// sensor-level equipment (ARP, ZCU, NUP, OPP). Click a plant opens level 2."
// SPEC 5.11: when loss is hidden for a row, the bar must not keep revealing its relative
// size either (that would leak the hidden number), so the bar switches to downtime hours.
export function LossByPlant({ plants }: { plants: PlantLoss[] }) {
  // loss_kusd is absent (not just hidden) on rows the viewing role can't see money for
  // (server-side redaction), so this has to filter before reducing or a single redacted row
  // poisons the max with NaN.
  const lossValues = plants.map((p) => p.loss_kusd).filter((v): v is number => v != null);
  const maxLoss = Math.max(...lossValues, 1);
  const maxDowntime = Math.max(...plants.map((p) => p.downtime_hrs), 1);

  return (
    <div className="border border-line bg-paper">
      <div className="border-b border-line px-2 py-1.5 text-12 font-semibold uppercase tracking-wide text-mute">
        Loss by plant
      </div>
      <ul className="divide-y divide-line">
        {plants.map((plant) => (
          <PlantRow key={plant.plant_code} plant={plant} maxLoss={maxLoss} maxDowntime={maxDowntime} />
        ))}
      </ul>
    </div>
  );
}

function PlantRow({
  plant,
  maxLoss,
  maxDowntime,
}: {
  plant: PlantLoss;
  maxLoss: number;
  maxDowntime: number;
}) {
  const { canSeeMoney } = useAppState();
  // Field presence, not just canSeeMoney(), since role can switch a render before a refetch
  // for the new role resolves (see KpiBand.tsx for the same reasoning).
  const moneyVisible = canSeeMoney(plant.plant_code) && plant.loss_kusd != null;
  const barPercent = moneyVisible
    ? (plant.loss_kusd! / maxLoss) * 100
    : (plant.downtime_hrs / maxDowntime) * 100;

  return (
    <li>
      <Link to={`/plant/${plant.plant_code}`} className="flex items-center gap-2 px-2 py-1 hover:bg-canvas">
        <span className="flex w-[64px] shrink-0 items-center gap-1 tabular text-13 font-medium text-ink">
          {plant.plant_code}
          {plant.has_sensor_equipment === 1 && (
            <span className="h-0.5 w-0.5 rounded-full bg-blue" title="Has sensor-level equipment" />
          )}
        </span>
        <span className="relative h-2 flex-1 bg-canvas">
          <span className="absolute inset-y-0 left-0 bg-blue" style={{ width: `${barPercent}%` }} />
        </span>
        <span className="tabular w-[80px] shrink-0 text-right text-13 text-ink">
          <Money kusd={plant.loss_kusd} plantCode={plant.plant_code} fallback={formatHours(plant.downtime_hrs)} />
        </span>
        <span className="tabular w-[32px] shrink-0 text-right text-12 text-mute">{plant.incident_count}</span>
      </Link>
    </li>
  );
}
