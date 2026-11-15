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
