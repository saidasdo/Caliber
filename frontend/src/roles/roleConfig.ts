import type { Role } from "../lib/types";

// Phase 10 section 1: "the only place that defines role behavior." Pages and components read
// this; nothing outside this file should branch on `role === "..."` for what to show, where
// to land, or what a role may do. The narrow exceptions are money visibility (already its own
// single source of truth, canSeeMoney in lib/money.ts, reused here rather than duplicated)
// and action-button gating, which lives next to ACTION_RIGHTS below.

export type WidgetState = "expanded" | "collapsed" | "hidden";

export type OverviewWidgetKey =
  | "kpiBand"
  | "priorityQueue"
  | "lossByPlant"
  | "heatmap"
  | "followUpPipeline"
  | "topAlertsBusiness"
  | "overdueEscalations";

export type PlantWidgetKey =
  | "plantKpis"
  | "equipmentTable"
  | "sensorDetail"
  | "downtimeByCause"
  | "rcaSummaries"
  | "incidentHistory"
  | "openActions"
  | "pendingProposals";

export type EquipmentWidgetKey =
  | "gauges"
  | "statusTimeline"
  | "weeklyCharts"
  | "hourlyTrend"
  | "diagnosisFull"
  | "diagnosisOneLiner"
  | "impactSummary"
  | "similarIncidents"
  | "suggestedActions"
  | "rcaEvidence"
  | "energyProxy";

interface RoleConfig {
  scope: "all" | "plant" | "equipment";
  landingRoute: (ctx: { selectedPlant: string | null; topAlertTag: string | null }) => string;
  overview: Record<OverviewWidgetKey, WidgetState>;
  plant: Record<PlantWidgetKey, WidgetState>;
  equipment: Record<EquipmentWidgetKey, WidgetState>;
}

export const ROLE_CONFIG: Record<Role, RoleConfig> = {
  Executive: {
    scope: "all",
    landingRoute: () => "/",
    overview: {
      kpiBand: "expanded",
      priorityQueue: "expanded",
      lossByPlant: "expanded",
      heatmap: "expanded",
      followUpPipeline: "expanded",
      topAlertsBusiness: "expanded",
      overdueEscalations: "expanded",
    },
    plant: {
      plantKpis: "expanded",
      equipmentTable: "expanded",
      sensorDetail: "collapsed",
      downtimeByCause: "expanded",
      rcaSummaries: "collapsed",
      incidentHistory: "collapsed",
      openActions: "expanded",
      pendingProposals: "hidden",
    },
    equipment: {
      gauges: "expanded",
      statusTimeline: "expanded",
      weeklyCharts: "expanded",
      hourlyTrend: "expanded",
      diagnosisFull: "expanded",
      diagnosisOneLiner: "hidden",
      impactSummary: "expanded",
      similarIncidents: "expanded",
      suggestedActions: "expanded",
      rcaEvidence: "expanded",
      energyProxy: "expanded",
    },
  },

  "Plant manager": {
    scope: "plant",
    landingRoute: ({ selectedPlant }) => (selectedPlant ? `/plant/${selectedPlant}` : "/"),
    overview: {
      kpiBand: "hidden",
      priorityQueue: "hidden",
      lossByPlant: "hidden",
      heatmap: "hidden",
      followUpPipeline: "hidden",
      topAlertsBusiness: "hidden",
      overdueEscalations: "hidden",
    },
    plant: {
      plantKpis: "expanded",
      equipmentTable: "expanded",
      sensorDetail: "expanded",
      downtimeByCause: "expanded",
      rcaSummaries: "expanded",
      incidentHistory: "collapsed",
      openActions: "expanded",
      pendingProposals: "expanded",
    },
    equipment: {
      gauges: "expanded",
      statusTimeline: "expanded",
      weeklyCharts: "expanded",
      hourlyTrend: "expanded",
      diagnosisFull: "expanded",
      diagnosisOneLiner: "hidden",
      impactSummary: "expanded",
      similarIncidents: "expanded",
      suggestedActions: "expanded",
      rcaEvidence: "expanded",
      energyProxy: "expanded",
    },
  },

  Engineer: {
    scope: "equipment",
    landingRoute: ({ topAlertTag }) => (topAlertTag ? `/equipment/${topAlertTag}` : "/"),
    overview: {
      kpiBand: "hidden",
      priorityQueue: "hidden",
      lossByPlant: "hidden",
      heatmap: "hidden",
      followUpPipeline: "hidden",
      topAlertsBusiness: "hidden",
      overdueEscalations: "hidden",
    },
    plant: {
      plantKpis: "expanded",
      equipmentTable: "expanded",
      sensorDetail: "expanded",
      downtimeByCause: "hidden",
      rcaSummaries: "hidden",
      incidentHistory: "hidden",
      openActions: "hidden",
      pendingProposals: "hidden",
    },
    equipment: {
      gauges: "expanded",
      statusTimeline: "expanded",
      weeklyCharts: "expanded",
      hourlyTrend: "expanded",
      diagnosisFull: "expanded",
      diagnosisOneLiner: "hidden",
      impactSummary: "hidden",
      similarIncidents: "expanded",
      suggestedActions: "expanded",
      rcaEvidence: "expanded",
      energyProxy: "expanded",
    },
  },
};

// Phase 10 section 4 ("Action rights"): who may click what. Checked by the UI to decide which
// buttons render at all ("buttons a role cannot use are not shown"); the backend (app.scope,
// app/api/actions.py) is the real enforcement, this just keeps the UI honest about it.
export const ACTION_RIGHTS: Record<Role, { label: string; key: string }[]> = {
  Executive: [
    { key: "comment", label: "Comment" },
    { key: "escalate", label: "Escalate" },
  ],
  "Plant manager": [
    { key: "approveProposal", label: "Approve" },
    { key: "rejectProposal", label: "Reject" },
    { key: "close", label: "Close" },
  ],
  Engineer: [
    { key: "confirmDiagnosis", label: "Confirm diagnosis" },
    { key: "rejectDiagnosis", label: "Reject diagnosis" },
    { key: "propose", label: "Propose action" },
    { key: "progress", label: "Update progress" },
  ],
};

export function canUseAction(role: Role, actionKey: string): boolean {
  return ACTION_RIGHTS[role].some((a) => a.key === actionKey);
}
