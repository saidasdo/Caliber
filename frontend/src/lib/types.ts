export interface KpiValue {
  value: number;
  previous: number;
}

export interface KpiBand {
  incidents: KpiValue;
  downtime_hours: KpiValue;
  loss_kusd?: KpiValue; // absent entirely when the viewing role can't see it
  open_follow_ups: KpiValue;
  equipment_in_alarm: KpiValue;
  period_days: number;
}

export type HealthStatus = "NORMAL" | "ALARM" | "TRIP" | null;
export type PriorityLabel = "Critical" | "High" | "Medium" | "Low";

export type TrendDirection = "rising" | "falling" | "flat";
export type LimitDirection = "higher_is_worse" | "lower_is_worse";

export interface WeeklyParameter {
  parameter: string;
  unit: string | null;
  value: number | null;
  alarm: number | null;
  trip: number | null;
  direction: LimitDirection | null;
  trend_slope: number | null;
  trend: TrendDirection;
  remark: string | null;
}

export interface WorstParameter {
  parameter: string;
  value: number | null;
  unit: string | null;
  alarm: number | null;
  trip: number | null;
  direction: LimitDirection | null;
}

export interface PriorityRow {
  equipment_tag: string;
  equipment_name: string;
  plant_code: string;
  priority_score: number;
  priority_label: PriorityLabel;
  breakdown: {
    severity: number;
    severity_reason: string;
    class_score: number;
    eq_class: string | null;
    loss_exposure: number;
  };
  health_status: HealthStatus;
  weeks_in_status: number | null;
  estimated_loss_kusd?: number | null; // absent entirely when the viewing role can't see it
  diagnosis_rule_name: string | null;
  diagnosis_confidence: "High" | "Medium" | "Low" | null;
  worst_parameter: WorstParameter | null;
  reason: string;
}

export interface PlantLoss {
  plant_code: string;
  has_sensor_equipment: 0 | 1;
  loss_kusd?: number; // absent entirely when the viewing role can't see it
  downtime_hrs: number;
  incident_count: number;
}

export interface HeatmapCell {
  plant_code: string;
  month_year: string;
  incident_count: number;
  loss_kusd?: number; // absent entirely when the viewing role can't see it
}

export interface FollowUpPipeline {
  by_status: Record<string, number>;
  rca_process_overdue: number;
}

export interface OverviewResponse {
  replay_date: string;
  kpi_band: KpiBand;
  priority_queue: PriorityRow[];
  loss_by_plant: PlantLoss[];
  heatmap: HeatmapCell[];
  follow_up_pipeline: FollowUpPipeline;
}

export interface ReplayPreset {
  equipment_tag: string;
  label: string;
  replay_date: string;
}

export interface ReplayConfig {
  product_name: string;
  default_replay_date: string;
  presets: ReplayPreset[];
}

export type Role = "Executive" | "Plant manager" | "Engineer";

export interface WeeklyState {
  week: number;
  week_date: string;
  health_status: HealthStatus;
  parameters: WeeklyParameter[];
}

export interface Gauge {
  value: number | null;
  previous: number | null;
  sparkline: number[];
  data_available: boolean;
}

export interface HealthMarginGauge extends Gauge {
  worst_parameter: string | null;
}

export interface ProductionGauge extends Gauge {
  baseline: number | null;
}

export interface Gauges {
  availability: Gauge;
  health_margin: HealthMarginGauge;
  production_vs_normal: ProductionGauge;
}

export interface PerformanceSummary {
  equipment_tag: string;
  monitoring_period_weeks: number;
  total_downtime_hours: number;
  period_hours: number;
  availability_pct: number;
  failures_period: number;
  mtbf_hours: number;
  mttr_hours: number;
  alarm_readings: number;
  trip_readings: number;
  normal_readings: number;
  pm_compliance_pct: number;
  production_loss_ton: number;
  estimated_loss_kusd?: number; // absent entirely when the viewing role can't see it
}

export interface CapaAction {
  action_category: string;
  item_code: string | null;
  action_text: string;
  plan_date: string | null;
  pic: string | null;
  status: string | null;
  extra_json: string | null;
}

export interface LinkedRca {
  rca_id: number;
  ar_no: string | null;
  problem_statement: string | null;
  chronology: { datetime: string; event: string }[];
  root_cause: string | null;
  four_p: unknown;
  four_m_1e: unknown;
  capa_actions: CapaAction[];
}

export interface DiagnosisCondition {
  parameter: string;
  value: number | null;
  limit: number | null;
  direction: LimitDirection | null;
  trend: TrendDirection | null;
  check?: string;
  pass: boolean;
}

