import { useState } from "react";
import { Link } from "react-router-dom";
import type { PriorityRow } from "../../lib/types";
import { HealthChip, PriorityChip } from "../ui/StatusChip";
import { formatHours } from "../../lib/format";

// Above this many plain tag codes, showing them all inline stops being glanceable and starts
// being a wall of chips; collapse behind a count + expand instead.
const INLINE_LIMIT = 8;

// SPEC section 5.2: "equipment table (status chip, class, worst parameter vs limit,
// priority)." Equipment without sensor data is listed separately as "Incident history only".
export function EquipmentTable({
  equipment,
  incidentOnlyTags,
}: {
  equipment: PriorityRow[];
  incidentOnlyTags: string[];
}) {
  const [expanded, setExpanded] = useState(false);
  const showToggle = incidentOnlyTags.length > INLINE_LIMIT;
  const visibleTags = showToggle && !expanded ? [] : incidentOnlyTags;

  return (
    <div className="border border-line bg-paper">
      <div className="border-b border-line px-2 py-1.5 text-12 font-semibold uppercase tracking-wide text-mute">
        Equipment
      </div>
      <table className="w-full text-13">
        <thead>
          <tr className="border-b border-line text-left text-12 text-mute">
            <th className="px-2 py-1 font-medium">Tag</th>
            <th className="px-2 py-1 font-medium">Class</th>
            <th className="px-2 py-1 font-medium">Status</th>
            <th className="px-2 py-1 font-medium">Worst parameter vs limit</th>
            <th className="px-2 py-1 font-medium text-right">MTBF</th>
            <th className="px-2 py-1 font-medium text-right">MTTR</th>
            <th className="px-2 py-1 font-medium">Priority</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {equipment.map((eq) => (
            <tr key={eq.equipment_tag} className="hover:bg-canvas">
              <td className="px-2 py-1.5">
                <Link to={`/equipment/${eq.equipment_tag}`} className="tabular font-medium text-blue">
                  {eq.equipment_tag}
                </Link>
              </td>
              <td className="tabular px-2 py-1.5 text-ink">{eq.breakdown.eq_class ?? "-"}</td>
              <td className="px-2 py-1.5">
                <HealthChip status={eq.health_status} />
              </td>
              <td className="px-2 py-1.5 text-ink">
                {eq.worst_parameter ? (
                  <span className="tabular">
                    {eq.worst_parameter.parameter} {eq.worst_parameter.value}
                    {eq.worst_parameter.unit} vs alarm {eq.worst_parameter.alarm}
                  </span>
                ) : (
                  <span className="text-mute">-</span>
                )}
              </td>
              <td className="tabular px-2 py-1.5 text-right text-ink">
                {eq.reliability?.mtbf_hours != null ? (
                  formatHours(eq.reliability.mtbf_hours)
                ) : (
                  <span className="text-12 text-mute">{eq.reliability?.message ?? "-"}</span>
                )}
              </td>
              <td className="tabular px-2 py-1.5 text-right text-ink">
                {eq.reliability?.mttr_hours != null ? (
                  formatHours(eq.reliability.mttr_hours)
                ) : (
                  <span className="text-12 text-mute">-</span>
                )}
              </td>
              <td className="px-2 py-1.5">
                <PriorityChip label={eq.priority_label} />
              </td>
            </tr>
          ))}
          {equipment.length === 0 && (
            <tr>
              <td colSpan={7} className="px-2 py-2 text-mute">
                No sensor-equipped equipment in this plant.
              </td>
            </tr>
          )}
        </tbody>
      </table>
      {incidentOnlyTags.length > 0 && (
        <div className="border-t border-line px-2 py-1.5">
          <div className="flex items-center justify-between">
            <span className="text-12 text-mute">
              Incident history only (no sensor data) &middot; {incidentOnlyTags.length} equipment
            </span>
            {showToggle && (
              <button
                type="button"
                onClick={() => setExpanded((v) => !v)}
                className="text-12 text-blue"
              >
                {expanded ? "Hide list" : "Show list"}
              </button>
            )}
          </div>
          {visibleTags.length > 0 && (
            <div className="mt-1 flex flex-wrap gap-1">
              {visibleTags.map((tag) => (
                <span key={tag} className="tabular border border-line px-1 py-0.5 text-12 text-mute">
                  {tag}
                </span>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
