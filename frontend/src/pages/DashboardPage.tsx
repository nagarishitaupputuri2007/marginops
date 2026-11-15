import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchHealth } from '@/services/api';
import { Server, Database, Layers, CheckCircle2, AlertTriangle, ShieldCheck } from 'lucide-react';

export const DashboardPage: React.FC = () => {
  const { data: health, isLoading, isError, error } = useQuery({
    queryKey: ['system-health'],
    queryFn: fetchHealth,
    refetchInterval: 15000,
    retry: 1,
  });

  return (
    <div className="space-y-8 max-w-6xl">
      <div>
        <h2 className="text-2xl font-bold text-white tracking-tight">System Overview</h2>
        <p className="text-slate-400 text-sm mt-1">
          Infrastructure health and foundational service connectivity status.
        </p>
      </div>

      {/* Status Highlights */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="p-6 rounded-xl border border-slate-800 bg-slate-900/60 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-slate-400">Backend API</span>
            <Server className="h-5 w-5 text-emerald-400" />
          </div>
          <div className="mt-4 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-white">
              {isLoading ? 'Checking...' : isError ? 'Offline' : health?.status.toUpperCase()}
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-2">
            FastAPI modular monolith on Python 3.13
          </p>
        </div>

        <div className="p-6 rounded-xl border border-slate-800 bg-slate-900/60 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-slate-400">Primary Database</span>
            <Database className="h-5 w-5 text-cyan-400" />
          </div>
          <div className="mt-4 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-white">
              {isLoading ? '...' : health?.dependencies.postgres.status === 'connected' ? 'Connected' : 'Pending Docker'}
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-2">
            PostgreSQL 16 (SQLAlchemy 2.x asyncpg)
          </p>
        </div>

        <div className="p-6 rounded-xl border border-slate-800 bg-slate-900/60 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-slate-400">Telemetry Engine</span>
            <Layers className="h-5 w-5 text-violet-400" />
          </div>
          <div className="mt-4 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-white">
              {isLoading ? '...' : health?.dependencies.mongodb.status === 'connected' ? 'Connected' : 'Pending Docker'}
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-2">
            MongoDB 7.0 (Official PyMongo Async)
          </p>
        </div>
      </div>

      {/* Infrastructure Connection Details */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-6">
        <h3 className="text-base font-semibold text-white mb-4 flex items-center gap-2">
          <ShieldCheck className="h-5 w-5 text-emerald-400" />
          Foundation Subsystems & Diagnostics
        </h3>

        {isLoading ? (
          <div className="text-sm text-slate-400 py-4">Polling subsystem status...</div>
        ) : isError ? (
          <div className="p-4 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-300 text-sm flex items-center gap-3">
            <AlertTriangle className="h-5 w-5 shrink-0" />
            <div>
              <p className="font-medium">Backend API currently unreachable at /api/v1/health.</p>
              <p className="text-xs text-amber-400/80 mt-0.5">
                Ensure the FastAPI backend is running on port 8000. (Error: {(error as Error)?.message})
              </p>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {Object.entries(health?.dependencies || {}).map(([service, dep]) => {
              const isConnected = dep.status === 'connected';
              return (
                <div
                  key={service}
                  className="p-4 rounded-lg bg-slate-950/60 border border-slate-800/80 flex flex-col justify-between"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium capitalize text-slate-300">{service}</span>
                    {isConnected ? (
                      <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                    ) : (
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20">
                        Unreachable
                      </span>
                    )}
                  </div>
                  <div className="mt-3 text-xs text-slate-500 font-mono">
                    {isConnected ? (
                      <span className="text-emerald-400">Latency: {dep.latency_ms}ms</span>
                    ) : (
                      <span className="text-slate-400 truncate block" title={dep.error || 'Connection failed'}>
                        {dep.error ? dep.error.slice(0, 45) + '...' : 'Awaiting Docker startup'}
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
