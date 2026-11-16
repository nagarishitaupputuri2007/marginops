import axios from 'axios';
import type {
  AnomalyDetectionSummary,
  ApprovalActionCard,
  BenchmarkReport,
  CostAttributionSummary,
  CostExplorerResponse,
  HealthResponse,
  InvestigationReport,
  KpiSummary,
  SpendForecastReport,
  UnitEconomicsReport,
} from '@/types/api';

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api/v1',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Health check
export async function fetchHealth(): Promise<HealthResponse> {
  const response = await apiClient.get<HealthResponse>('/health');
  return response.data;
}

// Cost Intelligence
export async function fetchKpiSummary(): Promise<KpiSummary> {
  const response = await apiClient.get<KpiSummary>('/costs/summary');
  return response.data;
}

export async function fetchCostExplorer(params?: {
  provider?: string;
  service?: string;
  workload?: string;
  page?: number;
  limit?: number;
}): Promise<CostExplorerResponse> {
  const response = await apiClient.get<CostExplorerResponse>('/costs/explorer', { params });
  return response.data;
}

export async function fetchCostAttribution(): Promise<CostAttributionSummary> {
  const response = await apiClient.get<CostAttributionSummary>('/costs/attribution');
  return response.data;
}

// Unit Economics & Telemetry Fusion
export async function fetchUnitEconomics(): Promise<UnitEconomicsReport> {
  const response = await apiClient.get<UnitEconomicsReport>('/unit-economics/report');
  return response.data;
}

// Anomaly Detection & Benchmark
export async function fetchAnomalies(): Promise<AnomalyDetectionSummary> {
  const response = await apiClient.get<AnomalyDetectionSummary>('/anomalies');
  return response.data;
}

export async function fetchBenchmark(): Promise<BenchmarkReport> {
  const response = await apiClient.get<BenchmarkReport>('/anomalies/benchmark');
  return response.data;
}

// Spend Forecasting
export async function fetchSpendForecast(days: number = 30): Promise<SpendForecastReport> {
  const response = await apiClient.get<SpendForecastReport>('/forecasting/spend', {
    params: { days },
  });
  return response.data;
}

// AI Investigator & Governed Human Approval Gate
export async function fetchInvestigations(): Promise<InvestigationReport[]> {
  const response = await apiClient.get<InvestigationReport[]>('/investigations');
  return response.data;
}

export async function fetchInvestigation(id: string): Promise<InvestigationReport> {
  const response = await apiClient.get<InvestigationReport>(`/investigations/${id}`);
  return response.data;
}

export async function approveInvestigation(
  id: string,
  reviewerEmail: string,
  notes?: string
): Promise<ApprovalActionCard> {
  const response = await apiClient.post<ApprovalActionCard>(`/investigations/${id}/approve`, {
    reviewer_email: reviewerEmail,
    notes,
  });
  return response.data;
}

export async function rejectInvestigation(
  id: string,
  reviewerEmail: string,
  notes?: string
): Promise<ApprovalActionCard> {
  const response = await apiClient.post<ApprovalActionCard>(`/investigations/${id}/reject`, {
    reviewer_email: reviewerEmail,
    notes,
  });
  return response.data;
}

export async function dismissInvestigation(
  id: string,
  reviewerEmail: string,
  notes?: string
): Promise<ApprovalActionCard> {
  const response = await apiClient.post<ApprovalActionCard>(`/investigations/${id}/dismiss`, {
    reviewer_email: reviewerEmail,
    notes,
  });
  return response.data;
}
