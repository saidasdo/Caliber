import type {
  ActionComment,
  ActionsResponse,
  ActionStatus,
  AnomalyResponse,
  AuditLogEntry,
  BacktestResponse,
  DataQualityResponse,
  DiagnosisReview,
  EnergyProxyResponse,
  EquipmentDetail,
  HourlySeries,
  KpiDictionaryResponse,
  OverviewResponse,
  PlantDetail,
  ProblemsResponse,
  ProcessFlagsResponse,
  ReplayConfig,
  ResetDemoDataResponse,
  Signal,
  SourceMapResponse,
  StatusTimeline,
  SuggestedActionsResponse,
  TrackedAction,
  WeeklySeries,
  Assumption,
} from "./types";
import { getRequestHeaders } from "./requestScope";

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(path, { headers: getRequestHeaders() });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${path} -> ${res.status}: ${body}`);
  }
  return res.json() as Promise<T>;
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getRequestHeaders() },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${path} -> ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

async function patchJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(path, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...getRequestHeaders() },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${path} -> ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export function getOverview(replayDate: string): Promise<OverviewResponse> {
  return getJson(`/api/overview?replay_date=${encodeURIComponent(replayDate)}`);
}

export function getReplayConfig(): Promise<ReplayConfig> {
  return getJson("/api/replay");
}

export function getPlant(plantCode: string, replayDate: string): Promise<PlantDetail> {
  return getJson(
    `/api/plants/${encodeURIComponent(plantCode)}?replay_date=${encodeURIComponent(replayDate)}`,
  );
}

export function getEquipment(tag: string, replayDate: string): Promise<EquipmentDetail> {
  return getJson(
    `/api/equipment/${encodeURIComponent(tag)}?replay_date=${encodeURIComponent(replayDate)}`,
  );
}

// Every live read takes the replay date: the backend never returns anything after it (SPEC 4).
export function getEquipmentStatusTimeline(tag: string, replayDate: string): Promise<StatusTimeline> {
  return getJson(
    `/api/equipment/${encodeURIComponent(tag)}/status-timeline?replay_date=${encodeURIComponent(replayDate)}`,
  );
}

export function getEquipmentWeeklySeries(tag: string, replayDate: string): Promise<WeeklySeries> {
  return getJson(
    `/api/equipment/${encodeURIComponent(tag)}/weekly-series?replay_date=${encodeURIComponent(replayDate)}`,
  );
}

export function getEquipmentSeries(tag: string, signal: Signal, replayDate: string): Promise<HourlySeries> {
  return getJson(
    `/api/equipment/${encodeURIComponent(tag)}/series?signal=${encodeURIComponent(signal)}&replay_date=${encodeURIComponent(replayDate)}`,
  );
}

export function getEquipmentAnomalies(tag: string, signal: Signal, replayDate: string): Promise<AnomalyResponse> {
  return getJson(
    `/api/equipment/${encodeURIComponent(tag)}/anomalies?signal=${encodeURIComponent(signal)}&replay_date=${encodeURIComponent(replayDate)}`,
  );
}

export function getEquipmentSuggestedActions(
  tag: string,
  replayDate: string,
): Promise<SuggestedActionsResponse> {
  return getJson(
    `/api/equipment/${encodeURIComponent(tag)}/suggested-actions?replay_date=${encodeURIComponent(replayDate)}`,
  );
}

export function getProblems(replayDate: string, sourceType?: string, plantCode?: string): Promise<ProblemsResponse> {
  const params = new URLSearchParams({ replay_date: replayDate });
  if (sourceType) params.set("source_type", sourceType);
  if (plantCode) params.set("plant_code", plantCode);
  return getJson(`/api/problems?${params}`);
}

export function getActions(params: {
  replayDate: string;
  status?: string;
  equipmentTag?: string;
  source?: string;
  plantCode?: string;
}): Promise<ActionsResponse> {
  const query = new URLSearchParams({ replay_date: params.replayDate });
  if (params.status) query.set("status", params.status);
  if (params.equipmentTag) query.set("equipment_tag", params.equipmentTag);
  if (params.source) query.set("source", params.source);
  if (params.plantCode) query.set("plant_code", params.plantCode);
  return getJson(`/api/actions?${query}`);
}

export function approveAction(body: {
  equipment_tag: string;
  action_text: string;
  pic: string;
  due_date: string;
  source_capa_action_id?: number | null;
  actor_role?: string;
}): Promise<TrackedAction> {
  return postJson("/api/actions/approve", body);
}

export function rejectAction(body: {
  equipment_tag: string;
  action_text: string;
  reason: string;
  source_capa_action_id?: number | null;
  actor_role?: string;
}): Promise<TrackedAction> {
  return postJson("/api/actions/reject", body);
}

export function updateActionStatus(
  id: number,
  status: ActionStatus,
  actorRole?: string,
  note?: string,
): Promise<TrackedAction> {
  return patchJson(`/api/actions/${id}`, { status, actor_role: actorRole, note });
}

// --- Phase 10: role-gated action flow (SPEC phase 10 section 4) ----------------------------

export function proposeAction(body: {
  equipment_tag: string;
  action_text: string;
  source_capa_action_id?: number | null;
}): Promise<TrackedAction> {
  return postJson("/api/actions/propose", body);
}

export function approveProposal(id: number, body: { pic: string; due_date: string }): Promise<TrackedAction> {
  return postJson(`/api/actions/${id}/approve-proposal`, body);
}

export function rejectProposal(id: number, reason: string): Promise<TrackedAction> {
  return postJson(`/api/actions/${id}/reject-proposal`, { reason });
}

export function closeAction(id: number): Promise<TrackedAction> {
  return postJson(`/api/actions/${id}/close`, {});
}

export function escalateAction(id: number, replayDate: string, comment?: string): Promise<TrackedAction> {
  return postJson(`/api/actions/${id}/escalate`, { replay_date: replayDate, comment });
}

export function commentOnAction(id: number, comment: string): Promise<ActionComment> {
  return postJson(`/api/actions/${id}/comment`, { comment });
}

export function getActionComments(id: number): Promise<{ results: ActionComment[] }> {
  return getJson(`/api/actions/${id}/comments`);
}

export interface ActionHistoryEvent {
  ts: string;
  actor_role: string | null;
  kind: "event" | "comment";
  event: string;
  detail: Record<string, unknown>;
}

export function getActionHistory(id: number): Promise<{ action_id: number; results: ActionHistoryEvent[] }> {
  return getJson(`/api/actions/${id}/history`);
}

export function getDiagnosisReview(tag: string): Promise<DiagnosisReview | null> {
  return getJson(`/api/equipment/${encodeURIComponent(tag)}/diagnosis-review`);
}

export function postDiagnosisReview(
  tag: string,
  body: { status: "confirmed" | "rejected"; reason?: string; replay_date: string },
): Promise<DiagnosisReview> {
  return postJson(`/api/equipment/${encodeURIComponent(tag)}/diagnosis-review`, body);
}

export function getAuditLog(actionType?: string): Promise<{ results: AuditLogEntry[] }> {
  const query = actionType ? `?action_type=${encodeURIComponent(actionType)}` : "";
  return getJson(`/api/audit-log${query}`);
}

export function getBacktest(): Promise<BacktestResponse> {
  return getJson("/api/backtest");
}

export function getSourceMap(): Promise<SourceMapResponse> {
  return getJson("/api/source-map");
}

export function getKpiDictionary(): Promise<KpiDictionaryResponse> {
  return getJson("/api/kpi-dictionary");
}

export function getAssumptions(): Promise<{ results: Assumption[] }> {
  return getJson("/api/assumptions");
}

export function getDataQuality(): Promise<DataQualityResponse> {
  return getJson("/api/data-quality");
}

export function getProcessFlags(replayDate: string): Promise<ProcessFlagsResponse> {
  return getJson(`/api/process-flags?replay_date=${encodeURIComponent(replayDate)}`);
}

export function getEnergyProxy(tag: string, replayDate: string): Promise<EnergyProxyResponse> {
  return getJson(
    `/api/equipment/${encodeURIComponent(tag)}/energy-proxy?replay_date=${encodeURIComponent(replayDate)}`,
  );
}

export function logRoleSwitch(body: {
  from_role: string | null;
  to_role: string;
  selected_plant: string | null;
}): Promise<{ status: string }> {
  return postJson("/api/audit-log/role-switch", body);
}

export function logViewMoney(body: {
  actor_role: string;
  page: string;
  plant_code?: string | null;
}): Promise<{ status: string }> {
  return postJson("/api/audit-log/view-money", body);
}

export function resetDemoData(): Promise<ResetDemoDataResponse> {
  return postJson("/api/reset-demo-data", {});
}
