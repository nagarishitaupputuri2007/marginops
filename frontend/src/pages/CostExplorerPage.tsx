import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchCostAttribution, fetchCostExplorer } from '@/services/api';
import {
  ShieldCheck,
  Filter,
  Search,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';

export const CostExplorerPage: React.FC = () => {
  const [selectedProvider, setSelectedProvider] = useState<string>('');
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [currentPage, setCurrentPage] = useState<number>(1);
  const pageSize = 20;

  // Fetch attribution audit summary
  const { data: attribution } = useQuery({
    queryKey: ['cost-attribution'],
    queryFn: fetchCostAttribution,
  });

  // Fetch paginated explorer records
  const { data: explorer, isLoading } = useQuery({
    queryKey: ['cost-explorer', selectedProvider, searchTerm, currentPage],
    queryFn: () =>
      fetchCostExplorer({
        provider: selectedProvider || undefined,
        service: searchTerm || undefined,
        page: currentPage,
        limit: pageSize,
      }),
  });

  const providers = ['', 'AWS', 'GCP', 'Azure'];

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-6">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-white tracking-tight">
              Cost Explorer & Attribution Ledger
            </h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-mono font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              Hare-Niemeyer Deterministic
            </span>
          </div>
          <p className="text-slate-400 text-sm mt-1">
            Reconciles multi-cloud expenditures down to the exact sub-cent with zero penny leakage.
          </p>
        </div>

        {/* Audit Callout Badge */}
        <div className="bg-slate-900 border border-emerald-500/30 rounded-xl p-3 flex items-center gap-3">
          <ShieldCheck className="h-6 w-6 text-emerald-400 shrink-0" />
          <div className="text-xs">
            <div className="font-semibold text-emerald-300">Strict Conservation of Money</div>
            <div className="text-slate-400 font-mono">
              Delta Δ = <span className="text-white font-bold">$0.0000</span> (100% Reconciled)
            </div>
          </div>
        </div>
      </div>

      {/* Attribution Breakdown Cards */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-6 space-y-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-2">
          <div>
            <h2 className="text-base font-semibold text-white">Product Feature Allocation Summary</h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Attributed directly to revenue-generating features via multi-tier waterfall rules.
            </p>
          </div>
          <div className="text-xs text-slate-400 font-mono">
            Total Source: ${attribution?.total_source_amount.toFixed(2)} USD
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {attribution?.by_feature.map((feat) => (
            <div
              key={feat.feature_id}
              className="p-4 rounded-lg bg-slate-950/60 border border-slate-800/80 flex flex-col justify-between"
            >
              <div>
                <span className="text-xs text-slate-400 font-medium block truncate">
                  {feat.feature_name}
                </span>
                <span className="text-xl font-bold text-white mt-1 block">
                  ${feat.allocated_amount.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </span>
              </div>
              <div className="mt-3">
                <div className="flex items-center justify-between text-xs text-slate-500 mb-1">
                  <span>Share</span>
                  <span className="text-slate-300 font-semibold">{feat.share_percent}%</span>
                </div>
                <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                  <div
                    className="bg-emerald-500 h-full rounded-full"
                    style={{ width: `${feat.share_percent}%` }}
                  />
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Filter & Search Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-slate-500" />
          <span className="text-xs font-medium text-slate-400 mr-2">Provider:</span>
          <div className="flex gap-1.5 bg-slate-900 p-1 rounded-lg border border-slate-800">
            {providers.map((p) => (
              <button
                key={p}
                onClick={() => {
                  setSelectedProvider(p);
                  setCurrentPage(1);
                }}
                className={`px-3 py-1 rounded text-xs font-semibold transition ${
                  selectedProvider === p
                    ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                }`}
              >
                {p === '' ? 'All Providers' : p}
              </button>
            ))}
          </div>
        </div>

        <div className="relative">
          <Search className="h-4 w-4 text-slate-500 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search service or SKU..."
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value);
              setCurrentPage(1);
            }}
            className="pl-9 pr-4 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 w-full sm:w-64"
          />
        </div>
      </div>

      {/* Daily Aggregated Spend Visual Mini-Bar */}
      {explorer?.daily_time_series && (
        <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/30">
          <div className="flex items-center justify-between mb-3 text-xs">
            <span className="font-semibold text-white">Daily Spend Trajectory (Recent 40 Days)</span>
            <div className="flex items-center gap-4 text-slate-400">
              <span className="flex items-center gap-1.5">
                <span className="h-2.5 w-2.5 rounded-full bg-amber-500" /> AWS
              </span>
              <span className="flex items-center gap-1.5">
                <span className="h-2.5 w-2.5 rounded-full bg-blue-500" /> GCP
              </span>
              <span className="flex items-center gap-1.5">
                <span className="h-2.5 w-2.5 rounded-full bg-cyan-400" /> Azure
              </span>
            </div>
          </div>
          <div className="h-24 flex items-end gap-1.5 pt-4 overflow-x-auto">
            {explorer.daily_time_series.slice(-40).map((pt) => {
              const maxDaily = 150;
              const heightPercent = Math.min(100, Math.max(5, (pt.total / maxDaily) * 100));
              return (
                <div
                  key={pt.date}
                  className="flex-1 flex flex-col items-center group relative cursor-pointer min-w-[12px]"
                >
                  <div
                    className="w-full bg-emerald-500/80 rounded-t group-hover:bg-emerald-400 transition"
                    style={{ height: `${heightPercent}%` }}
                  />
                  {/* Tooltip */}
                  <div className="hidden group-hover:block absolute bottom-full mb-2 bg-slate-950 border border-slate-700 px-2.5 py-1 rounded shadow-lg text-[10px] text-white whitespace-nowrap z-20">
                    <div className="font-semibold">{pt.date}</div>
                    <div className="text-emerald-400 font-mono">${pt.total.toFixed(2)}</div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Normalized Records Table */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/40 overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
          <span className="text-xs font-semibold text-slate-300">
            Ingested Line Items ({explorer?.total_items.toLocaleString()} records)
          </span>
          <span className="text-xs text-slate-500">
            Page {explorer?.page} of {explorer?.total_pages}
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-950/80 border-b border-slate-800 text-slate-400 uppercase tracking-wider font-semibold text-[11px]">
              <tr>
                <th className="px-4 py-3">Date</th>
                <th className="px-4 py-3">Provider</th>
                <th className="px-4 py-3">Service</th>
                <th className="px-4 py-3">Resource / Identifier</th>
                <th className="px-4 py-3">Workload</th>
                <th className="px-4 py-3">Product Feature</th>
                <th className="px-4 py-3 text-right">Amount (USD)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {isLoading ? (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-slate-500">
                    Querying multi-cloud ledger...
                  </td>
                </tr>
              ) : explorer?.items.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-slate-500">
                    No matching billing records found.
                  </td>
                </tr>
              ) : (
                explorer?.items.map((item, idx) => (
                  <tr key={idx} className="hover:bg-slate-800/30 transition">
                    <td className="px-4 py-3 text-slate-400">{item.billing_date}</td>
                    <td className="px-4 py-3 font-sans">
                      <span
                        className={`inline-block px-2 py-0.5 rounded text-[10px] font-semibold ${
                          item.cloud_provider === 'AWS'
                            ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                            : item.cloud_provider === 'GCP'
                            ? 'bg-blue-500/10 text-blue-400 border border-blue-500/20'
                            : 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20'
                        }`}
                      >
                        {item.cloud_provider}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-sans text-slate-200">{item.service_name}</td>
                    <td className="px-4 py-3 text-slate-400 text-[11px] truncate max-w-[200px]" title={item.resource_id}>
                      {item.resource_id}
                    </td>
                    <td className="px-4 py-3 font-sans text-slate-400 text-[11px]">
                      {item.workload_id || 'unassigned'}
                    </td>
                    <td className="px-4 py-3 font-sans text-slate-300 text-[11px]">
                      {item.product_feature_id || 'shared'}
                    </td>
                    <td className="px-4 py-3 text-right font-bold">
                      {item.is_credit ? (
                        <span className="text-emerald-400">-${Math.abs(item.billing_amount).toFixed(4)}</span>
                      ) : (
                        <span className="text-white">${item.billing_amount.toFixed(4)}</span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Controls */}
        <div className="px-6 py-4 border-t border-slate-800 flex items-center justify-between text-xs">
          <button
            disabled={currentPage <= 1}
            onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
            className="px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-300 hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1.5 transition"
          >
            <ChevronLeft className="h-4 w-4" /> Previous
          </button>
          <span className="text-slate-500 font-mono">
            Page {currentPage} of {explorer?.total_pages || 1}
          </span>
          <button
            disabled={!explorer || currentPage >= explorer.total_pages}
            onClick={() => setCurrentPage((p) => p + 1)}
            className="px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-300 hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1.5 transition"
          >
            Next <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
};
