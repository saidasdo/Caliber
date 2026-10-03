import { useAppState } from "../../state/AppStateContext";
import { getActions } from "../../lib/api";
import { useFetch } from "../../lib/useFetch";
import { Money } from "../ui/Money";
import { HealthChip } from "../ui/StatusChip";
import type { EquipmentDetail, PriorityRow } from "../../lib/types";

const CONSEQUENCE: Record<string, string> = {
  TRIP: "production stop",
  ALARM: "trip risk",
  NORMAL: "no active risk",
};

// Phase 10 section 2 (executive equipment page): "impact summary card (what could stop,
// estimated impact, status of the response)." Three number tiles, same shape as the KPI band
// everywhere else in the app, instead of three sentences.
export function ImpactSummaryCard({
  equipment,
  priorityRow,
}: {
  equipment: EquipmentDetail;
  priorityRow: PriorityRow | undefined;
}) {
  const { replayDate } = useAppState();
  const actions = useFetch(
    () => getActions({ replayDate, equipmentTag: equipment.tag }),
    [replayDate, equipment.tag],
  );
  const open =
    actions.status === "ready"
      ? actions.data.results.filter(
          (a) => a.status === "Open" || a.status === "In progress" || a.status === "Proposed",
        )
      : [];
  const status = equipment.weekly_state?.health_status;

  return (
    <div className="flex h-full divide-x divide-line border border-line bg-paper">
      <div className="flex-1 px-2 py-1.5">
        <div className="text-12 uppercase tracking-wide text-mute">Status</div>
        <div className="mt-0.5">
          <HealthChip status={status ?? null} />
        </div>
        <div className="mt-0.5 text-12 text-mute">{status ? CONSEQUENCE[status] : "no data"}</div>
      </div>
      <div className="flex-1 px-2 py-1.5">
        <div className="text-12 uppercase tracking-wide text-mute">Estimated impact</div>
        <div className="tabular font-display stretch-semi-expanded text-28 text-ink">
          <Money kusd={priorityRow?.estimated_loss_kusd} plantCode={equipment.plant_code} fallback="-" />
        </div>
      </div>
      <div className="flex-1 px-2 py-1.5">
        <div className="text-12 uppercase tracking-wide text-mute">Response</div>
        <div className="tabular font-display stretch-semi-expanded text-28 text-ink">{open.length}</div>
        <div className="text-12 text-mute">action{open.length === 1 ? "" : "s"} in progress</div>
      </div>
    </div>
  );
}
