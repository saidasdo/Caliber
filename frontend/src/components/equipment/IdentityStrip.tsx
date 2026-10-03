import type { EquipmentDetail } from "../../lib/types";
import { HealthChip } from "../ui/StatusChip";

// SPEC section 5.3: "Identity strip: tag, name, type, plant, class, status chip."
export function IdentityStrip({ equipment }: { equipment: EquipmentDetail }) {
  return (
    <div className="flex items-center justify-between border border-line bg-paper px-2 py-1.5">
      <div className="flex items-baseline gap-2">
        <h1 className="tabular font-display stretch-semi-expanded text-28 font-bold text-ink">
          {equipment.tag}
        </h1>
        <span className="text-15 text-ink">{equipment.name}</span>
      </div>
      <div className="flex items-center divide-x divide-line text-13 text-mute">
        <span className="px-1.5">{equipment.eq_type}</span>
        <span className="px-1.5">{equipment.plant_code}</span>
        <span className="px-1.5">Class {equipment.eq_class ?? "-"}</span>
        <span className="px-1.5">{equipment.criticality ?? "-"} criticality</span>
        <span className="pl-1.5">
          <HealthChip status={equipment.weekly_state?.health_status ?? null} />
        </span>
      </div>
    </div>
  );
}
