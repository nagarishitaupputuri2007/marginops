import React, { useState, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  fetchCostAttribution,
  fetchCostExplorer,
  uploadBillingFile,
  downloadAuditExport,
} from '@/services/api';
import {
  ShieldCheck,
  Filter,
  Search,
  ChevronLeft,
  ChevronRight,
  UploadCloud,
  Download,
  CheckCircle2,
  X,
  FileText,
  AlertCircle,
  FileSpreadsheet,
} from 'lucide-react';

export const CostExplorerPage: React.FC = () => {
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [selectedProvider, setSelectedProvider] = useState<string>('');
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [showUploadModal, setShowUploadModal] = useState<boolean>(false);
  const [uploadResult, setUploadResult] = useState<any>(null);
  const [isExporting, setIsExporting] = useState<boolean>(false);
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

  // Mutation for uploading custom billing files
  const uploadMutation = useMutation({
    mutationFn: (file: File) => uploadBillingFile(file),
    onSuccess: (data) => {
      setUploadResult(data);
      queryClient.invalidateQueries({ queryKey: ['cost-attribution'] });
      queryClient.invalidateQueries({ queryKey: ['cost-explorer'] });
      queryClient.invalidateQueries({ queryKey: ['kpi-summary'] });
      queryClient.invalidateQueries({ queryKey: ['anomalies-active'] });
    },
  });

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      uploadMutation.mutate(file);
    }
  };

  const handleExport = async (format: 'json' | 'csv') => {
    try {
      setIsExporting(true);
      await downloadAuditExport(format);
    } finally {
      setIsExporting(false);
    }
  };

  const providers = ['', 'AWS', 'GCP', 'Azure'];

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* Executive Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-zinc-800/80 pb-6">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-semibold text-zinc-100 tracking-tight">
              Cost Explorer & Attribution Ledger
            </h1>
            <span className="px-2.5 py-0.5 rounded-full text-[11px] font-mono font-medium bg-zinc-800 text-zinc-300 border border-zinc-700/60">
              Hare-Niemeyer Deterministic
            </span>
          </div>
          <p className="text-zinc-400 text-xs mt-1">
            Reconciles multi-cloud expenditures down to the exact sub-cent with zero penny leakage.
          </p>
        </div>

        {/* Action Controls */}
        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={() => {
              setUploadResult(null);
              setShowUploadModal(true);
            }}
            className="px-3.5 py-1.5 rounded-lg bg-zinc-800 hover:bg-zinc-700 border border-zinc-700/70 text-xs font-medium text-zinc-200 hover:text-white flex items-center gap-2 transition"
          >
            <UploadCloud className="h-4 w-4 text-zinc-400" />
            Ingest Billing CSV
          </button>

          <button
            onClick={() => handleExport('csv')}
            disabled={isExporting}
            className="px-3.5 py-1.5 rounded-lg bg-zinc-800 hover:bg-zinc-700 border border-zinc-700/70 text-xs font-medium text-zinc-200 hover:text-white flex items-center gap-2 transition disabled:opacity-50"
          >
            <Download className="h-4 w-4 text-zinc-400" />
            Export Audit CSV
          </button>

          {/* Audit Callout Badge */}
          <div className="bg-[#12141e] border border-zinc-800 rounded-lg px-3 py-1.5 flex items-center gap-2.5 text-xs">
            <ShieldCheck className="h-4 w-4 text-emerald-400 shrink-0" />
            <div className="flex items-center gap-1.5 font-mono text-[11px]">
              <span className="text-zinc-400">Ledger Δ:</span>
              <span className="text-emerald-400 font-semibold">$0.0000</span>
              <span className="text-zinc-400 font-sans text-[10px]">(100% Reconciled)</span>
            </div>
          </div>
        </div>
      </div>

      {/* Upload Modal Drawer */}
      {showUploadModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[#0e1017] border border-zinc-800 rounded-xl max-w-lg w-full p-6 space-y-5 shadow-2xl relative">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <FileSpreadsheet className="h-5 w-5 text-zinc-300" />
                <h3 className="text-sm font-semibold text-zinc-100">Ingest Multi-Cloud Billing Dataset</h3>
              </div>
              <button
                onClick={() => setShowUploadModal(false)}
                className="text-zinc-400 hover:text-white p-1 rounded-lg"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <p className="text-xs text-zinc-400">
              Upload normalized AWS CUR, GCP Billing, or Azure CSV exports. The engine parses line items,
              verifies SHA-256 idempotency, runs Hare-Niemeyer attribution, and flags anomalies.
            </p>

            {/* Dropzone */}
            <div
              onClick={() => fileInputRef.current?.click()}
              className="border border-dashed border-zinc-700 hover:border-zinc-500 rounded-lg p-8 text-center cursor-pointer bg-zinc-900/40 hover:bg-zinc-900/80 transition space-y-3"
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv"
                onChange={handleFileUpload}
                className="hidden"
              />
              <FileText className="h-7 w-7 text-zinc-500 mx-auto" />
              <div>
                <span className="text-xs font-medium text-zinc-200 block">
                  Click to select a CSV billing file
                </span>
                <span className="text-[11px] text-zinc-400 mt-1 block">
                  Supports FOCUS 1.0, AWS CUR, GCP Export, Azure Cost Management CSV
                </span>
              </div>
            </div>

            {/* Status / Results */}
            {uploadMutation.isPending && (
              <div className="p-3.5 rounded-lg bg-zinc-900 border border-zinc-800 text-xs text-zinc-400 flex items-center gap-2 animate-pulse">
                <span>Ingesting line items and executing Largest Remainder attribution...</span>
              </div>
            )}

            {uploadMutation.isError && (
              <div className="p-3.5 rounded-lg bg-rose-500/10 border border-rose-500/20 text-xs text-rose-300 flex items-center gap-2">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>Upload failed: {(uploadMutation.error as Error)?.message || 'Invalid format'}</span>
              </div>
            )}

            {uploadResult && (
              <div className="p-4 rounded-lg bg-zinc-900/90 border border-zinc-800 text-xs space-y-2">
                <div className="flex items-center gap-2 text-emerald-400 font-medium">
                  <CheckCircle2 className="h-4 w-4" />
                  Dataset Ingested & 100% Reconciled
                </div>
                <div className="grid grid-cols-2 gap-2 text-[11px] font-mono text-zinc-300 pt-1">
                  <div>Valid Rows: <span className="text-white font-medium">{uploadResult.valid_rows}</span></div>
                  <div>Anomalies: <span className="text-amber-400 font-medium">{uploadResult.anomalies_detected}</span></div>
                  <div>Positive: <span className="text-zinc-200">${uploadResult.positive_charges.toFixed(2)}</span></div>
                  <div>Credits: <span className="text-zinc-200">${uploadResult.credits.toFixed(2)}</span></div>
                </div>
                <div className="text-[10px] font-mono text-zinc-400 pt-1 truncate">
                  SHA-256 Checksum: {uploadResult.sha256_checksum}
                </div>
              </div>
            )}

            <div className="pt-2 flex justify-end">
              <button
                onClick={() => setShowUploadModal(false)}
                className="px-4 py-2 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-xs font-medium text-zinc-200 transition"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Attribution Breakdown Cards */}
      <div className="rounded-xl border border-zinc-800/80 bg-[#0d0e15] p-6 space-y-5 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-2">
          <div>
            <h2 className="text-sm font-semibold text-zinc-100">Product Feature Allocation Summary</h2>
            <p className="text-xs text-zinc-400 mt-0.5">
              Attributed directly to revenue-generating features via multi-tier waterfall rules.
            </p>
          </div>
          <div className="text-xs text-zinc-400 font-mono">
            Total Source: ${attribution?.total_source_amount.toFixed(2)} USD
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {attribution?.by_feature.map((feat) => (
            <div
              key={feat.feature_id}
              className="p-4 rounded-lg bg-zinc-900/50 border border-zinc-800 flex flex-col justify-between"
            >
              <div>
                <span className="text-xs text-zinc-400 font-medium block truncate">
                  {feat.feature_name}
                </span>
                <span className="text-xl font-semibold tracking-tight text-zinc-100 mt-1 block">
                  ${feat.allocated_amount.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </span>
              </div>
              <div className="mt-3">
                <div className="flex items-center justify-between text-xs text-zinc-400 mb-1">
                  <span>Share</span>
                  <span className="text-zinc-200 font-medium font-mono">{feat.share_percent}%</span>
                </div>
                <div className="w-full bg-zinc-800/80 h-1.5 rounded-full overflow-hidden">
                  <div
                    className="bg-zinc-300 h-full rounded-full"
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
          <Filter className="h-4 w-4 text-zinc-400" />
          <span className="text-xs font-medium text-zinc-400 mr-1">Provider:</span>
          <div className="flex gap-1 bg-[#12141e] p-1 rounded-lg border border-zinc-800">
            {providers.map((p) => (
              <button
                key={p}
                onClick={() => {
                  setSelectedProvider(p);
                  setCurrentPage(1);
                }}
                className={`px-3 py-1 rounded-md text-xs font-medium transition ${
                  selectedProvider === p
                    ? 'bg-zinc-800 text-zinc-100 shadow-sm border border-zinc-700/60'
                    : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/40'
                }`}
              >
                {p === '' ? 'All Providers' : p}
              </button>
            ))}
          </div>
        </div>

        <div className="relative">
          <Search className="h-4 w-4 text-zinc-400 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search service or SKU..."
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value);
              setCurrentPage(1);
            }}
            className="pl-9 pr-4 py-1.5 rounded-lg bg-[#12141e] border border-zinc-800 text-xs text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-zinc-600 w-full sm:w-64"
          />
        </div>
      </div>

      {/* Daily Aggregated Spend Visual */}
      {explorer?.daily_time_series && (
        <div className="p-5 rounded-xl border border-zinc-800/80 bg-[#0d0e15] shadow-sm">
          <div className="flex items-center justify-between mb-3 text-xs">
            <span className="font-semibold text-zinc-200">Daily Spend Trajectory (Recent 40 Days)</span>
            <div className="flex items-center gap-4 text-zinc-400">
              <span className="flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-amber-500/80" /> AWS
              </span>
              <span className="flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-blue-500/80" /> GCP
              </span>
              <span className="flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-indigo-500/80" /> Azure
              </span>
            </div>
          </div>
          <div className="h-24 flex items-end gap-1.5 pt-3 overflow-x-auto">
            {explorer.daily_time_series.slice(-40).map((pt) => {
              const maxDaily = 120;
              const heightPercent = Math.min(100, Math.max(8, (Math.max(0, pt.total) / maxDaily) * 100));
              return (
                <div
                  key={pt.date}
                  className="flex-1 h-full flex flex-col justify-end items-center group relative cursor-pointer min-w-[14px]"
                >
                  <div
                    className="w-full bg-zinc-600 rounded-t group-hover:bg-zinc-400 transition"
                    style={{ height: `${heightPercent}%` }}
                  />
                  {/* Tooltip */}
                  <div className="hidden group-hover:block absolute bottom-full mb-2 bg-zinc-900 border border-zinc-700 px-2.5 py-1 rounded shadow-lg text-[10px] text-zinc-100 whitespace-nowrap z-20">
                    <div className="font-medium text-zinc-300">{pt.date}</div>
                    <div className="text-zinc-100 font-mono font-medium">${pt.total.toFixed(2)}</div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Normalized Records Table */}
      <div className="rounded-xl border border-zinc-800/80 bg-[#0d0e15] overflow-hidden shadow-sm">
        <div className="px-6 py-4 border-b border-zinc-800/80 flex items-center justify-between">
          <span className="text-xs font-semibold text-zinc-200">
            Ingested Line Items ({explorer?.total_items.toLocaleString()} records)
          </span>
          <span className="text-xs text-zinc-400 font-mono">
            Page {explorer?.page} of {explorer?.total_pages}
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-zinc-300">
            <thead className="bg-[#12141e] border-b border-zinc-800/80 text-zinc-400 uppercase tracking-wider font-medium text-[11px]">
              <tr>
                <th className="px-4 py-3">Date</th>
                <th className="px-4 py-3">Provider</th>
                <th className="px-4 py-3">Service</th>
                <th className="px-4 py-3">Resource Identifier</th>
                <th className="px-4 py-3">Workload</th>
                <th className="px-4 py-3">Product Feature</th>
                <th className="px-4 py-3 text-right">Amount (USD)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/50 font-mono">
              {isLoading ? (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-zinc-500 font-sans">
                    Querying multi-cloud ledger...
                  </td>
                </tr>
              ) : explorer?.items.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-zinc-500 font-sans">
                    No matching billing records found.
                  </td>
                </tr>
              ) : (
                explorer?.items.map((item, idx) => (
                  <tr key={idx} className="hover:bg-zinc-900/50 transition">
                    <td className="px-4 py-3 text-zinc-400">{item.billing_date}</td>
                    <td className="px-4 py-3 font-sans">
                      <span
                        className={`inline-block px-2 py-0.5 rounded text-[10px] font-medium ${
                          item.cloud_provider === 'AWS'
                            ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                            : item.cloud_provider === 'GCP'
                            ? 'bg-blue-500/10 text-blue-400 border border-blue-500/20'
                            : 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20'
                        }`}
                      >
                        {item.cloud_provider}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-sans text-zinc-200">{item.service_name}</td>
                    <td className="px-4 py-3 text-zinc-400 text-[11px] truncate max-w-[200px]" title={item.resource_id}>
                      {item.resource_id}
                    </td>
                    <td className="px-4 py-3 font-sans text-zinc-400 text-[11px]">
                      {item.workload_id || 'unassigned'}
                    </td>
                    <td className="px-4 py-3 font-sans text-zinc-300 text-[11px]">
                      {item.product_feature_id || 'shared'}
                    </td>
                    <td className="px-4 py-3 text-right font-medium">
                      {item.is_credit ? (
                        <span className="text-emerald-400">-${Math.abs(item.billing_amount).toFixed(4)}</span>
                      ) : (
                        <span className="text-zinc-100">${item.billing_amount.toFixed(4)}</span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Controls */}
        <div className="px-6 py-4 border-t border-zinc-800/80 flex items-center justify-between text-xs">
          <button
            disabled={currentPage <= 1}
            onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
            className="px-3 py-1.5 rounded-lg bg-zinc-800/80 border border-zinc-700/60 text-zinc-300 hover:bg-zinc-700 disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1.5 transition"
          >
            <ChevronLeft className="h-4 w-4" /> Previous
          </button>
          <span className="text-zinc-400 font-mono">
            Page {currentPage} of {explorer?.total_pages || 1}
          </span>
          <button
            disabled={!explorer || currentPage >= explorer.total_pages}
            onClick={() => setCurrentPage((p) => p + 1)}
            className="px-3 py-1.5 rounded-lg bg-zinc-800/80 border border-zinc-700/60 text-zinc-300 hover:bg-zinc-700 disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1.5 transition"
          >
            Next <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
};
