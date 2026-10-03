import { useState } from "react";
import { useParams } from "react-router-dom";
import { useAppState } from "../state/AppStateContext";
import { getEquipment, getEquipmentStatusTimeline, getEquipmentWeeklySeries } from "../lib/api";
import { useFetch } from "../lib/useFetch";
import { useLogViewMoney } from "../lib/useLogViewMoney";
import { colors } from "../styles/tokens";
import { ROLE_CONFIG, type EquipmentWidgetKey } from "../roles/roleConfig";
import type { Signal } from "../lib/types";
import { Modal } from "../components/ui/Modal";
import { SummaryTile } from "../components/ui/SummaryTile";
import { ChartTile } from "../components/ui/ChartTile";
import { RotatingPanel, type RotatingSlide } from "../components/ui/RotatingPanel";
import { BulletBar } from "../components/ui/BulletBar";
import { IdentityStrip } from "../components/equipment/IdentityStrip";
import { GaugeCard } from "../components/equipment/GaugeCard";
import { MachineStatusTimeline } from "../components/equipment/MachineStatusTimeline";
import { DistributionPanel } from "../components/equipment/DistributionPanel";
import { WeeklySmallMultiples } from "../components/equipment/WeeklySmallMultiples";
import { WeeklyParameterChart } from "../components/equipment/WeeklyParameterChart";
import { HourlyTrendChart } from "../components/equipment/HourlyTrendChart";
import { DiagnosisPanel } from "../components/equipment/DiagnosisPanel";
import { DiagnosisOneLiner } from "../components/equipment/DiagnosisOneLiner";
import { ImpactSummaryCard } from "../components/equipment/ImpactSummaryCard";
import { SimilarIncidentsPanel } from "../components/equipment/SimilarIncidentsPanel";
import { SuggestedActionsPanel } from "../components/equipment/SuggestedActionsPanel";
import { RcaEvidencePanel } from "../components/equipment/RcaEvidencePanel";
import { EnergyProxyPanel } from "../components/equipment/EnergyProxyPanel";

const GAUGE_SPECS = [
  { key: "availability" as const, title: "Availability", min: 0, max: 100, unit: "%" },
  { key: "health_margin" as const, title: "Health margin to trip", min: -20, max: 100, unit: "%" },
  { key: "production_vs_normal" as const, title: "Production vs normal", min: 0, max: 150, unit: "%" },
];
const GAUGE_COLOR_STOPS: Record<string, [number, string][]> = {
  availability: [
    [0.9, colors.red],
    [0.99, colors.amber],
    [1, colors.green],
  ],
  health_margin: [
    [0.167, colors.red],
    [0.333, colors.amber],
    [1, colors.green],
  ],
  production_vs_normal: [
    [0.467, colors.red],
    [0.6, colors.amber],
    [1, colors.green],
  ],
};
const SIGNAL_LABEL: Record<Signal, string> = {
  vibration: "Vibration",
  temperature: "Temperature",
  motor_current: "Motor current",
  discharge_pressure: "Discharge pressure",
  feed: "Feed",
  plant_rate: "Plant rate",
};