export interface Diagnosis {
  rule_name: string | null;
  confidence: "High" | "Medium" | "Low" | null;
  conditions: DiagnosisCondition[];
  passes?: number;
  of?: number;
  week?: number;
  week_date?: string;
  note: string;
  reason?: string;
}

export interface SimilarIncident {
  serial_no: number;
  ar_no: string | null;
  tag_number: string;
  risk_case_title: string | null;
  date_of_occur: string;
  downtime_hrs: number;
  total_loss_kusd?: number; // absent entirely when the viewing role can't see it
  overall_status: string;
  eq_type_family: string | null;
  component: string | null;
  plant_code: string | null;
  score: number;
  score_breakdown: Record<string, number>;
  dq9_flag: boolean;
}

export interface EquipmentDetail {
  tag: string;
  name: string;
  eq_type: string;
  eq_type_family: string | null;
  eq_class: string | null;
  plant_code: string;
  criticality: string | null;
  dominant_failure_mode: string | null;
  replay_date: string;
  has_hourly_coverage: boolean;
  hourly_signals: Signal[];
  weekly_state: WeeklyState | null;
  performance_summary: PerformanceSummary | null;
  gauges: Gauges;
  diagnosis: Diagnosis;
  similar_incidents: SimilarIncident[];
  linked_rca: LinkedRca | null;
}

export type StatusLane = "running" | "alarm" | "trip_off" | "no_data";

export interface StatusSegment {
  lane: StatusLane;
  start_ts: string;
  end_ts: string;
  hours: number;
}

export interface StatusDistribution {
  lane: StatusLane;
  duration_hours: number;
  occurrences: number;
}

export interface StatusTimeline {
  tag: string;
  segments: StatusSegment[];
  distribution: StatusDistribution[];
}

export interface WeeklySeriesParameter {
  parameter: string;
  unit: string | null;
  alarm: number | null;
  trip: number | null;
  direction: LimitDirection | null;
  points: { week: number; week_date: string; value: number | null; remark: string | null }[];
}

export interface WeeklySeries {
  tag: string;
  parameters: WeeklySeriesParameter[];
}

export type Signal =
  | "feed"
  | "discharge_pressure"
  | "vibration"
  | "temperature"
  | "motor_current"
  | "plant_rate";

export interface HourlyPoint {
  ts: string;
  value: number | null;
  run_status: "ON" | "OFF";
}

export interface HourlySeries {
  tag: string;
  signal: Signal;
  points: HourlyPoint[];
}

export interface AnomalyMarker {
  start_ts: string;
  end_ts: string;
  baseline_mean: number;
  peak_value: number;
}

export interface AnomalyResponse {
  tag: string;
  signal: Signal;
  anomalies: AnomalyMarker[];
}

export interface PlantDetail {
  plant_code: string;
  plant_name: string | null;
  has_sensor_equipment: boolean;
  replay_date: string;
  kpis: {
    incident_count: number;
    downtime_hrs: number;
    loss_kusd?: number; // absent entirely when the viewing role can't see it
  };
  equipment: PriorityRow[];
  incident_only_tags: string[];
  incident_history: {
    serial_no: number;
    ar_no: string | null;
    tag_number: string | null;
    date_of_occur: string;
    risk_case_title_display: string | null;
    overall_status: string;
    downtime_hrs: number;
    total_loss_kusd?: number; // absent entirely when the viewing role can't see it
  }[];
  open_actions: TrackedAction[];
  downtime_by_cause: {
    component: string;
    mechanism: string;
    incident_count: number;
    downtime_hrs: number;
  }[];
  rca_summaries: {
    equipment_tag: string;
    equipment_name: string;
    ar_no: string | null;
    root_cause: string | null;
  }[];
}

// --- Phase 6: Problem Tank, actions, audit log (SPEC section 5.7) ---------------------

export type ActionStatus = "Proposed" | "Open" | "In progress" | "Done" | "Closed" | "Rejected";
export type ActionSource = "capa_preload" | "diagnosis_suggestion" | "manual";
export type ProblemSourceType = "alert" | "incident" | "rca";

export interface TrackedAction {
  id: number;
  problem_id: number | null;
  equipment_tag: string | null;
  source: ActionSource;
  capa_action_id: number | null;
  action_text: string;
  pic: string | null;
  due_date: string | null;
  status: ActionStatus;
  reject_reason: string | null;
  progress_note: string | null;
  proposed_by_role: string | null;
  approved_by_role: string | null;
  closed_by_role: string | null;
  escalated: 0 | 1;
  approved_at: string | null;
  closed_at: string | null;
  created_at: string | null;
  overdue_days?: number | null;
}

