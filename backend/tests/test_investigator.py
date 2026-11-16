"""Comprehensive unit tests for the Evidence-Led AI Investigator and Human Approval Gate (Slide 06)."""
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
import pytest

from app.services.anomaly_detection.models import AnomalySeverity, AnomalyType, DetectedAnomaly
from app.services.cost_attribution.models import TenantIsolationError
from app.services.investigator import (
    ApprovalActionCard,
    BoundedInvestigationTools,
    EvidenceLedInvestigator,
    InvestigationReport,
    InvestigationStatus,
)


# =============================================================================
# 1. Bounded Read-Only Tool Sandbox Tests
# =============================================================================

def test_bounded_tools_query_cost_ledger():
    """Bounded tool queries cost history scoped strictly to the target organization."""
    org_id = uuid.uuid4()
    records = [
        {
            "organization_id": org_id,
            "billing_date": date(2026, 8, 28),
            "service_id": "AmazonEC2",
            "resource_id": "i-worker-pipeline-runaway",
            "billing_amount": Decimal("554.88"),
            "resource_tags": {"Environment": "production"},
        },
        {
            "organization_id": org_id,
            "billing_date": date(2026, 8, 29),
            "service_id": "AmazonEC2",
            "resource_id": "i-worker-pipeline-runaway",
            "billing_amount": Decimal("489.60"),
            "resource_tags": {"Environment": "production"},
        },
    ]

    tools = BoundedInvestigationTools(cost_records=records)
    history = tools.query_cost_ledger(
        organization_id=org_id,
        service_id="AmazonEC2",
        resource_id="i-worker-pipeline-runaway",
    )

    assert len(history) == 2
    assert history[0]["billing_amount"] == 554.88
    assert history[1]["billing_amount"] == 489.60
    assert history[0]["tags"]["Environment"] == "production"


def test_bounded_tools_query_telemetry():
    """Bounded tool extracts token volume and latencies from operational telemetry."""
    org_id = uuid.uuid4()
    feat_id = uuid.uuid4()

    events = [
        {
            "organization_id": org_id,
            "product_feature_id": feat_id,
            "ai_model": "gpt-4o",
            "tokens": {"prompt_tokens": 1000, "completion_tokens": 500},
            "latency_ms": 150.0,
            "status": "success",
        },
        {
            "organization_id": org_id,
            "product_feature_id": feat_id,
            "ai_model": "gpt-4o",
            "tokens": {"prompt_tokens": 2000, "completion_tokens": 800},
            "latency_ms": 300.0,
            "status": "error",
        },
    ]

    tools = BoundedInvestigationTools(telemetry_events=events)
    metrics = tools.query_telemetry_metrics(organization_id=org_id, feature_id=feat_id)

    assert metrics["total_requests"] == 2
    assert metrics["prompt_tokens"] == 3000
    assert metrics["completion_tokens"] == 1300
    assert metrics["total_tokens"] == 4300
    assert metrics["error_count"] == 1
    assert metrics["error_rate_pct"] == 50.0
    assert metrics["avg_latency_ms"] == 225.0


def test_bounded_tools_inspect_metadata():
    """Bounded tool inspects resource tags and ownership metadata without write side-effects."""
    org_id = uuid.uuid4()
    records = [
        {
            "organization_id": org_id,
            "service_id": "AmazonS3",
            "resource_id": "arn:aws:s3:::raw-telemetry",
            "workload_id": "workload-storage",
            "resource_tags": {"Team": "data-infra", "Retention": "none"},
        }
    ]

    tools = BoundedInvestigationTools(cost_records=records)
    meta = tools.inspect_resource_metadata(org_id, "arn:aws:s3:::raw-telemetry")

    assert meta["found"] is not False
    assert meta["workload_id"] == "workload-storage"
    assert meta["tags"]["Team"] == "data-infra"


# =============================================================================
# 2. AI Investigator Diagnostic Workflow Tests (Compute, AI, Storage, Zombie)
# =============================================================================

