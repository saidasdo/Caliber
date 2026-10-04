import { useState } from "react";
import { Link } from "react-router-dom";
import { useAppState } from "../../state/AppStateContext";
import type { HealthStatus } from "../../lib/types";
import type { PriorityRow } from "../../lib/types";

const STATUS_DOT: Record<NonNullable<HealthStatus>, string> = {
  TRIP: "bg-red",
  ALARM: "bg-amber",
  NORMAL: "bg-green",
};

const STATUS_RANK: Record<NonNullable<HealthStatus>, number> = { TRIP: 2, ALARM: 1, NORMAL: 0 };

function worstStatus(equipment: { health_status: HealthStatus }[]): HealthStatus {
  let worst: HealthStatus = null;
  for (const eq of equipment) {
    if (!eq.health_status) continue;
    if (!worst || STATUS_RANK[eq.health_status] > STATUS_RANK[worst]) worst = eq.health_status;
  }
  return worst;
}

// SPEC section 7: "asset tree panel (plants, then equipment, with count badges, 240 px)".
export function AssetTree() {
  const { overview } = useAppState();
  const [expanded, setExpanded] = useState<Set<string>>(new Set(["ZCU"]));
  const [collapsed, setCollapsed] = useState(false);

  if (collapsed) {
    return (
      <aside className="flex w-3 shrink-0 flex-col items-center border-r border-line bg-paper py-1.5">
        <button
          type="button"
          onClick={() => setCollapsed(false)}
          aria-label="Show plants panel"
          className="flex h-2.5 w-2.5 items-center justify-center text-mute hover:text-ink"
        >
          <svg viewBox="0 0 12 12" width="9" height="9" className="fill-current">
            <path d="M3 2l4 4-4 4z" />
          </svg>
        </button>
      </aside>
    );
  }

  if (overview.status !== "ready") {
    return (
      <aside className="shrink-0 border-r border-line bg-paper p-2" style={{ width: 240 }}>
        <div className="text-12 text-mute">
          {overview.status === "loading" ? "Loading assets..." : "Assets unavailable"}
        </div>
      </aside>
    );
  }

  const { loss_by_plant, priority_queue } = overview.data;
  const equipmentByPlant = new Map<string, typeof priority_queue>();
  for (const row of priority_queue) {
    const list = equipmentByPlant.get(row.plant_code) ?? [];
    list.push(row);
    equipmentByPlant.set(row.plant_code, list);
  }

  // Worst-first: plants with a live TRIP/ALARM sort above quieter ones, ties broken by the
  // highest individual priority score, and plants with no sensor equipment (no status to
  // rank) sort last.
  const sortedPlants = [...loss_by_plant].sort((a, b) => {
    const eqA = equipmentByPlant.get(a.plant_code) ?? [];
    const eqB = equipmentByPlant.get(b.plant_code) ?? [];
    const rankA = eqA.length ? STATUS_RANK[worstStatus(eqA) ?? "NORMAL"] : -1;
    const rankB = eqB.length ? STATUS_RANK[worstStatus(eqB) ?? "NORMAL"] : -1;
    if (rankA !== rankB) return rankB - rankA;
    const bestRank = (eq: PriorityRow[]) => eq.reduce((m, r) => Math.min(m, r.rank ?? 99), 99);
    return bestRank(eqA) - bestRank(eqB);
  });

  function toggle(plantCode: string) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(plantCode)) next.delete(plantCode);
      else next.add(plantCode);
      return next;
    });
  }

  return (
    <aside
      className="flex shrink-0 flex-col overflow-y-auto border-r border-line bg-paper"
      style={{ width: 240 }}
    >
      <div className="flex items-center justify-between border-b border-line px-2 py-1.5 text-12 font-semibold uppercase tracking-wide text-mute">
        Plants
        <button
          type="button"
          onClick={() => setCollapsed(true)}
          aria-label="Hide plants panel"
          className="flex h-2.5 w-2.5 items-center justify-center normal-case text-mute hover:text-ink"
        >
          <svg viewBox="0 0 12 12" width="9" height="9" className="fill-current">
            <path d="M9 2L5 6l4 4z" />
          </svg>
        </button>
      </div>
      <ul>
        {sortedPlants.map((plant) => {
          const equipment = equipmentByPlant.get(plant.plant_code) ?? [];
          const isExpandable = plant.has_sensor_equipment === 1 && equipment.length > 0;
          const isOpen = expanded.has(plant.plant_code);
          return (
            <li key={plant.plant_code} className="border-b border-line">
              <div className="flex items-center gap-1 px-2 py-1.5">
                {isExpandable ? (
                  <button
                    type="button"
                    onClick={() => toggle(plant.plant_code)}
                    aria-label={isOpen ? "Collapse" : "Expand"}
                    className="flex h-2 w-2 shrink-0 items-center justify-center text-mute"
                  >
                    <svg
                      viewBox="0 0 12 12"
                      width="10"
                      height="10"
                      className={`fill-current transition-transform ${isOpen ? "rotate-90" : ""}`}
                    >
                      <path d="M4 2l4 4-4 4z" />
                    </svg>
                  </button>
                ) : (
                  <span className="h-2 w-2 shrink-0" />
                )}
                <span
                  className={`h-1 w-1 shrink-0 rounded-full ${
                    equipment.length ? STATUS_DOT[worstStatus(equipment) ?? "NORMAL"] : "bg-line"
                  }`}
                  title={equipment.length ? (worstStatus(equipment) ?? "NORMAL") : "No sensor equipment"}
                />
                <Link
                  to={`/plant/${plant.plant_code}`}
                  className="flex-1 truncate text-13 font-medium text-ink hover:text-blue"
                >
                  {plant.plant_code}
                </Link>
              </div>
              {isExpandable && isOpen && (
                <ul className="pb-1">
                  {equipment.map((eq) => (
                    <li key={eq.equipment_tag}>
                      <Link
                        to={`/equipment/${eq.equipment_tag}`}
                        className="flex items-center gap-1.5 py-1 pl-5 pr-2 text-13 text-mute hover:text-blue"
                      >
                        <span
                          className={`h-1 w-1 shrink-0 rounded-full ${
                            eq.health_status ? STATUS_DOT[eq.health_status] : "bg-line"
                          }`}
                        />
                        <span className="tabular truncate">{eq.equipment_tag}</span>
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </li>
          );
        })}
      </ul>
    </aside>
  );
}
