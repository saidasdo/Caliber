import { useEffect, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { useAppState } from "../state/AppStateContext";
import {
  getActions,
  getEquipment,
  getEquipmentStatusTimeline,
  getEquipmentSuggestedActions,
  getEquipmentWeeklySeries,
} from "../lib/api";
import { useFetch } from "../lib/useFetch";
import { useLogViewMoney } from "../lib/useLogViewMoney";
import { colors } from "../styles/tokens";
import { ROLE_CONFIG, canUseAction, type EquipmentWidgetKey } from "../roles/roleConfig";
import type { Signal } from "../lib/types";
import { Modal } from "../components/ui/Modal";
import { ChartTile } from "../components/ui/ChartTile";
import { RotatingPanel, type RotatingSlide } from "../components/ui/RotatingPanel";
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
import { EmissionDetail, EmissionTile } from "../components/equipment/EmissionTile";

const GAUGE_SPECS = [
  { key: "availability" as const, title: "Availability", min: 0, max: 100, unit: "%" },
  { key: "health_margin" as const, title: "Health margin to trip", min: -20, max: 120, unit: "%" },
  { key: "production_vs_normal" as const, title: "Production vs normal", min: 0, max: 150, unit: "%" },
];
const GAUGE_COLOR_STOPS: Record<string, [number, string][]> = {
  availability: [
    [0.9, colors.red],
    [0.99, colors.amber],
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

type ModalKey = "gauges" | "statusTimeline" | "trends" | "energyProxy" | "emission";

// Health margin bands come from the response, not fixed numbers: red below 0 (beyond trip),
// amber from 0 up to the highest alarm margin across parameters, green above it (engine/gauges.py).
function healthMarginStops(min: number, max: number, alarmMarginPct: number | null): [number, string][] {
  const fraction = (v: number) => Math.min(1, Math.max(0, (v - min) / (max - min)));
  if (alarmMarginPct == null) return [[fraction(0), colors.red], [1, colors.green]];
  return [
    [fraction(0), colors.red],
    [fraction(alarmMarginPct), colors.amber],
    [1, colors.green],
  ];
}

// Two tabs on one machine. Overview (the default) is the glance: gauges, status timeline,
// the rotating trends and the energy proxy, sized to fill the window. Action (?view=action)
// holds everything about the problem (root cause, similar incidents, suggested actions, RCA
// evidence) inside one red "A problem occurred" group, and is the tab that beeps while an
// alarm is waiting for someone to act. Detail behind any chart opens as a pop-up on click.
export function EquipmentPage() {
  const { tag = "" } = useParams<{ tag: string }>();
  const [searchParams] = useSearchParams();
  const view = searchParams.get("view") === "action" ? "action" : "overview";
  const { replayDate, role, setActionDue } = useAppState();
  const [modal, setModal] = useState<ModalKey | null>(null);
  // Bumped when a suggested action is proposed or rejected, so the beep and the list refresh.
  const [actionsVersion, setActionsVersion] = useState(0);
  const onActionsChanged = () => setActionsVersion((v) => v + 1);

  const equipment = useFetch(() => getEquipment(tag, replayDate), [tag, replayDate, role]);
  const timeline = useFetch(() => getEquipmentStatusTimeline(tag, replayDate), [tag, replayDate]);
  const weekly = useFetch(() => getEquipmentWeeklySeries(tag, replayDate), [tag, replayDate]);
  const suggested = useFetch(
    () => getEquipmentSuggestedActions(tag, replayDate),
    [tag, replayDate, role, actionsVersion],
  );
  const tracked = useFetch(
    () => getActions({ replayDate, equipmentTag: tag, source: "diagnosis_suggestion" }),
    [tag, replayDate, role, actionsVersion],
  );
  useLogViewMoney("equipment", equipment.status === "ready" ? equipment.data.plant_code : undefined);

  const healthStatus = equipment.status === "ready" ? equipment.data.weekly_state?.health_status : null;
  const isProblem = healthStatus === "ALARM" || healthStatus === "TRIP";
  const canAct = canUseAction(role, "propose") || canUseAction(role, "approveProposal");
  // "An action to do": a suggestion that no tracked action covers yet (same matching the
  // suggestion rows use to show Proposed/Approved state).
  const actionDue =
    isProblem &&
    canAct &&
    suggested.status === "ready" &&
    tracked.status === "ready" &&
    suggested.data.suggestions.some(
      (s) =>
        !tracked.data.results.some(
          (a) =>
            a.action_text === s.action_text &&
            (s.source_capa_action_id === null || a.capa_action_id === s.source_capa_action_id),
        ),
    );

  useEffect(() => {
    setActionDue(actionDue);
    return () => setActionDue(false);
  }, [actionDue, setActionDue]);

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

  const alarmHours =
    timeline.status === "ready" ? timeline.data.distribution.find((d) => d.lane === "alarm")?.duration_hours : undefined;

  const weeklyParams = weekly.status === "ready" ? weekly.data.parameters : [];
  const axisWeeks = weekly.status === "ready" ? weekly.data.axis_weeks : 0;
  const timelineData = timeline.status === "ready" ? timeline.data : null;
  const weeklySlides: RotatingSlide[] = weeklyParams.map((p) => ({
    key: `w-${p.parameter}`,
    caption: p.parameter,
    content: <WeeklyParameterChart series={p} axisWeeks={axisWeeks} compact />,
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

  // Overview is taller than the window on purpose (the page scrolls): every number needs room.
  // Action keeps the single-window layout so its problem group scrolls inside itself.
  const rootClass =
    view === "action" ? "flex h-full flex-col gap-1 overflow-hidden pb-14" : "flex flex-col gap-1 pb-14";

  return (
    <div className={rootClass}>
      <div className="shrink-0">
        <IdentityStrip equipment={eq} />
      </div>

      {view === "overview" && (
        <>
          {(show("impactSummary") || show("diagnosisOneLiner")) && (
            <div className="grid shrink-0 grid-cols-12 gap-1">
              {show("impactSummary") && (
                <div className={show("diagnosisOneLiner") ? "col-span-6" : "col-span-12"}>
                  <ImpactSummaryCard equipment={eq} />
                </div>
              )}
              {show("diagnosisOneLiner") && (
                <div className={show("impactSummary") ? "col-span-6" : "col-span-12"}>
                  <DiagnosisOneLiner diagnosis={eq.diagnosis} />
                </div>
              )}
            </div>
          )}

          {/* The three main gauges, biggest on the page */}
          {show("gauges") && (
            <div className="grid h-[200px] shrink-0 grid-cols-3 gap-1">
              {GAUGE_SPECS.map((g) => (
                <ChartTile key={g.key} label={g.title} onClick={() => setModal("gauges")}>
                  <GaugeCard
                    title={g.title}
                    gauge={gauges[g.key]}
                    min={g.min}
                    max={g.max}
                    unit={g.unit}
                    colorStops={
                      g.key === "health_margin"
                        ? healthMarginStops(g.min, g.max, gauges.health_margin.alarm_margin_pct)
                        : GAUGE_COLOR_STOPS[g.key]
                    }
                    compact
                  />
                </ChartTile>
              ))}
            </div>
          )}

          {/* Each panel cycles its own charts; click for all of them */}
          {(show("weeklyCharts") || show("hourlyTrend")) && (
            <div className="grid h-[330px] shrink-0 grid-cols-2 gap-1">
              {show("weeklyCharts") && (
                <RotatingPanel label="Weekly trend" slides={weeklySlides} onOpen={() => setModal("trends")} />
              )}
              {show("hourlyTrend") && (
                <RotatingPanel label="Hourly trend" slides={hourlySlides} onOpen={() => setModal("trends")} />
              )}
            </div>
          )}

          {show("energyProxy") && (
            <div className="grid h-[300px] shrink-0 grid-cols-12 gap-1">
              <div className="col-span-8">
                <ChartTile label="Energy proxy" sublabel="motor load index" onClick={() => setModal("energyProxy")}>
                  <EnergyProxyPanel tag={tag} replayDate={replayDate} compact />
                </ChartTile>
              </div>
              <div className="col-span-4">
                <ChartTile
                  label="Emission estimate"
                  sublabel="estimate from motor current, not metered; factors are placeholders"
                  onClick={() => setModal("emission")}
                >
                  <EmissionTile emission={eq.emission} />
                </ChartTile>
              </div>
            </div>
          )}

          {show("statusTimeline") && (
            <div className="h-[200px] shrink-0">
              <ChartTile
                label="Status timeline"
                sublabel={alarmHours != null ? `${alarmHours.toFixed(0)}h in alarm` : undefined}
                onClick={() => setModal("statusTimeline")}
              >
                <MachineStatusTimeline
                  segments={timelineData?.segments ?? []}
                  windowStart={timelineData?.window_start ?? null}
                  axisHours={timelineData?.axis_hours ?? 0}
                  replayDate={replayDate}
                  hasHourlyCoverage={eq.has_hourly_coverage}
                  compact
                />
              </ChartTile>
            </div>
          )}
        </>
      )}

      {view === "action" &&
        (isProblem ? (
          <div className="flex min-h-0 flex-1 flex-col overflow-hidden border border-red">
            <div className="shrink-0 bg-red px-2 py-0.5 text-12 font-semibold uppercase tracking-wide text-white">
              A problem occurred
            </div>
            {/* Scrolls when the panels run longer than the window; each panel stays at full size */}
            <div className="grid min-h-0 flex-1 auto-rows-min grid-cols-2 content-start gap-1 overflow-y-auto p-1">
              {show("diagnosisFull") && <DiagnosisPanel diagnosis={eq.diagnosis} tag={tag} replayDate={replayDate} />}
              {show("similarIncidents") && <SimilarIncidentsPanel incidents={eq.similar_incidents} />}
              {show("suggestedActions") && (
                <SuggestedActionsPanel tag={tag} replayDate={replayDate} onChange={onActionsChanged} />
              )}
              {show("rcaEvidence") && <RcaEvidencePanel rca={eq.linked_rca} pastRcas={eq.past_rcas} />}
            </div>
          </div>
        ) : (
          <div className="border border-line bg-paper px-2 py-3 text-13 text-mute">
            No active problem on this machine. Nothing needs action right now.
          </div>
        ))}

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
                segments={timelineData?.segments ?? []}
                windowStart={timelineData?.window_start ?? null}
                axisHours={timelineData?.axis_hours ?? 0}
                replayDate={replayDate}
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
            {weekly.status === "ready" && <WeeklySmallMultiples parameters={weeklyParams} axisWeeks={axisWeeks} />}
            <HourlyTrendChart tag={tag} replayDate={replayDate} hasHourlyCoverage={eq.has_hourly_coverage} />
          </div>
        </Modal>
      )}
      {modal === "emission" && (
        <Modal title="Emission estimate" onClose={() => setModal(null)}>
          <EmissionDetail emission={eq.emission} />
        </Modal>
      )}
      {modal === "energyProxy" && (
        <Modal title="Energy proxy" onClose={() => setModal(null)} wide>
          <div className="p-1">
            <EnergyProxyPanel tag={tag} replayDate={replayDate} />
          </div>
        </Modal>
      )}
    </div>
  );
}