// Layout (top to bottom): the three main gauges, status timeline, two rotating trend panels,
// the problem group (only when the machine is actually in ALARM or TRIP), energy proxy. Each
// chart shows inline; the number and detail behind it open in a pop-up on click.
export function EquipmentPage() {
  const { tag = "" } = useParams<{ tag: string }>();
  const { replayDate, role, overview } = useAppState();
  const [modal, setModal] = useState<EquipmentWidgetKey | "trends" | null>(null);

  const equipment = useFetch(() => getEquipment(tag, replayDate), [tag, replayDate, role]);
  const timeline = useFetch(() => getEquipmentStatusTimeline(tag), [tag]);
  const weekly = useFetch(() => getEquipmentWeeklySeries(tag), [tag]);
  useLogViewMoney("equipment", equipment.status === "ready" ? equipment.data.plant_code : undefined);

  if (equipment.status === "loading") {
    return <div className="p-3 text-13 text-mute">Loading equipment...</div>;
  }
  if (equipment.status === "error") {
    return (
      <div className="border border-line bg-paper p-3 text-13 text-red">
        Could not load {tag}: {equipment.error}
      </div>
    );
  }

  const eq = equipment.data;
  const { gauges } = eq;
  const widgets = ROLE_CONFIG[role].equipment;
  const show = (key: EquipmentWidgetKey) => widgets[key] !== "hidden";
  const priorityRow =
    overview.status === "ready" ? overview.data.priority_queue.find((r) => r.equipment_tag === tag) : undefined;

  const status = eq.weekly_state?.health_status;
  const isProblem = status === "ALARM" || status === "TRIP";
  const problemTiles = [
    show("diagnosisFull") && "diagnosis",
    show("similarIncidents") && "similar",
    show("suggestedActions") && "suggested",
    show("rcaEvidence") && "rca",
  ].filter(Boolean) as string[];
  const showProblemGroup = isProblem && problemTiles.length > 0;

  const alarmHours =
    timeline.status === "ready" ? timeline.data.distribution.find((d) => d.lane === "alarm")?.duration_hours : undefined;

  const weeklyParams = weekly.status === "ready" ? weekly.data.parameters : [];
  const weeklySlides: RotatingSlide[] = weeklyParams.map((p) => ({
    key: `w-${p.parameter}`,
    caption: p.parameter,
    content: <WeeklyParameterChart series={p} replayDate={replayDate} compact />,
  }));
  const hourlySlides: RotatingSlide[] = eq.has_hourly_coverage
    ? eq.hourly_signals.map((sig) => ({
        key: `h-${sig}`,
        caption: SIGNAL_LABEL[sig],
        content: (
          <HourlyTrendChart
            tag={tag}
            replayDate={replayDate}
            hasHourlyCoverage={eq.has_hourly_coverage}
            compact
            signal={sig}
          />
        ),
      }))
    : [];

  return (
    <div className="flex h-full flex-col gap-1 overflow-hidden pb-14">
      <div className="shrink-0">
        <IdentityStrip equipment={eq} />
      </div>

      {(show("impactSummary") || show("diagnosisOneLiner")) && (
        <div className="grid shrink-0 grid-cols-12 gap-1">
          {show("impactSummary") && (
            <div className={show("diagnosisOneLiner") ? "col-span-6" : "col-span-12"}>
              <ImpactSummaryCard equipment={eq} priorityRow={priorityRow} />
            </div>
          )}
          {show("diagnosisOneLiner") && (
            <div className={show("impactSummary") ? "col-span-6" : "col-span-12"}>
              <DiagnosisOneLiner diagnosis={eq.diagnosis} />
            </div>
          )}
        </div>
      )}

      {/* Row 1: the main three, biggest on the page */}
      {show("gauges") && (
        <div className="grid min-h-0 flex-[3] grid-cols-3 gap-1">
          {GAUGE_SPECS.map((g) => (
            <ChartTile key={g.key} label={g.title} onClick={() => setModal("gauges")}>
              <GaugeCard
                title={g.title}
                gauge={gauges[g.key]}
                min={g.min}
                max={g.max}
                unit={g.unit}
                colorStops={GAUGE_COLOR_STOPS[g.key]}
                compact
              />
            </ChartTile>
          ))}
        </div>
      )}

      {/* Row 2: status timeline */}
      {show("statusTimeline") && (
        <div className="min-h-0 flex-[1.3]">
          <ChartTile
            label="Status timeline"
            sublabel={alarmHours != null ? `${alarmHours.toFixed(0)}h in alarm` : undefined}
            onClick={() => setModal("statusTimeline")}
          >
            <MachineStatusTimeline
              segments={timeline.status === "ready" ? timeline.data.segments : []}
              hasHourlyCoverage={eq.has_hourly_coverage}
              compact
            />
          </ChartTile>
        </div>
      )}

      {/* Row 3: rotating trends (each panel cycles its own charts; click for all of them) */}
      {(show("weeklyCharts") || show("hourlyTrend")) && (
        <div className="grid min-h-0 flex-[2.5] grid-cols-2 gap-1">
          {show("weeklyCharts") && (
            <RotatingPanel label="Weekly trend" slides={weeklySlides} onOpen={() => setModal("trends")} />
          )}
          {show("hourlyTrend") && (
            <RotatingPanel label="Hourly trend" slides={hourlySlides} onOpen={() => setModal("trends")} />
          )}
        </div>
      )}

      {/* Row 4: the problem group, only while the machine is in alarm or trip */}
      {showProblemGroup && (
        <div className="flex min-h-[170px] flex-[2.6] flex-col overflow-hidden border border-red">
          <div className="shrink-0 bg-red px-2 py-0.5 text-12 font-semibold uppercase tracking-wide text-white">
            A problem occurred
          </div>
          <div className="grid min-h-0 flex-1 grid-cols-4 gap-1 overflow-hidden p-1">
            {problemTiles.includes("diagnosis") && (
              <ChartTile
                label={`Root cause hint ${eq.diagnosis.rule_name ? `${eq.diagnosis.passes}/${eq.diagnosis.of}` : ""}`}
                sublabel={eq.diagnosis.confidence ?? "no confident hint"}
                onClick={() => setModal("diagnosisFull")}
              >
                <div className="flex h-full flex-col justify-center gap-1">
                  {eq.diagnosis.conditions.slice(0, 2).map((c, i) => (
                    <div key={i}>
                      <div className="truncate text-12 text-mute">{c.parameter}</div>
                      <BulletBar value={c.value} limit={c.limit} danger={c.pass} />
                    </div>
                  ))}
                  {eq.diagnosis.conditions.length === 0 && (
                    <span className="text-12 text-mute">No confident hint</span>
                  )}
                </div>
              </ChartTile>
            )}
            {problemTiles.includes("similar") && (
              <SummaryTile
                label="Similar incidents"
                value={eq.similar_incidents.length}
                sublabel="top matches"
                onClick={() => setModal("similarIncidents")}
              />
            )}
            {problemTiles.includes("suggested") && (
              <SummaryTile
                label="Suggested actions"
                value="View"
                sublabel="from diagnosis"
                onClick={() => setModal("suggestedActions")}
              />
            )}
            {problemTiles.includes("rca") && (
              <SummaryTile
                label="RCA evidence"
                value={eq.linked_rca ? "Available" : "None"}
                sublabel="4P, 4M+1E, chronology"
                onClick={() => setModal("rcaEvidence")}
              />
            )}
          </div>
        </div>
      )}

      {/* Row 5: energy proxy */}
      {show("energyProxy") && (
        <div className="min-h-[90px] flex-[1.2] overflow-hidden">
          <ChartTile label="Energy proxy" sublabel="motor load index" onClick={() => setModal("energyProxy")}>
            <EnergyProxyPanel tag={tag} compact />
          </ChartTile>
        </div>
      )}

      {modal === "gauges" && (
        <Modal title="Gauges" onClose={() => setModal(null)} wide>
          <div className="grid grid-cols-3 gap-1 p-1">
            {GAUGE_SPECS.map((g) => (
              <GaugeCard
                key={g.key}
                title={g.title}
                gauge={gauges[g.key]}
                min={g.min}
                max={g.max}
                unit={g.unit}
                colorStops={GAUGE_COLOR_STOPS[g.key]}
              />
            ))}
          </div>
        </Modal>
      )}
      {modal === "statusTimeline" && (
        <Modal title="Machine status timeline" onClose={() => setModal(null)} wide>
          <div className="grid grid-cols-12 gap-1 p-1">
            <div className="col-span-9">
              <MachineStatusTimeline
                segments={timeline.status === "ready" ? timeline.data.segments : []}
                hasHourlyCoverage={eq.has_hourly_coverage}
              />
            </div>
            <div className="col-span-3">
              <DistributionPanel
                distribution={timeline.status === "ready" ? timeline.data.distribution : []}
                hasHourlyCoverage={eq.has_hourly_coverage}
              />
            </div>
          </div>
        </Modal>
      )}
      {modal === "trends" && (
        <Modal title="Trends" onClose={() => setModal(null)} wide>
          <div className="space-y-2 p-1">
            {weekly.status === "ready" && <WeeklySmallMultiples parameters={weeklyParams} replayDate={replayDate} />}
            <HourlyTrendChart tag={tag} replayDate={replayDate} hasHourlyCoverage={eq.has_hourly_coverage} />
          </div>
        </Modal>
      )}
      {modal === "diagnosisFull" && (
        <Modal title="Root cause hint" onClose={() => setModal(null)}>
          <DiagnosisPanel diagnosis={eq.diagnosis} tag={tag} replayDate={replayDate} />
        </Modal>
      )}
      {modal === "similarIncidents" && (
        <Modal title="Similar incidents" onClose={() => setModal(null)}>
          <SimilarIncidentsPanel incidents={eq.similar_incidents} />
        </Modal>
      )}
      {modal === "suggestedActions" && (
        <Modal title="Suggested actions" onClose={() => setModal(null)}>
          <SuggestedActionsPanel tag={tag} replayDate={replayDate} />
        </Modal>
      )}
      {modal === "rcaEvidence" && (
        <Modal title="RCA evidence" onClose={() => setModal(null)} wide>
          <RcaEvidencePanel rca={eq.linked_rca} />
        </Modal>
      )}
      {modal === "energyProxy" && (
        <Modal title="Energy proxy" onClose={() => setModal(null)} wide>
          <div className="p-1">
            <EnergyProxyPanel tag={tag} />
          </div>
        </Modal>
      )}
    </div>
  );
}
