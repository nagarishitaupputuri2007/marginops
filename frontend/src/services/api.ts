import axios from 'axios';
import type { HealthResponse } from '@/types/api';

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api/v1',
  timeout: 5000,
  headers: {
    'Content-Type': 'application/json',
  },
});

export async function fetchHealth(): Promise<HealthResponse> {
  const response = await apiClient.get<HealthResponse>('/health');
  return response.data;
}