export interface DiagnosisReview {
  id: number;
  equipment_tag: string;
  rule_name: string | null;
  status: "confirmed" | "rejected";
  reason: string | null;
  actor_role: string | null;
  ts: string;
}

export interface ActionComment {
  id: number;
  action_id: number;
  comment: string;
  actor_role: string | null;
  ts: string;
}

export interface ActionsResponse {
  results: TrackedAction[];
  counts_by_status: Record<string, number>;
}

export interface Problem {
  id: number | string;
  source_type: ProblemSourceType;
  source_ref: string | null;
  title: string;
  opened_date: string | null;
  status: string;
  priority_label: string | null;
}

export interface ProblemsResponse {
  results: Problem[];
  counts_by_source_type: Record<string, number>;
}

export interface SuggestedAction {
  source_capa_action_id: number | null;
  action_text: string;
  suggested_pic: string | null;
  suggested_due_date: string | null;
  source: "rca_capa" | "generic_default";
}

export interface SuggestedActionsResponse {
  tag: string;
  replay_date: string;
  rule_name: string | null;
  confidence: "High" | "Medium" | "Low" | null;
  suggestions: SuggestedAction[];
}

export interface AuditLogEntry {
  id: number;
  ts: string;
  actor_role: string | null;
  action_type: string;
  detail_json: string;
}

// --- Phase 7: Backtest (SPEC section 5.8) ---------------------------------------------

export interface BacktestWeek {
  week: number;
  week_date: string;
  health_status: HealthStatus;
}

export interface BacktestRow {
  equipment_tag: string;
  plant_code: string | null;
  failure_date: string;
  first_alarm_week: number | null;
  first_alarm_date: string | null;
  first_trip_week: number | null;
  first_trip_date: string | null;
  lead_time_weeks: number | null;
  first_off_ts: string | null;
  first_hourly_anomaly_ts: string | null;
  first_hourly_anomaly_week: number | null;
  lead_time_hours: number | null;
  downtime_hours: number | null;
  loss_kusd?: number | null; // absent entirely when the viewing role can't see it
  weekly_health: BacktestWeek[];
  message: string | null;
  assumption: string;
}

export interface BacktestResponse {
  results: BacktestRow[];
}

// --- Phase 8: Source map, KPI dictionary, Data quality (SPEC section 5.9 / 6) ---------

export interface SourceMapEntry {
  source_file: string;
  sheet: string;
  column: string | null;
  target_table: string | null;
  target_column: string | null;
  feeds: string[];
}

export interface JoinKey {
  key: string;
  links: string[];
  notes: string;
}

export interface SourceMapResponse {
  entries: SourceMapEntry[];
  join_keys: JoinKey[];
}

export interface KpiDictionaryEntry {
  kpi_name: string;
  definition: string;
  formula: string | null;
  source: string | null;
  refresh_frequency: string | null;
  owner: string | null;
}

export interface KpiDictionaryResponse {
  results: KpiDictionaryEntry[];
}

export interface DqIssue {
  id: number;
  dq_id: string;
  severity: string;
  source_location: string | null;
  observed: string | null;
  expected: string | null;
  applied_assumption: string | null;
  status: "Open" | "Accepted";
}

export interface Assumption {
  id: number;
  area: string;
  assumption_text: string;
  rationale: string | null;
  created_at: string | null;
}

export interface DataQualityResponse {
  score: number;
  score_formula: string;
  issue_count: number;
  issues: DqIssue[];
  by_dq_id: Record<string, DqIssue[]>;
  not_errors: Assumption[];
}

export interface ProcessFlagMetric {
  count: number;
  of_total: number;
  description: string;
  oldest_date?: string | null;
}

export interface ProcessFlagsResponse {
  replay_date: string;
  rca_process_overdue: ProcessFlagMetric;
  new_registered_stale: ProcessFlagMetric;
  incidents_without_ar_no: ProcessFlagMetric;
}

// --- Phase 9: roles, energy proxy, reset demo data (SPEC section 5.10 / 5.11 / 10) ----

export interface EnergyProxyPoint {
  day: string;
  motor_load_index: number;
}

export interface EnergyProxyMovingAveragePoint {
  day: string;
  value: number;
}

export interface EnergyProxyForecastPoint {
  day: string;
  value: number;
}

export interface EnergyProxyResponse {
  tag: string;
  label: string;
  history: EnergyProxyPoint[];
  moving_average: EnergyProxyMovingAveragePoint[];
  forecast: EnergyProxyForecastPoint[];
  assumption?: string;
}

export interface ResetDemoDataResponse {
  status: string;
  checks: { name: string; passed: boolean | null; detail: string }[];
}
