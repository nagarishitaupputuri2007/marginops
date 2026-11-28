import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { fetchUnitEconomics } from '@/services/api';
import {
  AlertTriangle,
  CheckCircle2,
  XCircle,
  HelpCircle,
  ArrowRight,
  Zap,
} from 'lucide-react';

export const UnitEconomicsPage: React.FC = () => {
  const { data: unitEcon, isLoading, isError, error } = useQuery({
    queryKey: ['unit-economics-report'],
    queryFn: fetchUnitEconomics,
    refetchInterval: 15000,
  });

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'HEALTHY':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <CheckCircle2 className="h-3 w-3" /> Healthy
          </span>
        );
      case 'WARNING':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <AlertTriangle className="h-3 w-3" /> Warning
          </span>
        );
      case 'CRITICAL':
      case 'NEGATIVE':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-rose-500/10 text-rose-400 border border-rose-500/20">
            <XCircle className="h-3 w-3" /> Critical
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-zinc-800 text-zinc-400 border border-zinc-700/60">
            <HelpCircle className="h-3 w-3" /> Platform Overhead
          </span>
        );
    }
  };

  if (isError) {
    return (
      <div className="p-8 rounded-xl border border-rose-500/30 bg-rose-500/10 text-zinc-200 max-w-xl mx-auto my-12 text-center space-y-3">
        <AlertTriangle className="h-8 w-8 text-rose-400 mx-auto" />
        <h2 className="text-base font-semibold text-rose-300">Failed to Load Unit Economics Telemetry</h2>
        <p className="text-xs text-zinc-400">
          {(error as Error)?.message || 'Unable to connect to the backend unit economics engine.'}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* Executive Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-zinc-800/80 pb-6">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-semibold text-zinc-100 tracking-tight">
              Product Unit Economics & Telemetry Fusion
            </h1>
            <span className="px-2.5 py-0.5 rounded-full text-[11px] font-mono font-medium bg-zinc-800 text-zinc-300 border border-zinc-700/60">
              Telemetry Fusion Engine
            </span>
          </div>
          <p className="text-zinc-400 text-xs mt-1">
            Fuses relational ledger expenditures with high-throughput operational telemetry to evaluate $/kReq, $/MTok, and gross margin compliance.
          </p>
        </div>

        <div className="bg-[#12141e] border border-zinc-800 rounded-lg px-4 py-2 flex items-center gap-4 text-xs">
          <div>
            <div className="text-zinc-400">Blended Gross Margin</div>
            <div className="text-lg font-semibold tracking-tight text-zinc-100 mt-0.5">
              {isLoading ? '...' : `${Number(unitEcon?.overall_gross_margin_percent ?? 0).toFixed(1)}%`}
            </div>
          </div>
          <div className="border-l border-zinc-800 pl-4">
            <div className="text-zinc-400">Target Benchmark</div>
            <div className="text-xs font-medium text-emerald-400 mt-1">70.0% Target</div>
          </div>
        </div>
      </div>

      {/* Primary Volume & Cost Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="p-5 rounded-xl border border-zinc-800/80 bg-[#0d0e15] shadow-sm">
          <span className="text-xs font-medium text-zinc-400">Total Attributed COGS</span>
          <div className="mt-2 text-2xl font-semibold tracking-tight text-zinc-100">
            ${Number(unitEcon?.total_attributed_cost ?? 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
          <p className="text-[11px] text-zinc-400 mt-1">Hosting, compute & model inference</p>
        </div>

        <div className="p-5 rounded-xl border border-zinc-800/80 bg-[#0d0e15] shadow-sm">
          <span className="text-xs font-medium text-zinc-400">Monitored SaaS Revenue</span>
          <div className="mt-2 text-2xl font-semibold tracking-tight text-emerald-400">
            ${Number(unitEcon?.total_revenue ?? 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
          <p className="text-[11px] text-zinc-400 mt-1">Recognized customer contract billings</p>
        </div>

        <div className="p-5 rounded-xl border border-zinc-800/80 bg-[#0d0e15] shadow-sm">
          <span className="text-xs font-medium text-zinc-400">API Requests Tracked</span>
          <div className="mt-2 text-2xl font-semibold tracking-tight text-zinc-200 font-mono">
            {(unitEcon?.total_requests ?? 0).toLocaleString()}
          </div>
          <p className="text-[11px] text-zinc-400 mt-1">Ingress gateway telemetry stream</p>
        </div>

        <div className="p-5 rounded-xl border border-zinc-800/80 bg-[#0d0e15] shadow-sm">
          <span className="text-xs font-medium text-zinc-400">Inference Token Volume</span>
          <div className="mt-2 text-2xl font-semibold tracking-tight text-zinc-200 font-mono">
            {((unitEcon?.total_tokens ?? 0) / 1000000).toFixed(1)}M Tokens
          </div>
          <p className="text-[11px] text-zinc-400 mt-1">Bedrock & Azure OpenAI combined</p>
        </div>
      </div>

      {/* Unit Cost Drivers */}
      <div>
        <h2 className="text-sm font-semibold text-zinc-200 mb-3 flex items-center gap-2">
          <Zap className="h-4 w-4 text-zinc-400" />
          Unit Cost Drivers ($/kReq & $/MTok)
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {unitEcon?.metrics?.map((m, idx) => {
            const costVal = m.cost_per_thousand !== undefined
              ? `$${Number(m.cost_per_thousand).toFixed(4)}`
              : m.cost_per_million !== undefined
              ? `$${Number(m.cost_per_million).toFixed(2)}`
              : `$${Number(m.unit_cost ?? 0).toFixed(4)}`;
            const totalCost = Number(m.total_allocated_cost ?? m.total_cost_usd ?? 0);
            const totalVol = Number(m.total_usage_units ?? m.total_volume ?? 0);

            return (
              <div
                key={m.id || idx}
                className="p-5 rounded-xl border border-zinc-800/80 bg-[#0d0e15] flex flex-col justify-between shadow-sm"
              >
                <div>
                  <div className="flex items-center justify-between text-xs text-zinc-400">
                    <span className="font-medium text-zinc-200">{m.feature_name || 'Service Unit'}</span>
                    <span className="px-2 py-0.5 rounded text-[10px] bg-zinc-800 font-mono text-zinc-400 border border-zinc-700/50">
                      {m.metric_type}
                    </span>
                  </div>
                  <div className="mt-3">
                    <span className="text-2xl font-semibold tracking-tight text-zinc-100">
                      {costVal}
                    </span>
                    <span className="text-xs text-zinc-400 ml-1.5 font-normal">{m.unit_name}</span>
                  </div>
                </div>
                <div className="mt-4 pt-3 border-t border-zinc-800/70 flex items-center justify-between text-xs text-zinc-400 font-mono">
                  <span>Total Cost: ${totalCost.toFixed(2)}</span>
                  <span>Volume: {totalVol.toLocaleString()}</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Feature Gross Margin Compliance Matrix */}
      <div className="rounded-xl border border-zinc-800/80 bg-[#0d0e15] overflow-hidden shadow-sm">
        <div className="px-6 py-4 border-b border-zinc-800/80 flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-zinc-100">Feature Gross Margin Compliance Matrix</h2>
            <p className="text-xs text-zinc-400 mt-0.5">
              Scorecard comparing actual COGS profitability against business target margins.
            </p>
          </div>
          <Link
            to="/investigator"
            className="text-xs font-medium text-zinc-300 hover:text-white flex items-center gap-1 transition"
          >
            Investigate Underperforming Features <ArrowRight className="h-3.5 w-3.5 text-zinc-400" />
          </Link>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-zinc-300">
            <thead className="bg-[#12141e] border-b border-zinc-800/80 text-zinc-400 uppercase tracking-wider font-medium text-[11px]">
              <tr>
                <th className="px-4 py-3">Product Feature</th>
                <th className="px-4 py-3">Tier</th>
                <th className="px-4 py-3 text-right">COGS (Cost)</th>
                <th className="px-4 py-3 text-right">Revenue</th>
                <th className="px-4 py-3 text-right">Gross Profit</th>
                <th className="px-4 py-3 text-center">Actual Margin</th>
                <th className="px-4 py-3 text-center">Target</th>
                <th className="px-4 py-3 text-center">Health Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/50 font-mono">
              {isLoading ? (
                <tr>
                  <td colSpan={8} className="px-4 py-8 text-center text-zinc-500 font-sans">
                    Fusing ledger and telemetry...
                  </td>
                </tr>
              ) : unitEcon?.margins?.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-4 py-8 text-center text-zinc-500 font-sans">
                    No product feature margins calculated yet.
                  </td>
                </tr>
              ) : (
                unitEcon?.margins?.map((m, idx) => {
                  const cogs = Number(m.cogs_cost ?? m.total_cost_usd ?? 0);
                  const rev = Number(m.revenue ?? m.total_revenue_usd ?? 0);
                  const gp = Number(m.gross_profit ?? m.gross_profit_usd ?? 0);
                  const targetMargin = Number(m.target_gross_margin_percent ?? 70);
                  const actualMargin = m.actual_gross_margin_percent !== undefined ? Number(m.actual_gross_margin_percent) : undefined;

                  return (
                    <tr key={m.product_feature_id || m.feature_id || idx} className="hover:bg-zinc-900/50 transition">
                      <td className="px-4 py-3 font-sans font-medium text-zinc-200">{m.feature_name}</td>
                      <td className="px-4 py-3 font-sans">
                        <span className="px-2 py-0.5 rounded text-[10px] bg-zinc-800 text-zinc-400 capitalize border border-zinc-700/40">
                          {m.tier}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right text-zinc-300">${cogs.toFixed(2)}</td>
                      <td className="px-4 py-3 text-right text-emerald-400 font-medium">
                        ${rev.toFixed(2)}
                      </td>
                      <td className="px-4 py-3 text-right text-zinc-200">
                        ${gp.toFixed(2)}
                      </td>
                      <td className="px-4 py-3 text-center font-medium">
                        {actualMargin !== undefined ? (
                          <span
                            className={
                              m.status === 'HEALTHY'
                                ? 'text-emerald-400'
                                : m.status === 'WARNING'
                                ? 'text-amber-400'
                                : 'text-rose-400'
                            }
                          >
                            {actualMargin.toFixed(1)}%
                          </span>
                        ) : (
                          <span className="text-zinc-500">N/A</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-center text-zinc-400">
                        {targetMargin.toFixed(1)}%
                      </td>
                      <td className="px-4 py-3 text-center font-sans">{getStatusBadge(m.status)}</td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
