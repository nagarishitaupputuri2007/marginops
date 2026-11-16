export interface DependencyHealth {
  status: 'connected' | 'unreachable';
  latency_ms?: number;
  error?: string;
}

export interface HealthResponse {
  status: 'healthy' | 'degraded';
  app: string;
  version: string;
  environment: string;
  timestamp: string;
  dependencies: {
    postgres: DependencyHealth;
    mongodb: DependencyHealth;
    redis: DependencyHealth;
  };
}

export interface ProviderBreakdown {
  provider: string;
  amount: number;
  share_percent: number;
}

export interface KpiSummary {
  organization_id: string;
  organization_name: string;
  total_net_spend: number;
  mtd_spend: number;
  monthly_budget: number;
  burn_rate_percent: number;
  budget_exceeded: boolean;
  projected_budget_variance: number;
  projected_monthly_spend: number;
  trend_direction: string;
  blended_gross_margin_percent: number;
  active_anomalies_count: number;
  critical_anomalies_count: number;
  total_anomalous_impact: number;
  total_records_ingested: number;
  providers_breakdown: ProviderBreakdown[];
  reconciliation_delta: string;
  is_reconciled: boolean;
}

export interface DailySpendPoint {
  date: string;
  total: number;
  AWS: number;
  GCP: number;
  Azure: number;
}

export interface BillingRecordItem {
  billing_date: string;
  cloud_provider: string;
  service_id: string;
  service_name: string;
  resource_id: string;
  workload_id?: string;
  product_feature_id?: string;
  billing_amount: number;
  is_credit: boolean;
  tags?: Record<string, any>;
}

export interface CostExplorerResponse {
  total_items: number;
  page: number;
  limit: number;
  total_pages: number;
  items: BillingRecordItem[];
  daily_time_series: DailySpendPoint[];
}

export interface FeatureAttributionItem {
  feature_id: string;
  feature_name: string;
  allocated_amount: number;
  share_percent: number;
}

export interface CostAttributionSummary {
  organization_id: string;
  total_source_amount: number;
  total_allocated_amount: number;
  total_unallocated_amount: number;
  reconciliation_delta: string;
  is_reconciled: boolean;
  allocated_items_count: number;
  unallocated_items_count: number;
  by_feature: FeatureAttributionItem[];
  algorithm: string;
  audit_guarantee: string;
}

export interface UnitCostDriver {
  feature_id?: string;
  feature_name?: string;
  metric_type: string;
  unit_name: string;
  total_cost_usd: number;
  total_volume: number;
  unit_cost: number;
  cost_per_thousand?: number;
  cost_per_million?: number;
  status: string;
}

export interface FeatureGrossMargin {
  feature_id: string;
  feature_name: string;
  feature_slug: string;
  tier: string;
  total_cost_usd: number;
  total_revenue_usd: number;
  gross_profit_usd: number;
  target_gross_margin_percent: number;
  actual_gross_margin_percent?: number;
  margin_delta_percent?: number;
  status: 'HEALTHY' | 'WARNING' | 'CRITICAL' | 'NEGATIVE' | 'NO_REVENUE';
}

export interface UnitEconomicsReport {
  organization_id: string;
  generated_at: string;
  total_attributed_cost: number;
  total_revenue: number;
  overall_gross_margin_percent?: number;
  total_requests: number;
  total_tokens: number;
  metrics: UnitCostDriver[];
  margins: FeatureGrossMargin[];
}

export interface DetectedAnomaly {
  id: string;
  organization_id: string;
  anomaly_type: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  status: string;
  title: string;
  description: string;
  cloud_provider: string;
  service_id: string;
  resource_id?: string;
  workload_id?: string;
  product_feature_id?: string;
  detected_date: string;
  start_date: string;
  end_date?: string;
  actual_cost: number | string;
  expected_baseline_cost: number | string;
  cost_impact: number | string;
  z_score?: number;
  percentage_increase?: number;
  evidence: Record<string, any>;
  root_cause_hint?: string;
}

export interface AnomalyDetectionSummary {
  organization_id: string;
  evaluated_records_count: number;
  evaluated_days_count: number;
  anomalies_detected_count: number;
  total_cost_impact: number | string;
  by_severity: Record<string, number>;
  by_type: Record<string, number>;
  anomalies: DetectedAnomaly[];
}

export interface ScenarioMatchResult {
  scenario_id: string;
  scenario_type: string;
  title: string;
  target_service: string;
  target_resource_id: string;
  is_detected: boolean;
  matched_anomaly?: DetectedAnomaly;
  expected_impact?: number | string;
  detected_impact?: number | string;
}

export interface BenchmarkReport {
  total_ground_truth_scenarios: number;
  true_positives: number;
  false_positives: number;
  false_negatives: number;
  precision: number;
  recall: number;
  f1_score: number;
  scenario_results: ScenarioMatchResult[];
}

export interface ForecastDataPoint {
  forecast_date: string;
  predicted_amount: number | string;
  lower_bound_80: number | string;
  upper_bound_80: number | string;
  lower_bound_95: number | string;
  upper_bound_95: number | string;
}

export interface SpendForecastReport {
  organization_id: string;
  service_id?: string;
  historical_days_evaluated: number;
  historical_daily_average: number | string;
  forecast_days: number;
  projected_total_spend: number | string;
  daily_burn_rate: number | string;
  trend_slope: number | string;
  trend_direction: string;
  budget_limit?: number | string;
  budget_exceeded: boolean;
  projected_budget_variance?: number | string;
  forecast_points: ForecastDataPoint[];
}

export interface EvidenceItem {
  id: string;
  evidence_type: string;
  source_system: string;
  metric_name: string;
  metric_value: any;
  observed_date?: string;
  citation_ref: string;
}

export interface Hypothesis {
  hypothesis_id: string;
  title: string;
  description: string;
  confidence_score: number;
  is_primary: boolean;
  supporting_evidence: string[];
}

export interface OptimizationOption {
  option_id: string;
  action_type: string;
  title: string;
  description: string;
  estimated_monthly_savings_usd: number | string;
  implementation_effort: string;
  risk_assessment: string;
  trade_offs: Record<string, any>;
  is_recommended: boolean;
}

export interface ApprovalActionCard {
  id: string;
  investigation_id: string;
  organization_id: string;
  selected_option_id: string;
  status: 'pending_approval' | 'approved' | 'rejected' | 'dismissed';
  reviewed_by?: string;
  reviewed_at?: string;
  review_notes?: string;
  audit_hash: string;
}

export interface InvestigationReport {
  id: string;
  organization_id: string;
  anomaly_id: string;
  anomaly_title: string;
  anomaly_type: string;
  status: 'triggered' | 'gathering_evidence' | 'analyzing' | 'pending_approval' | 'approved' | 'rejected' | 'dismissed';
  started_at: string;
  completed_at?: string;
  executive_summary: string;
  primary_root_cause: string;
  evidence: EvidenceItem[];
  hypotheses: Hypothesis[];
  options: OptimizationOption[];
  approval_card?: ApprovalActionCard;
}
