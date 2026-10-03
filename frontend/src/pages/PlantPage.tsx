import { Link, useParams } from "react-router-dom";
import { useAppState } from "../state/AppStateContext";
import { getPlant } from "../lib/api";
import { useFetch } from "../lib/useFetch";
import { useLogViewMoney } from "../lib/useLogViewMoney";
import { formatHours } from "../lib/format";
import { ROLE_CONFIG } from "../roles/roleConfig";
import { EquipmentTable } from "../components/plant/EquipmentTable";
import { IncidentHistoryTable } from "../components/plant/IncidentHistoryTable";
import { DowntimeByCause } from "../components/plant/DowntimeByCause";
import { RcaSummaries } from "../components/plant/RcaSummaries";
import { PendingProposals } from "../components/plant/PendingProposals";
import { ActionsTable } from "../components/actions/ActionsTable";
import { Money } from "../components/ui/Money";

const ROW_HEIGHT = 340;

// SPEC section 5.2: "Plant KPIs, equipment table (...), incident history, open actions."
// Phase 10 section 2 adds downtime-by-cause, RCA summaries and a plant-manager approval
// queue, each shown or hidden per ROLE_CONFIG.plant. Like Overview, this page is sized to fit
// one screen: incident history and RCA summaries are summary tiles that open a pop-up (they're
// genuinely long reads), open actions and downtime-by-cause keep their own fixed-height
// internal scroll instead of growing the page.
export function PlantPage() {
  const { plantCode = "" } = useParams<{ plantCode: string }>();
  const { replayDate, canSeeMoney, role, selectedPlant } = useAppState();
  const plant = useFetch(() => getPlant(plantCode, replayDate), [plantCode, replayDate, role, selectedPlant]);
  useLogViewMoney("plant", plantCode);
  const widgets = ROLE_CONFIG[role].plant;

  if (plant.status === "loading") {
    return <div className="p-3 text-13 text-mute">Loading plant...</div>;
  }
  if (plant.status === "error") {
    return (
      <div className="border border-line bg-paper p-3 text-13 text-red">
        Could not load {plantCode}: {plant.error}
      </div>
    );
  }

  const p = plant.data;
  const alarmEquipment = p.equipment.filter(
    (eq) => eq.health_status === "ALARM" || eq.health_status === "TRIP",
  );
  const hasTrip = alarmEquipment.some((eq) => eq.health_status === "TRIP");

  return (
    <div className="flex h-full flex-col gap-1.5 overflow-hidden">
      <div className="flex items-center justify-between border border-line bg-paper px-2 py-1">
        <h1 className="font-display text-15 font-semibold text-mute">
          {p.plant_name ? `${p.plant_name} (${p.plant_code})` : p.plant_code}
        </h1>
        <div className="flex items-center gap-2">
          {!p.has_sensor_equipment && (
            <span className="text-12 text-mute">No sensor-level equipment in this plant</span>
          )}
          {role === "Plant manager" && (
            <Link to="/?all=1" className="text-12 text-blue">
              View all plants
            </Link>
          )}
        </div>
      </div>

      {alarmEquipment.length > 0 && (
        <div
          className={`shrink-0 flex items-center gap-1.5 px-2 py-1.5 text-13 font-semibold ${
            hasTrip ? "bg-red text-white" : "bg-amber text-ink"
          }`}
        >
          <span className="tabular">
            {alarmEquipment.length} equipment in {hasTrip ? "TRIP/ALARM" : "ALARM"}:
          </span>
          {alarmEquipment.map((eq, i) => (
            <span key={eq.equipment_tag} className="tabular">
              <Link to={`/equipment/${eq.equipment_tag}`} className="underline hover:no-underline">
                {eq.equipment_tag}
              </Link>
              {i < alarmEquipment.length - 1 ? "," : ""}
            </span>
          ))}
        </div>
      )}

      {widgets.pendingProposals !== "hidden" && (
        <div className="max-h-[160px] shrink-0 overflow-y-auto">
          <PendingProposals plantCode={p.plant_code} replayDate={replayDate} />
        </div>
      )}

      <div className="flex shrink-0 divide-x divide-line border border-line bg-paper">
        <KpiCell label="Incidents" value={String(p.kpis.incident_count)} />
        <KpiCell label="Downtime" value={formatHours(p.kpis.downtime_hrs)} />
        {canSeeMoney(p.plant_code) && (
          <div className="flex-1 px-2 py-1.5">
            <div className="text-12 uppercase tracking-wide text-mute">Loss</div>
            <div className="tabular font-display stretch-semi-expanded text-28 text-ink">
              <Money kusd={p.kpis.loss_kusd} plantCode={p.plant_code} />
            </div>
          </div>
        )}
      </div>

      <div className="shrink-0">
        <EquipmentTable equipment={p.equipment} incidentOnlyTags={p.incident_only_tags} />
      </div>

      <div className="grid min-h-0 flex-1 grid-cols-12 gap-1.5" style={{ height: ROW_HEIGHT }}>
        {widgets.downtimeByCause !== "hidden" && (
          <div className="col-span-4 min-h-0 overflow-y-auto">
            <DowntimeByCause rows={p.downtime_by_cause} />
          </div>
        )}
        {(widgets.incidentHistory !== "hidden" || widgets.rcaSummaries !== "hidden") && (
          <div className="col-span-3 flex min-h-0 flex-col gap-1.5">
            {widgets.incidentHistory !== "hidden" && (
              <div className="min-h-0 flex-1">
                <IncidentHistoryTable rows={p.incident_history} plantCode={p.plant_code} />
              </div>
            )}
            {widgets.rcaSummaries !== "hidden" && (
              <div className="min-h-0 flex-1">
                <RcaSummaries rows={p.rca_summaries} />
              </div>
            )}
          </div>
        )}
        {widgets.openActions !== "hidden" && (
          <div className="col-span-5 flex min-h-0 flex-col border border-line bg-paper">
            <div className="flex items-center justify-between border-b border-line px-2 py-1.5">
              <span className="text-12 font-semibold uppercase tracking-wide text-mute">
                Open actions
              </span>
              <Link to={`/actions?plant=${p.plant_code}`} className="text-12 text-blue">
                View all in Actions
              </Link>
            </div>
            <div className="min-h-0 flex-1 overflow-y-auto">
              {p.open_actions.length === 0 ? (
                <div className="p-2 text-13 text-mute">No open tracked actions for this plant's equipment.</div>
              ) : (
                <ActionsTable actions={p.open_actions} selectedId={null} onSelect={() => {}} />
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function KpiCell({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex-1 px-2 py-1.5">
      <div className="text-12 uppercase tracking-wide text-mute">{label}</div>
      <div className="tabular font-display stretch-semi-expanded text-28 text-ink">{value}</div>
    </div>
  );
}
