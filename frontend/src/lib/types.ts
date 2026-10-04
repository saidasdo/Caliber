export interface KpiValue {
  value: number;
  previous: number;
}

export interface Assumption {
  id: number;
  area: string;
  assumption_text: string;
  rationale: string | null;
  created_at: string | null;
}

export interface KpiBand {
  incidents: KpiValue;
  downtime_hours: KpiValue;
  loss_kusd?: KpiValue; // absent entirely when the viewing role can't see it
  open_follow_ups: KpiValue;
  equipment_in_alarm: KpiValue;
  // Estimate from motor current for the motor-driven equipment, replay week. Not money.
  emission_kg?: KpiValue & { breakdown?: EmissionBreakdownRow[] };
  // Average production vs normal across equipment with hourly data on the replay date (null value =
  // "No hourly data").
  production_vs_normal?: ProductionKpi;
  // Motor load index, replay week vs the week before, with the 7-day forecast direction.
  energy_proxy?: EnergyKpi;
  period_days: number;
}

export interface EmissionBreakdownRow {
  equipment_tag: string;
  plant_code: string;
  week_kg: number;
  today_kg: number | null;
}

export interface ProductionKpi {
  value: number | null;
  previous: number | null;
  count: number;
  message: string | null;
  breakdown: {
    equipment_tag: string;
    plant_code: string;
    value: number;
    previous: number | null;
    baseline_plant_rate: number | null;
  }[];
}

export interface EnergyKpi {
  value: number | null;
  previous: number | null;
  forecast_next_7_days: number | null;
  forecast_direction: "up" | "down" | "flat" | null;
  message: string | null;
  breakdown: {
    equipment_tag: string;
    plant_code: string;
    week: number | null;
    previous_week: number | null;
    forecast_next_7_days: number | null;
    forecast_direction: "up" | "down" | "flat" | null;
  }[];
}

export type HealthStatus = "NORMAL" | "ALARM" | "TRIP" | null;
export type PriorityLabel = "Critical" | "High" | "Medium" | "Normal";

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
  // 1 = highest. The engine's dominance order, not the raw score: use this for any ordering.
  rank?: number;
  equipment_tag: string;
  equipment_name: string;
  equipment_type?: string | null;
  // Most advanced action state on this machine among actions known on the replay date.
  action_status?: ActionStatusLabel;
  plant_code: string;
  priority_score: number;
  priority_label: PriorityLabel;
  breakdown: {
    urgency?: number;
    severity: number;
    severity_reason: string;
    health_margin_pct: number | null;
    severity_floor: number;
    proximity: number;
    alarm_share: number;
    parameters_past_alarm: number;
    parameters_total: number;
    class_score: number;
    class_source: "eq_class" | "criticality" | "default";
    eq_class: string | null;
    criticality?: string | null;
    loss_exposure: number;
  };
  health_status: HealthStatus;
  weeks_in_status: number | null;
  estimated_impact?: EstimatedImpact | null; // absent entirely when the viewing role can't see it
  reliability?: Reliability;
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

export type ActionStatusLabel = "No owner yet" | "Proposed" | "Open" | "In progress";

export interface OverviewResponse {
  replay_date: string;
  kpi_band: KpiBand;
  priority_queue: PriorityRow[];
  follow_up_health: { awaiting_approval: number };
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
  // Highest margin at the alarm limit across the monitored parameters: the amber band runs from 0
  // up to this, so the gauge is never green while any parameter is past its alarm limit.
  alarm_margin_pct: number | null;
  // Healthy baseline of the worst parameter (median of its first 6 weeks).
  baseline: number | null;
}

export interface ProductionGauge extends Gauge {
  baseline: number | null;
}

export interface Gauges {
  availability: Gauge;
  health_margin: HealthMarginGauge;
  production_vs_normal: ProductionGauge;
}

// Replay-safe estimate of a failure's cost: median of earlier similar incidents. Never a known
// amount. The whole object is absent for a role that can't see money.
export interface EstimatedImpact {
  value_kusd: number | null;
  basis: "eq_type_family" | "eq_class" | "all" | null;
  n_incidents: number;
}

export interface Reliability {
  failures: number | null;
  observed_hours: number | null;
  downtime_hours: number | null;
  mtbf_hours: number | null;
  mttr_hours: number | null;
  message: string | null;
}

export interface EmissionDay {
  day: string;
  kwh: number;
  kg_co2e: number;
}

export interface Emission {
  applicable: boolean;
  label: string;
  factors: {
    motor_voltage_kv: number;
    power_factor: number;
    grid_emission_factor_kg_per_kwh: number;
  };
  series: EmissionDay[];
  today_kg: number | null;
  week_kg: number | null;
}

export interface PastRca {
  rca_id: number;
  equipment_tag: string;
  ar_no: string | null;
  root_cause: string | null;
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
  reliability: Reliability;
  emission: Emission;
  gauges: Gauges;
  diagnosis: Diagnosis;
  impact: EstimatedImpact;
  similar_incidents: SimilarIncident[];
  linked_rca: LinkedRca | null;
  past_rcas: PastRca[];
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
  replay_date: string;
  // Same axis contract as HourlySeries: the record's start and length, segments up to the replay date.
  window_start: string | null;
  axis_hours: number;
  segments: StatusSegment[];
  distribution: StatusDistribution[];
}

export interface WeeklySeriesParameter {
  parameter: string;
  unit: string | null;
  alarm: number | null;
  trip: number | null;
  direction: LimitDirection | null;
  points: {
    week: number;
    week_date: string;
    value: number | null;
    remark: string | null;
    health_status: HealthStatus;
  }[];
}

export interface WeeklySeries {
  tag: string;
  replay_date: string;
  // Number of weeks in the whole record (a count): the chart keeps this width; weeks after the
  // replay date are not returned.
  axis_weeks: number;
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
  replay_date: string;
  display_unit: string | null;
  // Start of the hourly record and its length in hours: the chart keeps this x-axis size on every
  // replay date, and the area after the replay date stays empty. Only points up to the replay date.
  window_start: string | null;
  axis_hours: number;
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
  plant_code?: string | null;
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
  category: "corrective" | "preventive";
  // "rca_capa": the equipment's own RCA, once its failure date is on or before the replay date.
  // "action_library": generic maintenance action for the rule (catalog/action_library.py).
  source: "rca_capa" | "action_library";
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
  outcome_basis: string; // "Actual outcome (after the trip)": downtime and loss are not known at the time
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
  replay_date: string;
  label: string;
  axis_days: number;
  history: EnergyProxyPoint[];
  moving_average: EnergyProxyMovingAveragePoint[];
  forecast: EnergyProxyForecastPoint[];
  assumption?: string;
}

export interface ResetDemoDataResponse {
  status: string;
  checks: { name: string; passed: boolean | null; detail: string }[];
}
