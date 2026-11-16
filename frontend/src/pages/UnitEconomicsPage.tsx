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
  const { data: unitEcon, isLoading } = useQuery({
    queryKey: ['unit-economics-report'],
    queryFn: fetchUnitEconomics,
    refetchInterval: 15000,
  });

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'HEALTHY':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <CheckCircle2 className="h-3 w-3" /> Healthy
          </span>
        );
      case 'WARNING':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <AlertTriangle className="h-3 w-3" /> Warning
          </span>
        );
      case 'CRITICAL':
      case 'NEGATIVE':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">
            <XCircle className="h-3 w-3" /> Critical
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-800 text-slate-400 border border-slate-700">
            <HelpCircle className="h-3 w-3" /> Internal Tool
          </span>
        );
    }
  };

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-6">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-white tracking-tight">
              Product Unit Economics & Telemetry Fusion
            </h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-mono font-semibold bg-violet-500/10 text-violet-400 border border-violet-500/20">
              Slide 05 Engine
            </span>
          </div>
          <p className="text-slate-400 text-sm mt-1">
            Fuses relational ledger expenditures with PyMongo operational telemetry to track $/kReq, $/MTok, and gross margin targets.
          </p>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-3 flex items-center gap-4 text-xs">
          <div>
            <div className="text-slate-500">Blended Gross Margin</div>
            <div className="text-xl font-bold text-white mt-0.5">
              {isLoading ? '...' : `${Number(unitEcon?.overall_gross_margin_percent || 0).toFixed(1)}%`}
            </div>
          </div>
          <div className="border-l border-slate-800 pl-4">
            <div className="text-slate-500">Target Benchmark</div>
            <div className="text-sm font-semibold text-emerald-400 mt-1">75.0% Target</div>
          </div>
        </div>
      </div>

      {/* KPI Cards: Telemetry Volume & Attributed COGS */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-5">
        <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/40">
          <span className="text-xs font-medium text-slate-400">Total Attributed COGS</span>
          <div className="mt-2 text-2xl font-extrabold text-white">
            ${Number(unitEcon?.total_attributed_cost || 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}
          </div>
          <p className="text-[11px] text-slate-500 mt-1">Infrastructure hosting & inference</p>
        </div>

        <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/40">
          <span className="text-xs font-medium text-slate-400">Total Monitored Revenue</span>
          <div className="mt-2 text-2xl font-extrabold text-emerald-400">
            ${Number(unitEcon?.total_revenue || 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}
          </div>
          <p className="text-[11px] text-slate-500 mt-1">Customer subscription & usage tiers</p>
        </div>

        <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/40">
          <span className="text-xs font-medium text-slate-400">Monitored API Requests</span>
          <div className="mt-2 text-2xl font-extrabold text-cyan-400 font-mono">
            {(unitEcon?.total_requests || 0).toLocaleString()}
          </div>
          <p className="text-[11px] text-slate-500 mt-1">High-throughput search & APIs</p>
        </div>

        <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/40">
          <span className="text-xs font-medium text-slate-400">Inference Token Volume</span>
          <div className="mt-2 text-2xl font-extrabold text-violet-400 font-mono">
            {((unitEcon?.total_tokens || 0) / 1000000).toFixed(1)}M Tokens
          </div>
          <p className="text-[11px] text-slate-500 mt-1">Bedrock / Azure OpenAI telemetry</p>
        </div>
      </div>

      {/* Unit Cost Drivers Cards */}
      <div>
        <h2 className="text-base font-semibold text-white mb-3 flex items-center gap-2">
          <Zap className="h-4 w-4 text-emerald-400" />
          Unit Cost Drivers ($/kReq & $/MTok)
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          {unitEcon?.metrics.map((m, idx) => (
            <div
              key={idx}
              className="p-5 rounded-xl border border-slate-800 bg-slate-900/40 flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between text-xs text-slate-400">
                  <span className="font-semibold text-slate-300">{m.feature_name || 'Service Unit'}</span>
                  <span className="px-2 py-0.5 rounded text-[10px] bg-slate-800 font-mono text-slate-400">
                    {m.metric_type}
                  </span>
                </div>
                <div className="mt-3">
                  <span className="text-2xl font-extrabold text-white">
                    {m.cost_per_thousand !== undefined
                      ? `$${m.cost_per_thousand.toFixed(4)}`
                      : m.cost_per_million !== undefined
                      ? `$${m.cost_per_million.toFixed(2)}`
                      : `$${m.unit_cost.toFixed(4)}`}
                  </span>
                  <span className="text-xs text-slate-400 ml-1.5 font-medium">{m.unit_name}</span>
                </div>
              </div>
              <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-500 font-mono">
                <span>Total Cost: ${m.total_cost_usd.toFixed(2)}</span>
                <span>Volume: {m.total_volume.toLocaleString()}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Feature Gross Margin Health Matrix Table */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/40 overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
          <div>
            <h2 className="text-base font-semibold text-white">Feature Gross Margin Compliance Matrix</h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Scorecard comparing actual COGS profitability against business target margins.
            </p>
          </div>
          <Link
            to="/investigator"
            className="text-xs font-semibold text-emerald-400 hover:text-emerald-300 flex items-center gap-1"
          >
            Investigate Underperforming Features <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-950/80 border-b border-slate-800 text-slate-400 uppercase tracking-wider font-semibold text-[11px]">
              <tr>
                <th className="px-4 py-3">Product Feature</th>
                <th className="px-4 py-3">Tier</th>
                <th className="px-4 py-3 text-right">COGS (Cost)</th>
                <th className="px-4 py-3 text-right">Revenue</th>
                <th className="px-4 py-3 text-right">Gross Profit</th>
                <th className="px-4 py-3 text-center">Actual Margin</th>
                <th className="px-4 py-3 text-center">Target</th>
                <th className="px-4 py-3 text-center">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {isLoading ? (
                <tr>
                  <td colSpan={8} className="px-4 py-8 text-center text-slate-500">
                    Fusing ledger and telemetry...
                  </td>
                </tr>
              ) : (
                unitEcon?.margins.map((m) => (
                  <tr key={m.feature_id} className="hover:bg-slate-800/30 transition">
                    <td className="px-4 py-3 font-sans font-semibold text-white">{m.feature_name}</td>
                    <td className="px-4 py-3 font-sans">
                      <span className="px-2 py-0.5 rounded text-[10px] bg-slate-800 text-slate-300 capitalize">
                        {m.tier}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">${m.total_cost_usd.toFixed(2)}</td>
                    <td className="px-4 py-3 text-right text-emerald-400">
                      ${m.total_revenue_usd.toFixed(2)}
                    </td>
                    <td className="px-4 py-3 text-right font-semibold">
                      ${m.gross_profit_usd.toFixed(2)}
                    </td>
                    <td className="px-4 py-3 text-center font-bold">
                      {m.actual_gross_margin_percent !== undefined ? (
                        <span
                          className={
                            m.status === 'HEALTHY'
                              ? 'text-emerald-400'
                              : m.status === 'WARNING'
                              ? 'text-amber-400'
                              : 'text-rose-400'
                          }
                        >
                          {m.actual_gross_margin_percent.toFixed(1)}%
                        </span>
                      ) : (
                        <span className="text-slate-500">N/A</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-center text-slate-400">
                      {m.target_gross_margin_percent.toFixed(1)}%
                    </td>
                    <td className="px-4 py-3 text-center font-sans">{getStatusBadge(m.status)}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
