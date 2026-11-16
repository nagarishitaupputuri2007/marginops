import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  fetchInvestigations,
  approveInvestigation,
  rejectInvestigation,
  dismissInvestigation,
} from '@/services/api';
import {
  ShieldCheck,
  CheckCircle2,
  XCircle,
  Lock,
  Clock,
  Fingerprint,
} from 'lucide-react';

export const InvestigatorPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [selectedId, setSelectedId] = useState<string>('');
  const [reviewerEmail, setReviewerEmail] = useState<string>('finops-lead@acme.com');
  const [reviewNotes, setReviewNotes] = useState<string>('Approved per Q3 infrastructure optimization policy');

  const { data: investigations, isLoading } = useQuery({
    queryKey: ['investigations-list'],
    queryFn: fetchInvestigations,
  });

  const activeReport =
    investigations?.find((inv) => (selectedId ? inv.id === selectedId : true)) ||
    investigations?.[0];

  // Mutation for approval
  const approveMutation = useMutation({
    mutationFn: ({ id, email, notes }: { id: string; email: string; notes?: string }) =>
      approveInvestigation(id, email, notes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['investigations-list'] });
    },
  });

  // Mutation for reject
  const rejectMutation = useMutation({
    mutationFn: ({ id, email, notes }: { id: string; email: string; notes?: string }) =>
      rejectInvestigation(id, email, notes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['investigations-list'] });
    },
  });

  // Mutation for dismiss
  const dismissMutation = useMutation({
    mutationFn: ({ id, email, notes }: { id: string; email: string; notes?: string }) =>
      dismissInvestigation(id, email, notes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['investigations-list'] });
    },
  });

  const handleApprove = () => {
    if (!activeReport) return;
    approveMutation.mutate({
      id: activeReport.id,
      email: reviewerEmail,
      notes: reviewNotes,
    });
  };

  const handleReject = () => {
    if (!activeReport) return;
    rejectMutation.mutate({
      id: activeReport.id,
      email: reviewerEmail,
      notes: reviewNotes,
    });
  };

  const handleDismiss = () => {
    if (!activeReport) return;
    dismissMutation.mutate({
      id: activeReport.id,
      email: reviewerEmail,
      notes: reviewNotes,
    });
  };

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-6">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-white tracking-tight">
              Evidence-Led AI Investigator & Human Approval Gate
            </h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-mono font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              Slide 06 Protocol
            </span>
          </div>
          <p className="text-slate-400 text-sm mt-1">
            Autonomous multi-cloud root cause analysis with bounded read-only tools and cryptographically sealed human governance.
          </p>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl px-4 py-2 flex items-center gap-3">
          <Lock className="h-4 w-4 text-emerald-400" />
          <span className="text-xs text-slate-300">
            Safety Invariant: <span className="font-semibold text-white">Zero Mutation Without Signature</span>
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Incident Selector Sidebar */}
        <div className="lg:col-span-1 space-y-3">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">
            Investigated Incidents ({investigations?.length || 0})
          </span>

          <div className="space-y-2">
            {isLoading ? (
              <div className="text-xs text-slate-500 p-4">Loading reports...</div>
            ) : (
              investigations?.map((inv) => {
                const isSelected = activeReport?.id === inv.id;
                const status = inv.approval_card?.status || inv.status;
                return (
                  <button
                    key={inv.id}
                    onClick={() => setSelectedId(inv.id)}
                    className={`w-full text-left p-3.5 rounded-xl border transition flex flex-col justify-between space-y-2 ${
                      isSelected
                        ? 'bg-slate-900 border-emerald-500/60 shadow-sm'
                        : 'bg-slate-950/60 border-slate-800 hover:border-slate-700 hover:bg-slate-900/40'
                    }`}
                  >
                    <div>
                      <div className="flex items-center justify-between text-[11px] mb-1">
                        <span className="font-mono text-slate-500 uppercase">{inv.anomaly_type}</span>
                        <span
                          className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${
                            status === 'approved'
                              ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                              : status === 'rejected'
                              ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                              : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                          }`}
                        >
                          {status.toUpperCase()}
                        </span>
                      </div>
                      <span className="text-xs font-semibold text-slate-200 line-clamp-2">
                        {inv.anomaly_title}
                      </span>
                    </div>

                    <div className="text-[10px] font-mono text-slate-500 flex items-center justify-between pt-1 border-t border-slate-900">
                      <span>{inv.evidence.length} Evidence</span>
                      <span>{inv.options.length} Options</span>
                    </div>
                  </button>
                );
              })
            )}
          </div>
        </div>

        {/* Investigation Details & War Room */}
        <div className="lg:col-span-3 space-y-6">
          {activeReport ? (
            <>
              {/* Executive Summary Banner */}
              <div className="p-6 rounded-xl border border-slate-800 bg-slate-900/40 space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <span className="text-xs font-mono text-emerald-400 uppercase tracking-wider font-semibold">
                    Incident Root Cause Analysis • {activeReport.anomaly_type}
                  </span>
                  <div className="text-xs text-slate-500 flex items-center gap-1.5 font-mono">
                    <Clock className="h-3.5 w-3.5 text-slate-400" />
                    <span>Investigated {activeReport.started_at.slice(0, 10)}</span>
                  </div>
                </div>

                <h2 className="text-lg font-bold text-white">{activeReport.anomaly_title}</h2>
                <p className="text-sm text-slate-300 leading-relaxed">
                  {activeReport.executive_summary}
                </p>

                <div className="p-3.5 rounded-lg bg-slate-950 border border-slate-800 text-xs">
                  <span className="text-slate-400 font-semibold block mb-1">
                    Confirmed Primary Root Cause:
                  </span>
                  <span className="text-emerald-300 font-mono">
                    {activeReport.primary_root_cause}
                  </span>
                </div>
              </div>

              {/* 5-Step Diagnostic Protocol Stepper */}
              <div className="rounded-xl border border-slate-800 bg-slate-900/30 p-5">
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-3">
                  Slide 06 Autonomous Investigation Protocol
                </span>
                <div className="grid grid-cols-1 md:grid-cols-5 gap-3 text-xs">
                  <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 flex flex-col justify-between">
                    <span className="font-mono text-slate-500 text-[10px]">STEP 01</span>
                    <span className="font-semibold text-white mt-1">Anomaly Trigger</span>
                    <span className="text-emerald-400 text-[11px] mt-1">Breach Confirmed</span>
                  </div>

                  <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 flex flex-col justify-between">
                    <span className="font-mono text-slate-500 text-[10px]">STEP 02</span>
                    <span className="font-semibold text-white mt-1">Gather Evidence</span>
                    <span className="text-emerald-400 text-[11px] mt-1">
                      {activeReport.evidence.length} Ledger Queries
                    </span>
                  </div>

                  <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 flex flex-col justify-between">
                    <span className="font-mono text-slate-500 text-[10px]">STEP 03</span>
                    <span className="font-semibold text-white mt-1">Hypotheses Rank</span>
                    <span className="text-emerald-400 text-[11px] mt-1">
                      {activeReport.hypotheses.length} Competing Causes
                    </span>
                  </div>

                  <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 flex flex-col justify-between">
                    <span className="font-mono text-slate-500 text-[10px]">STEP 04</span>
                    <span className="font-semibold text-white mt-1">Remediation Plan</span>
                    <span className="text-emerald-400 text-[11px] mt-1">
                      {activeReport.options.length} Options Formulated
                    </span>
                  </div>

                  <div
                    className={`p-3 rounded-lg border flex flex-col justify-between ${
                      activeReport.approval_card?.status === 'approved'
                        ? 'bg-emerald-950/20 border-emerald-500/40 text-emerald-300'
                        : 'bg-slate-950 border-amber-500/30 text-amber-300'
                    }`}
                  >
                    <span className="font-mono text-[10px] opacity-75">STEP 05</span>
                    <span className="font-semibold mt-1">Human Gate</span>
                    <span className="text-[11px] mt-1 font-bold">
                      {activeReport.approval_card?.status.toUpperCase() || 'PENDING'}
                    </span>
                  </div>
                </div>
              </div>

              {/* Forensic Evidence Citations */}
              <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-5 space-y-3">
                <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider block">
                  Auditable Forensic Citations ({activeReport.evidence.length} Records Checked)
                </span>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {activeReport.evidence.map((ev) => (
                    <div
                      key={ev.id}
                      className="p-3 rounded-lg bg-slate-950 border border-slate-800 text-xs font-mono space-y-1"
                    >
                      <div className="flex items-center justify-between text-slate-500 text-[10px]">
                        <span>{ev.source_system}</span>
                        <span className="text-emerald-400 font-semibold">{ev.evidence_type}</span>
                      </div>
                      <div className="text-slate-300 font-semibold">
                        {ev.metric_name}:{' '}
                        <span className="text-white font-bold">{String(ev.metric_value)}</span>
                      </div>
                      <div className="text-[10px] text-slate-500 truncate" title={ev.citation_ref}>
                        Ref: {ev.citation_ref}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Competing Hypotheses & Diagnostic Reasoning */}
              <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-5 space-y-3">
                <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider block">
                  Diagnostic Hypotheses & Confidence Calibration
                </span>
                <div className="space-y-3">
                  {activeReport.hypotheses.map((h) => (
                    <div
                      key={h.hypothesis_id}
                      className={`p-4 rounded-lg border text-xs space-y-2 ${
                        h.is_primary
                          ? 'bg-emerald-950/15 border-emerald-500/40'
                          : 'bg-slate-950/60 border-slate-800 opacity-70'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-bold">
                            {h.hypothesis_id}
                          </span>
                          <span className="font-bold text-white">{h.title}</span>
                          {h.is_primary && (
                            <span className="px-2 py-0.5 rounded text-[10px] bg-emerald-500/20 text-emerald-400 font-semibold">
                              Primary Root Cause
                            </span>
                          )}
                        </div>
                        <span className="font-mono font-bold text-slate-300">
                          {(h.confidence_score * 100).toFixed(0)}% Confidence
                        </span>
                      </div>
                      <p className="text-slate-400">{h.description}</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Recommended Options */}
              <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-5 space-y-4">
                <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider block">
                  Formulated Remediation Choices
                </span>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {activeReport.options.map((opt) => (
                    <div
                      key={opt.option_id}
                      className={`p-4 rounded-xl border flex flex-col justify-between space-y-3 ${
                        opt.is_recommended
                          ? 'bg-emerald-950/10 border-emerald-500/40'
                          : 'bg-slate-950 border-slate-800'
                      }`}
                    >
                      <div>
                        <div className="flex items-center justify-between text-xs mb-1.5">
                          <span className="font-mono text-slate-400 text-[10px]">{opt.option_id}</span>
                          {opt.is_recommended && (
                            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-300">
                              Primary Recommendation
                            </span>
                          )}
                        </div>
                        <h4 className="text-sm font-bold text-white">{opt.title}</h4>
                        <p className="text-xs text-slate-400 mt-1">{opt.description}</p>
                      </div>

                      <div className="pt-3 border-t border-slate-800/80 space-y-2 text-xs">
                        <div className="flex items-center justify-between font-mono">
                          <span className="text-slate-500">Est. Monthly Savings:</span>
                          <span className="font-bold text-emerald-400">
                            +${Number(opt.estimated_monthly_savings_usd).toFixed(2)}/mo
                          </span>
                        </div>
                        <div className="flex items-center justify-between text-[11px]">
                          <span className="text-slate-500">Effort:</span>
                          <span className="font-semibold text-slate-300">{opt.implementation_effort}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Governed Human Approval Gate Card (Slide 06) */}
              <div className="p-6 rounded-xl border border-emerald-500/40 bg-gradient-to-b from-slate-900 via-slate-900/90 to-slate-950 space-y-5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <ShieldCheck className="h-6 w-6 text-emerald-400" />
                    <div>
                      <h3 className="text-base font-bold text-white">
                        Governed Human Approval Gate
                      </h3>
                      <p className="text-xs text-slate-400">
                        Zero destructive mutations permitted without explicit human signature.
                      </p>
                    </div>
                  </div>

                  <span
                    className={`px-3 py-1 rounded-full text-xs font-mono font-bold uppercase tracking-wider ${
                      activeReport.approval_card?.status === 'approved'
                        ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40'
                        : activeReport.approval_card?.status === 'rejected'
                        ? 'bg-rose-500/20 text-rose-400 border border-rose-500/40'
                        : 'bg-amber-500/20 text-amber-300 border border-amber-500/40 animate-pulse'
                    }`}
                  >
                    {activeReport.approval_card?.status || 'PENDING_APPROVAL'}
                  </span>
                </div>

                {/* Gate Decision Form or Sealed Confirmation */}
                {activeReport.approval_card?.status === 'approved' ? (
                  <div className="p-4 rounded-lg bg-emerald-950/30 border border-emerald-500/30 space-y-3 text-xs">
                    <div className="flex items-center gap-2 text-emerald-400 font-semibold">
                      <CheckCircle2 className="h-4 w-4" />
                      Remediation Approved & Cryptographically Sealed
                    </div>
                    <div className="text-slate-300">
                      Approved by: <span className="font-mono text-white font-semibold">{activeReport.approval_card.reviewed_by}</span>
                    </div>
                    {activeReport.approval_card.review_notes && (
                      <div className="text-slate-400">
                        Notes: <i>"{activeReport.approval_card.review_notes}"</i>
                      </div>
                    )}
                    <div className="pt-2 border-t border-emerald-900/50 flex flex-col sm:flex-row sm:items-center justify-between gap-2 font-mono text-[11px] text-slate-400">
                      <span className="flex items-center gap-1.5">
                        <Fingerprint className="h-4 w-4 text-emerald-400" />
                        SHA-256 Audit Seal:
                      </span>
                      <span className="text-emerald-300 break-all select-all font-semibold">
                        {activeReport.approval_card.audit_hash}
                      </span>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-xs font-medium text-slate-400 mb-1">
                          Reviewer Corporate Identity
                        </label>
                        <input
                          type="email"
                          value={reviewerEmail}
                          onChange={(e) => setReviewerEmail(e.target.value)}
                          className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 font-mono"
                          placeholder="engineer@acme.com"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-slate-400 mb-1">
                          Approval / Policy Notes
                        </label>
                        <input
                          type="text"
                          value={reviewNotes}
                          onChange={(e) => setReviewNotes(e.target.value)}
                          className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
                          placeholder="e.g. Approved per FinOps runbook"
                        />
                      </div>
                    </div>

                    <div className="flex flex-wrap items-center gap-3 pt-2">
                      <button
                        onClick={handleApprove}
                        disabled={approveMutation.isPending}
                        className="px-5 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold flex items-center gap-2 transition shadow-lg shadow-emerald-900/20 disabled:opacity-50"
                      >
                        <ShieldCheck className="h-4 w-4" />
                        {approveMutation.isPending
                          ? 'Sealing Cryptographic Hash...'
                          : 'Approve & Execute (Cryptographic Audit Seal)'}
                      </button>

                      <button
                        onClick={handleReject}
                        disabled={rejectMutation.isPending}
                        className="px-4 py-2.5 rounded-lg bg-rose-600/20 hover:bg-rose-600/30 text-rose-300 border border-rose-500/30 text-xs font-semibold flex items-center gap-2 transition disabled:opacity-50"
                      >
                        <XCircle className="h-4 w-4" />
                        Reject Remediation
                      </button>

                      <button
                        onClick={handleDismiss}
                        disabled={dismissMutation.isPending}
                        className="px-4 py-2.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold transition disabled:opacity-50"
                      >
                        Dismiss as Expected
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="p-12 text-center text-slate-500">No incident selected.</div>
          )}
        </div>
      </div>
    </div>
  );
};