def test_investigate_compute_spike_workflow():
    """Investigator reasons about COMPUTE_SPIKE, ranks hypotheses, and formulates options."""
    org_id = uuid.uuid4()
    anomaly = DetectedAnomaly(
        organization_id=org_id,
        anomaly_type=AnomalyType.COMPUTE_SPIKE,
        severity=AnomalySeverity.CRITICAL,
        title="Runaway Compute Spike",
        description="Daily cost surged on EC2",
        cloud_provider="AWS",
        service_id="AmazonEC2",
        resource_id="i-worker-pipeline-runaway",
        detected_date=date(2026, 8, 28),
        start_date=date(2026, 8, 28),
        actual_cost=Decimal("554.88"),
        expected_baseline_cost=Decimal("25.00"),
        cost_impact=Decimal("529.88"),
        z_score=15.2,
    )

    cost_records = [
        {
            "organization_id": org_id,
            "billing_date": date(2026, 8, 28),
            "service_id": "AmazonEC2",
            "resource_id": "i-worker-pipeline-runaway",
            "billing_amount": Decimal("554.88"),
            "resource_tags": {"Component": "etl-worker-pool"},
        }
    ]

    tools = BoundedInvestigationTools(cost_records=cost_records)
    investigator = EvidenceLedInvestigator(tools=tools)

    report = investigator.investigate(anomaly)

    assert report.organization_id == org_id
    assert report.status == InvestigationStatus.PENDING_APPROVAL
    assert "Autoscaling" in report.primary_root_cause or "queue" in report.primary_root_cause

    # Verified evidence
    assert len(report.evidence) >= 2
    assert any("CostRecord:AmazonEC2" in e.citation_ref for e in report.evidence)

    # Hypotheses
    assert len(report.hypotheses) >= 2
    primary_h = next(h for h in report.hypotheses if h.is_primary)
    assert primary_h.confidence_score >= 0.85

    # Optimization Options
    assert len(report.options) >= 2
    rec_opt = next(o for o in report.options if o.is_recommended)
    assert rec_opt.estimated_monthly_savings_usd > Decimal("0.00")
    assert "trade_offs" in rec_opt.model_dump()

    # Governed Approval Action Card
    assert report.approval_card is not None
    assert report.approval_card.status == InvestigationStatus.PENDING_APPROVAL
    assert len(report.approval_card.audit_hash) == 64  # SHA-256


def test_investigate_ai_token_surge():
    """Investigator identifies recursive prompt expansion and recommends prompt caching."""
    org_id = uuid.uuid4()
    anomaly = DetectedAnomaly(
        organization_id=org_id,
        anomaly_type=AnomalyType.AI_TOKEN_SURGE,
        severity=AnomalySeverity.CRITICAL,
        title="AI Copilot Surge",
        description="Token surge on Claude 3.5 Sonnet",
        cloud_provider="AWS",
        service_id="AmazonBedrock",
        resource_id="anthropic.claude-3-5-sonnet",
        detected_date=date(2026, 10, 1),
        start_date=date(2026, 10, 1),
        actual_cost=Decimal("350.00"),
        expected_baseline_cost=Decimal("20.00"),
        cost_impact=Decimal("330.00"),
    )

    investigator = EvidenceLedInvestigator()
    report = investigator.investigate(anomaly)

    assert "token" in report.primary_root_cause.lower() or "reasoning" in report.primary_root_cause.lower()
    rec_opt = next(o for o in report.options if o.is_recommended)
    assert "ceiling" in rec_opt.title.lower() or "cache" in rec_opt.title.lower()


def test_investigate_storage_leak():
    """Investigator identifies unexpired S3 objects and recommends lifecycle transition."""
    org_id = uuid.uuid4()
    anomaly = DetectedAnomaly(
        organization_id=org_id,
        anomaly_type=AnomalyType.STORAGE_LEAK,
        severity=AnomalySeverity.HIGH,
        title="Unbounded S3 Growth",
        description="Raw telemetry bucket growth",
        cloud_provider="AWS",
        service_id="AmazonS3",
        resource_id="arn:aws:s3:::raw-telemetry",
        detected_date=date(2026, 11, 14),
        start_date=date(2026, 8, 1),
        actual_cost=Decimal("234.50"),
        expected_baseline_cost=Decimal("12.00"),
        cost_impact=Decimal("222.50"),
    )

    investigator = EvidenceLedInvestigator()
    report = investigator.investigate(anomaly)

    assert "lifecycle" in report.primary_root_cause.lower() or "unmanaged" in report.primary_root_cause.lower()
    rec_opt = next(o for o in report.options if o.is_recommended)
    assert "glacier" in rec_opt.description.lower() or "expire" in rec_opt.description.lower()


