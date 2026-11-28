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
  Terminal,
  Bot,
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
      {/* Executive Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-zinc-800/80 pb-6">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-semibold text-zinc-100 tracking-tight">
              AI Incident Remediation & Cryptographic Governance Studio
            </h1>
            <span className="px-2.5 py-0.5 rounded-full text-[11px] font-mono font-medium bg-zinc-800 text-zinc-300 border border-zinc-700/60">
              Bounded Inspection Tools
            </span>
          </div>
          <p className="text-zinc-400 text-xs mt-1">
            Autonomous multi-cloud root cause analysis with read-only tools and cryptographically sealed human governance.
          </p>
        </div>

        <div className="bg-[#12141e] border border-zinc-800 rounded-lg px-3 py-1.5 flex items-center gap-2 text-xs">
          <Lock className="h-3.5 w-3.5 text-zinc-400" />
          <span className="text-zinc-400">
            Safety Policy: <span className="font-medium text-zinc-200">Zero Mutation Without Cryptographic Signature</span>
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Incident Selector Sidebar */}
        <div className="lg:col-span-1 space-y-3">
          <span className="text-xs font-semibold text-zinc-300 uppercase tracking-wider block">
            Incident Queue ({investigations?.length || 0})
          </span>

          <div className="space-y-2">
            {isLoading ? (
              <div className="text-xs text-zinc-500 p-4 font-sans">Loading reports...</div>
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
                        ? 'bg-zinc-800/90 border-zinc-700 shadow-sm'
                        : 'bg-[#0d0e15] border-zinc-800/80 hover:border-zinc-700 hover:bg-zinc-900/40'
                    }`}
                  >
                    <div>
                      <div className="flex items-center justify-between text-[11px] mb-1">
                        <span className="font-mono text-zinc-400 uppercase text-[10px]">{inv.anomaly_type}</span>
                        <span
                          className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${
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
                      <span className="text-xs font-medium text-zinc-200 line-clamp-2">
                        {inv.anomaly_title}
                      </span>
                    </div>

                    <div className="text-[10px] font-mono text-zinc-400 flex items-center justify-between pt-1 border-t border-zinc-800/80">
                      <span>{inv.evidence.length} Evidence Checkpoints</span>
                      <span>{inv.options.length} Remediation Choices</span>
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
              <div className="p-6 rounded-xl border border-zinc-800/80 bg-[#0d0e15] space-y-4 shadow-sm">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <span className="text-xs font-mono text-zinc-300 uppercase tracking-wider font-medium flex items-center gap-1.5">
                    <Bot className="h-4 w-4 text-zinc-400" />
                    Root Cause Analysis • {activeReport.anomaly_type}
                  </span>
                  <div className="text-xs text-zinc-400 flex items-center gap-1.5 font-mono">
                    <Clock className="h-3.5 w-3.5 text-zinc-400" />
                    <span>Investigated {activeReport.started_at.slice(0, 10)}</span>
                  </div>
                </div>

                <h2 className="text-base font-semibold text-zinc-100">{activeReport.anomaly_title}</h2>
                <p className="text-xs text-zinc-300 leading-relaxed">
                  {activeReport.executive_summary}
                </p>

                <div className="p-3.5 rounded-lg bg-zinc-900/70 border border-zinc-800 text-xs">
                  <span className="text-zinc-400 font-medium block mb-1">
                    Confirmed Primary Root Cause:
                  </span>
                  <span className="text-zinc-200 font-mono text-xs">
                    {activeReport.primary_root_cause}
                  </span>
                </div>
              </div>

              {/* 5-Step Diagnostic Protocol Stepper */}
              <div className="rounded-xl border border-zinc-800/80 bg-[#0d0e15] p-5 shadow-sm">
                <span className="text-xs font-semibold text-zinc-300 uppercase tracking-wider block mb-3">
                  Autonomous 5-Step Diagnostic Workflow
                </span>
                <div className="grid grid-cols-1 md:grid-cols-5 gap-3 text-xs">
                  <div className="p-3 rounded-lg bg-zinc-900/60 border border-zinc-800 flex flex-col justify-between">
                    <span className="font-mono text-zinc-400 text-[10px]">STEP 01</span>
                    <span className="font-medium text-zinc-200 mt-1">Anomaly Trigger</span>
                    <span className="text-emerald-400 text-[11px] mt-1 font-medium">Deviation Confirmed</span>
                  </div>

                  <div className="p-3 rounded-lg bg-zinc-900/60 border border-zinc-800 flex flex-col justify-between">
                    <span className="font-mono text-zinc-400 text-[10px]">STEP 02</span>
                    <span className="font-medium text-zinc-200 mt-1">Inspect Evidence</span>
                    <span className="text-zinc-300 text-[11px] mt-1">
                      {activeReport.evidence.length} Ledger Queries
                    </span>
                  </div>

                  <div className="p-3 rounded-lg bg-zinc-900/60 border border-zinc-800 flex flex-col justify-between">
                    <span className="font-mono text-zinc-400 text-[10px]">STEP 03</span>
                    <span className="font-medium text-zinc-200 mt-1">Rank Hypotheses</span>
                    <span className="text-zinc-300 text-[11px] mt-1">
                      {activeReport.hypotheses.length} Competing Causes
                    </span>
                  </div>

                  <div className="p-3 rounded-lg bg-zinc-900/60 border border-zinc-800 flex flex-col justify-between">
                    <span className="font-mono text-zinc-400 text-[10px]">STEP 04</span>
                    <span className="font-medium text-zinc-200 mt-1">Synthesize Fix</span>
                    <span className="text-zinc-300 text-[11px] mt-1">
                      {activeReport.options.length} Options Formulated
                    </span>
                  </div>

                  <div
                    className={`p-3 rounded-lg border flex flex-col justify-between ${
                      activeReport.approval_card?.status === 'approved'
                        ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
                        : 'bg-zinc-900/60 border-zinc-700 text-zinc-300'
                    }`}
                  >
                    <span className="font-mono text-[10px] text-zinc-400">STEP 05</span>
                    <span className="font-medium mt-1">Human Gate</span>
                    <span className="text-[11px] mt-1 font-mono font-semibold">
                      {activeReport.approval_card?.status.toUpperCase() || 'PENDING'}
                    </span>
                  </div>
                </div>
              </div>

              {/* Forensic Evidence Citations */}
              <div className="rounded-xl border border-zinc-800/80 bg-[#0d0e15] p-5 space-y-3 shadow-sm">
                <span className="text-xs font-semibold text-zinc-300 uppercase tracking-wider block">
                  Auditable Forensic Citations ({activeReport.evidence.length} Records Inspected)
                </span>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {activeReport.evidence.map((ev) => (
                    <div
                      key={ev.id}
                      className="p-3 rounded-lg bg-zinc-900/50 border border-zinc-800 text-xs font-mono space-y-1"
                    >
                      <div className="flex items-center justify-between text-zinc-400 text-[10px]">
                        <span>{ev.source_system}</span>
                        <span className="text-zinc-300 font-medium">{ev.evidence_type}</span>
                      </div>
                      <div className="text-zinc-300">
                        {ev.metric_name}:{' '}
                        <span className="text-zinc-100 font-semibold">{String(ev.metric_value)}</span>
                      </div>
                      <div className="text-[10px] text-zinc-400 truncate" title={ev.citation_ref}>
                        Ref: {ev.citation_ref}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Competing Hypotheses & Diagnostic Reasoning */}
              <div className="rounded-xl border border-zinc-800/80 bg-[#0d0e15] p-5 space-y-3 shadow-sm">
                <span className="text-xs font-semibold text-zinc-300 uppercase tracking-wider block">
                  Diagnostic Hypotheses & Confidence Calibration
                </span>
                <div className="space-y-3">
                  {activeReport.hypotheses.map((h) => (
                    <div
                      key={h.hypothesis_id}
                      className={`p-4 rounded-lg border text-xs space-y-2 ${
                        h.is_primary
                          ? 'bg-zinc-900/80 border-zinc-700'
                          : 'bg-zinc-900/40 border-zinc-800/80 opacity-70'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-zinc-800 text-zinc-300 font-medium border border-zinc-700/50">
                            {h.hypothesis_id}
                          </span>
                          <span className="font-medium text-zinc-100">{h.title}</span>
                          {h.is_primary && (
                            <span className="px-2 py-0.5 rounded text-[10px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-medium">
                              Primary Root Cause
                            </span>
                          )}
                        </div>
                        <span className="font-mono font-medium text-zinc-300">
                          {(h.confidence_score * 100).toFixed(0)}% Confidence
                        </span>
                      </div>
                      <p className="text-zinc-400 leading-relaxed">{h.description}</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Formulated Remediation Choices */}
              <div className="rounded-xl border border-zinc-800/80 bg-[#0d0e15] p-5 space-y-4 shadow-sm">
                <span className="text-xs font-semibold text-zinc-300 uppercase tracking-wider block">
                  Formulated Remediation Choices
                </span>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {activeReport.options.map((opt) => (
                    <div
                      key={opt.option_id}
                      className={`p-4 rounded-xl border flex flex-col justify-between space-y-3 ${
                        opt.is_recommended
                          ? 'bg-zinc-900/70 border-zinc-700'
                          : 'bg-zinc-900/40 border-zinc-800/80'
                      }`}
                    >
                      <div>
                        <div className="flex items-center justify-between text-xs mb-1.5">
                          <span className="font-mono text-zinc-400 text-[10px]">{opt.option_id}</span>
                          {opt.is_recommended && (
                            <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-emerald-500/10 text-emerald-300 border border-emerald-500/20">
                              Recommended Solution
                            </span>
                          )}
                        </div>
                        <h4 className="text-xs font-semibold text-zinc-100">{opt.title}</h4>
                        <p className="text-xs text-zinc-400 mt-1 leading-relaxed">{opt.description}</p>
                      </div>

                      <div className="pt-3 border-t border-zinc-800/80 space-y-2 text-xs">
                        <div className="flex items-center justify-between font-mono">
                          <span className="text-zinc-400">Est. Monthly Savings:</span>
                          <span className="font-medium text-emerald-400">
                            +${Number(opt.estimated_monthly_savings_usd).toFixed(2)}/mo
                          </span>
                        </div>
                        <div className="flex items-center justify-between text-[11px]">
                          <span className="text-zinc-400">Implementation Effort:</span>
                          <span className="font-medium text-zinc-300">{opt.implementation_effort}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Governed Human Approval Gate Card */}
              <div className="p-6 rounded-xl border border-zinc-700/80 bg-[#0d0e15] space-y-5 shadow-sm">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <ShieldCheck className="h-5 w-5 text-zinc-300" />
                    <div>
                      <h3 className="text-sm font-semibold text-zinc-100">
                        Governed Human Approval Gate
                      </h3>
                      <p className="text-xs text-zinc-400">
                        Zero destructive mutations permitted without explicit human signature.
                      </p>
                    </div>
                  </div>

                  <span
                    className={`px-3 py-1 rounded-md text-xs font-mono font-medium uppercase tracking-wider ${
                      activeReport.approval_card?.status === 'approved'
                        ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                        : activeReport.approval_card?.status === 'rejected'
                        ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                        : 'bg-zinc-800 text-zinc-300 border border-zinc-700'
                    }`}
                  >
                    {activeReport.approval_card?.status || 'PENDING_APPROVAL'}
                  </span>
                </div>

                {/* Gate Decision Form or Sealed Confirmation */}
                {activeReport.approval_card?.status === 'approved' ? (
                  <div className="p-4 rounded-lg bg-zinc-900/80 border border-zinc-800 space-y-3 text-xs">
                    <div className="flex items-center gap-2 text-emerald-400 font-medium">
                      <CheckCircle2 className="h-4 w-4" />
                      Remediation Approved & Cryptographically Sealed
                    </div>
                    <div className="text-zinc-300">
                      Approved by: <span className="font-mono text-zinc-100 font-medium">{activeReport.approval_card.reviewed_by}</span>
                    </div>
                    {activeReport.approval_card.review_notes && (
                      <div className="text-zinc-400">
                        Notes: <i>"{activeReport.approval_card.review_notes}"</i>
                      </div>
                    )}
                    <div className="pt-2 border-t border-zinc-800 flex flex-col sm:flex-row sm:items-center justify-between gap-2 font-mono text-[11px] text-zinc-400">
                      <span className="flex items-center gap-1.5">
                        <Fingerprint className="h-4 w-4 text-zinc-400" />
                        SHA-256 Audit Seal:
                      </span>
                      <span className="text-zinc-200 break-all select-all font-medium">
                        {activeReport.approval_card.audit_hash}
                      </span>
                    </div>

                    {/* Infrastructure-as-Code Runbook */}
                    <div className="pt-3 border-t border-zinc-800 space-y-2">
                      <div className="flex items-center justify-between text-zinc-300 font-medium">
                        <span className="flex items-center gap-1.5 text-xs">
                          <Terminal className="h-3.5 w-3.5 text-zinc-400" />
                          Certified Remediation Runbook & IaC Patch:
                        </span>
                        <span className="text-[10px] text-emerald-400 font-mono">Ready to Apply</span>
                      </div>
                      <div className="p-3 rounded-lg bg-black/60 border border-zinc-800 font-mono text-[11px] text-zinc-300 overflow-x-auto leading-relaxed">
                        {activeReport.anomaly_type === 'compute_spike' ? (
                          <div>
                            <div className="text-zinc-500"># 1. Update AWS Auto-Scaling Group ceiling</div>
                            <div className="text-zinc-200">aws autoscaling update-auto-scaling-group \</div>
                            <div className="pl-4 text-zinc-400">--auto-scaling-group-name data-pipeline-worker-asg \</div>
                            <div className="pl-4 text-zinc-400">--max-size 8 --desired-capacity 3 --region us-east-1</div>
                            <div className="text-zinc-500 mt-2"># 2. Terminate runaway worker instance gracefully</div>
                            <div className="text-zinc-200">aws autoscaling terminate-instance-in-auto-scaling-group \</div>
                            <div className="pl-4 text-zinc-400">--instance-id i-worker-pipeline-runaway \</div>
                            <div className="pl-4 text-zinc-400">--should-decrement-desired-capacity</div>
                          </div>
                        ) : activeReport.anomaly_type === 'storage_leak' ? (
                          <div>
                            <div className="text-zinc-500"># Terraform: Apply 30-day lifecycle expiration rule</div>
                            <div className="text-zinc-200">resource "aws_s3_bucket_lifecycle_configuration" "telemetry_exp" &#123;</div>
                            <div className="pl-4 text-zinc-400">bucket = "marginops-prod-raw-telemetry"</div>
                            <div className="pl-4 text-zinc-400">rule &#123;</div>
                            <div className="pl-8 text-zinc-400">id = "auto-expire-raw-after-30-days"</div>
                            <div className="pl-8 text-zinc-400">status = "Enabled"</div>
                            <div className="pl-8 text-zinc-400">expiration &#123; days = 30 &#125;</div>
                            <div className="pl-4 text-zinc-400">&#125;</div>
                            <div className="text-zinc-200">&#125;</div>
                          </div>
                        ) : activeReport.anomaly_type === 'ai_token_surge' ? (
                          <div>
                            <div className="text-zinc-500"># AI Gateway Policy: Apply reasoning depth cap & prompt caching</div>
                            <div className="text-zinc-200">PATCH /api/v1/agent-gateway/policy</div>
                            <div className="text-zinc-400">&#123;</div>
                            <div className="pl-4 text-zinc-400">"max_reasoning_steps": 4,</div>
                            <div className="pl-4 text-zinc-400">"prompt_caching_enabled": true,</div>
                            <div className="pl-4 text-zinc-400">"fallback_model": "anthropic.claude-3-5-haiku"</div>
                            <div className="text-zinc-400">&#125;</div>
                          </div>
                        ) : (
                          <div>
                            <div className="text-zinc-500"># Terminate orphaned idle staging database</div>
                            <div className="text-zinc-200">aws rds delete-db-instance \</div>
                            <div className="pl-4 text-zinc-400">--db-instance-identifier db-marginops-staging-replica-orphaned \</div>
                            <div className="pl-4 text-zinc-400">--skip-final-snapshot</div>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-xs font-medium text-zinc-400 mb-1">
                          Reviewer Corporate Identity
                        </label>
                        <input
                          type="email"
                          value={reviewerEmail}
                          onChange={(e) => setReviewerEmail(e.target.value)}
                          className="w-full px-3 py-2 rounded-lg bg-[#12141e] border border-zinc-800 text-xs text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-zinc-600 font-mono"
                          placeholder="engineer@acme.com"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-zinc-400 mb-1">
                          Approval / Policy Notes
                        </label>
                        <input
                          type="text"
                          value={reviewNotes}
                          onChange={(e) => setReviewNotes(e.target.value)}
                          className="w-full px-3 py-2 rounded-lg bg-[#12141e] border border-zinc-800 text-xs text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-zinc-600"
                          placeholder="e.g. Approved per FinOps runbook"
                        />
                      </div>
                    </div>

                    <div className="flex flex-wrap items-center gap-3 pt-2">
                      <button
                        onClick={handleApprove}
                        disabled={approveMutation.isPending}
                        className="px-4 py-2 rounded-lg bg-zinc-100 hover:bg-white text-zinc-900 text-xs font-semibold flex items-center gap-2 transition disabled:opacity-50"
                      >
                        <ShieldCheck className="h-4 w-4" />
                        {approveMutation.isPending
                          ? 'Sealing Cryptographic Hash...'
                          : 'Approve & Execute (Cryptographic Audit Seal)'}
                      </button>

                      <button
                        onClick={handleReject}
                        disabled={rejectMutation.isPending}
                        className="px-3.5 py-2 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 border border-rose-500/30 text-xs font-medium flex items-center gap-2 transition disabled:opacity-50"
                      >
                        <XCircle className="h-4 w-4" />
                        Reject Remediation
                      </button>

                      <button
                        onClick={handleDismiss}
                        disabled={dismissMutation.isPending}
                        className="px-3.5 py-2 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-xs font-medium transition disabled:opacity-50"
                      >
                        Dismiss as Expected
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="p-12 text-center text-zinc-500">No incident selected.</div>
          )}
        </div>
      </div>
    </div>
  );
};
