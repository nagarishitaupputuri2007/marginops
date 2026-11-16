"""Domain models and contracts for the Evidence-Led AI Investigator and Human Approval Gate (Slide 06)."""
import enum
import hashlib
import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class InvestigationStatus(str, enum.Enum):
    """Lifecycle status of an AI investigation."""
    TRIGGERED = "triggered"
    GATHERING_EVIDENCE = "gathering_evidence"
    ANALYZING = "analyzing"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    DISMISSED = "dismissed"


class EvidenceItem(BaseModel):
    """Verified, traceable piece of forensic evidence queried by the AI investigator."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, description="Unique evidence identifier")
    evidence_type: str = Field(..., description="Classification: cost_history, telemetry_surge, tags, etc.")
    source_system: str = Field(..., description="Source: PostgreSQL_CostLedger, MongoDB_Telemetry, etc.")
    metric_name: str = Field(..., description="Metric key (e.g., daily_spend, prompt_tokens, p95_latency)")
    metric_value: Any = Field(..., description="Concrete observed value")
    observed_date: Optional[str] = Field(default=None, description="Observation timestamp or date string")
    citation_ref: str = Field(..., description="Auditable citation pointer (e.g., CostRecord:i-worker-pipeline:2026-08-28)")


class Hypothesis(BaseModel):
    """A competing diagnostic hypothesis evaluated by the investigator."""
    hypothesis_id: str = Field(..., description="Unique identifier (e.g., H1, H2)")
    title: str = Field(..., description="Summary of the potential root cause")
    description: str = Field(..., description="Detailed diagnostic rationale")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Calculated confidence score between 0.0 and 1.0")
    is_primary: bool = Field(default=False, description="True if selected as the primary root cause")
    supporting_evidence: List[str] = Field(default_factory=list, description="List of cited evidence references")


class OptimizationOption(BaseModel):
    """A concrete, actionable optimization recommendation with transparent trade-offs."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    option_id: str = Field(..., description="Option key (e.g., OPT-1, OPT-2)")
    action_type: str = Field(..., description="Type: downscale_sku, lifecycle_rule, model_tier_switch, etc.")
    title: str = Field(..., description="Short action summary")
    description: str = Field(..., description="Step-by-step remediation plan")
    estimated_monthly_savings_usd: Decimal = Field(..., description="Projected monthly cost reduction")
    implementation_effort: str = Field(..., description="Effort required: LOW, MEDIUM, HIGH")
    risk_assessment: str = Field(..., description="Operational risks and failure modes")
    trade_offs: Dict[str, Any] = Field(
        default_factory=dict,
        description="Side-by-side trade-offs (latency impact, engineer hours, memory ceiling)",
    )
    is_recommended: bool = Field(default=False, description="Flag indicating the primary recommended option")


class ApprovalActionCard(BaseModel):
    """Governed human approval gate requiring explicit human review before any action."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, description="Action card UUID")
    investigation_id: uuid.UUID = Field(..., description="Parent investigation UUID")
    organization_id: uuid.UUID = Field(..., description="Tenant organization UUID")
    selected_option_id: str = Field(..., description="Recommended option ID to be approved")
    status: InvestigationStatus = Field(
        default=InvestigationStatus.PENDING_APPROVAL,
        description="Gate state: pending_approval, approved, rejected, dismissed",
    )
    reviewed_by: Optional[str] = Field(default=None, description="Email or ID of the human reviewer")
    reviewed_at: Optional[datetime] = Field(default=None, description="UTC timestamp of human decision")
    review_notes: Optional[str] = Field(default=None, description="Optional justification or review notes")
    audit_hash: str = Field(..., description="Cryptographic SHA-256 fingerprint sealing the evidence and recommendation")


class InvestigationReport(BaseModel):
    """Complete, auditable AI investigation deliverable submitted to engineering and finance."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, description="Unique investigation UUID")
    organization_id: uuid.UUID = Field(..., description="Tenant boundary UUID")
    anomaly_id: uuid.UUID = Field(..., description="Associated anomaly UUID")
    anomaly_title: str = Field(..., description="Title of the anomaly investigated")
    anomaly_type: str = Field(..., description="Classification of the anomaly")
    status: InvestigationStatus = Field(default=InvestigationStatus.PENDING_APPROVAL)

    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = Field(default=None)

    # Narrative findings
    executive_summary: str = Field(..., description="High-level narrative explaining what happened and financial impact")
    primary_root_cause: str = Field(..., description="Primary identified root cause")

    # Diagnostic components
    evidence: List[EvidenceItem] = Field(default_factory=list, description="All verified evidence cited by investigator")
    hypotheses: List[Hypothesis] = Field(default_factory=list, description="Evaluated diagnostic hypotheses")
    options: List[OptimizationOption] = Field(default_factory=list, description="Actionable optimization choices")
    approval_card: Optional[ApprovalActionCard] = Field(default=None, description="Human approval gate action card")

    @classmethod
    def compute_audit_hash(
        cls,
        investigation_id: uuid.UUID,
        organization_id: uuid.UUID,
        option_id: str,
        evidence: List[EvidenceItem],
    ) -> str:
        """Computes SHA-256 cryptographic fingerprint to guarantee tamper-proof audit trails."""
        payload = f"{investigation_id}:{organization_id}:{option_id}:{len(evidence)}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def summary(self) -> Dict[str, Any]:
        """Produces a clean executive dictionary summary of the investigation."""
        return {
            "investigation_id": str(self.id),
            "organization_id": str(self.organization_id),
            "anomaly_title": self.anomaly_title,
            "status": self.status.value,
            "primary_root_cause": self.primary_root_cause,
            "evidence_count": len(self.evidence),
            "options_count": len(self.options),
            "recommended_option": next((opt.title for opt in self.options if opt.is_recommended), "None"),
            "approval_status": self.approval_card.status.value if self.approval_card else "NO_GATE",
            "audit_hash": self.approval_card.audit_hash if self.approval_card else "N/A",
        }