def test_investigate_idle_zombie():
    """Investigator identifies orphaned RDS replica and recommends snapshot & termination."""
    org_id = uuid.uuid4()
    anomaly = DetectedAnomaly(
        organization_id=org_id,
        anomaly_type=AnomalyType.UNDERUTILIZED_RESOURCE,
        severity=AnomalySeverity.MEDIUM,
        title="Orphaned Staging Replica",
        description="Staging DB running 24/7 with zero traffic",
        cloud_provider="AWS",
        service_id="AmazonRDS",
        resource_id="db-staging-replica",
        detected_date=date(2026, 11, 14),
        start_date=date(2026, 7, 18),
        actual_cost=Decimal("1497.60"),
        expected_baseline_cost=Decimal("0.00"),
        cost_impact=Decimal("1497.60"),
    )

    investigator = EvidenceLedInvestigator()
    report = investigator.investigate(anomaly)

    assert "idle" in report.primary_root_cause.lower() or "replica" in report.primary_root_cause.lower()
    rec_opt = next(o for o in report.options if o.is_recommended)
    assert "terminate" in rec_opt.title.lower() or "delete" in rec_opt.description.lower()


# =============================================================================
# 3. Governed Human Approval Gate Lifecycle & Audit Hash Tests
# =============================================================================

def test_human_approval_gate_lifecycle_approve():
    """Human engineer approves recommended action, sealing audit log and reviewer identity."""
    org_id = uuid.uuid4()
    anomaly = DetectedAnomaly(
        organization_id=org_id,
        anomaly_type=AnomalyType.COMPUTE_SPIKE,
        severity=AnomalySeverity.HIGH,
        title="Worker Spike",
        description="Spike on worker node",
        cloud_provider="AWS",
        service_id="AmazonEC2",
        detected_date=date(2026, 8, 28),
        start_date=date(2026, 8, 28),
        actual_cost=Decimal("200.00"),
        expected_baseline_cost=Decimal("20.00"),
        cost_impact=Decimal("180.00"),
    )

    investigator = EvidenceLedInvestigator()
    report = investigator.investigate(anomaly)

    # Initial state
    assert report.status == InvestigationStatus.PENDING_APPROVAL
    assert report.approval_card.status == InvestigationStatus.PENDING_APPROVAL

    # Human reviews and approves
    reviewer = "lead-devops@marginops.io"
    notes = "Verified DLQ implementation; proceeding with rollout."
    card = investigator.approve_action(report, reviewer_email=reviewer, review_notes=notes)

    assert card.status == InvestigationStatus.APPROVED
    assert card.reviewed_by == reviewer
    assert card.reviewed_at is not None
    assert card.review_notes == notes
    assert report.status == InvestigationStatus.APPROVED


def test_human_approval_gate_lifecycle_reject_and_dismiss():
    """Human engineer rejects or dismisses recommended action."""
    org_id = uuid.uuid4()
    anomaly = DetectedAnomaly(
        organization_id=org_id,
        anomaly_type=AnomalyType.COMPUTE_SPIKE,
        severity=AnomalySeverity.HIGH,
        title="Worker Spike",
        description="Spike on worker node",
        cloud_provider="AWS",
        service_id="AmazonEC2",
        detected_date=date(2026, 8, 28),
        start_date=date(2026, 8, 28),
        actual_cost=Decimal("200.00"),
        expected_baseline_cost=Decimal("20.00"),
        cost_impact=Decimal("180.00"),
    )

    investigator = EvidenceLedInvestigator()

    # Test Rejection
    report1 = investigator.investigate(anomaly)
    card_rejected = investigator.reject_action(report1, "eng@company.com", "Planned benchmark stress test.")
    assert card_rejected.status == InvestigationStatus.REJECTED
    assert report1.status == InvestigationStatus.REJECTED

    # Test Dismissal
    report2 = investigator.investigate(anomaly)
    card_dismissed = investigator.dismiss_action(report2, "finops@company.com", "Known budget exception.")
    assert card_dismissed.status == InvestigationStatus.DISMISSED
    assert report2.status == InvestigationStatus.DISMISSED


def test_audit_hash_integrity():
    """Audit hash uniquely and immutably identifies the evidence and recommendation payload."""
    inv_id = uuid.uuid4()
    org_id = uuid.uuid4()
    h1 = InvestigationReport.compute_audit_hash(inv_id, org_id, "OPT-1", [])
    h2 = InvestigationReport.compute_audit_hash(inv_id, org_id, "OPT-1", [])
    h3 = InvestigationReport.compute_audit_hash(inv_id, org_id, "OPT-2", [])

    assert h1 == h2
    assert h1 != h3
    assert len(h1) == 64
