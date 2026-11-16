"""Comprehensive test suite for the Anomaly Detection Engine and Ground Truth Benchmark."""
import uuid
from datetime import date, timedelta
from decimal import Decimal
import pytest

from app.services.anomaly_detection import (
    AnomalyBenchmarkEvaluator,
    AnomalyDetectionEngine,
    AnomalySeverity,
    AnomalyStatus,
    AnomalyType,
    DetectedAnomaly,
)


def test_detect_compute_spike():
    """Engine detects sudden surge exceeding Z-score threshold and flags as COMPUTE_SPIKE."""
    org_id = uuid.uuid4()
    engine = AnomalyDetectionEngine(z_score_threshold=3.0, min_impact_usd=Decimal("20.00"))

    records = []
    base_date = date(2026, 8, 1)

    # 14 days of baseline ($15/day on EC2)
    for i in range(14):
        d = base_date + timedelta(days=i)
        records.append({
            "organization_id": org_id,
            "billing_date": d,
            "cloud_provider": "AWS",
            "service_id": "AmazonEC2",
            "resource_id": "i-worker-pipeline",
            "workload_id": "data-pipeline",
            "billing_amount": Decimal("15.00"),
        })

    # Day 15: Runaway spike to $250.00
    spike_date = base_date + timedelta(days=14)
    records.append({
        "organization_id": org_id,
        "billing_date": spike_date,
        "cloud_provider": "AWS",
        "service_id": "AmazonEC2",
        "resource_id": "i-worker-pipeline",
        "workload_id": "data-pipeline",
        "billing_amount": Decimal("250.00"),
    })

    summary = engine.detect_anomalies(org_id, records)

    assert summary.anomalies_detected_count >= 1
    spike = next(a for a in summary.anomalies if a.anomaly_type == AnomalyType.COMPUTE_SPIKE)
    assert spike.severity == AnomalySeverity.CRITICAL
    assert spike.detected_date == spike_date
    assert spike.actual_cost == Decimal("250.00")
    assert spike.z_score is not None and spike.z_score >= 3.0
    assert spike.root_cause_hint is not None


def test_detect_ai_token_surge():
    """Engine classifies Bedrock/LLM spikes as AI_TOKEN_SURGE."""
    org_id = uuid.uuid4()
    engine = AnomalyDetectionEngine(z_score_threshold=3.0, min_impact_usd=Decimal("25.00"))

    records = []
    base_date = date(2026, 9, 1)

    for i in range(14):
        records.append({
            "organization_id": org_id,
            "billing_date": base_date + timedelta(days=i),
            "cloud_provider": "AWS",
            "service_id": "AmazonBedrock",
            "resource_id": "anthropic.claude-3-5-sonnet",
            "workload_id": "model-inference",
            "billing_amount": Decimal("20.00"),
        })

    # Surge day: $350.00
    records.append({
        "organization_id": org_id,
        "billing_date": base_date + timedelta(days=14),
        "cloud_provider": "AWS",
        "service_id": "AmazonBedrock",
        "resource_id": "anthropic.claude-3-5-sonnet",
        "workload_id": "model-inference",
        "billing_amount": Decimal("350.00"),
    })

    summary = engine.detect_anomalies(org_id, records)

    ai_spike = next(a for a in summary.anomalies if a.anomaly_type == AnomalyType.AI_TOKEN_SURGE)
    assert ai_spike.service_id == "AmazonBedrock"
    assert ai_spike.severity == AnomalySeverity.CRITICAL


def test_detect_storage_leak_monotonic_accumulation():
    """Engine flags monotonic daily increase across >= 21 days as STORAGE_LEAK."""
    org_id = uuid.uuid4()
    engine = AnomalyDetectionEngine(storage_leak_min_days=21)

    records = []
    base_date = date(2026, 8, 1)

    # 30 days of continuously increasing storage cost (from $2.00 to $10.00/day)
    for i in range(30):
        records.append({
            "organization_id": org_id,
            "billing_date": base_date + timedelta(days=i),
            "cloud_provider": "AWS",
            "service_id": "AmazonS3",
            "resource_id": "arn:aws:s3:::telemetry-logs",
            "workload_id": "storage-lake",
            "billing_amount": Decimal(str(round(2.0 + (i * 0.28), 4))),
        })

    summary = engine.detect_anomalies(org_id, records)

    storage_anomaly = next(a for a in summary.anomalies if a.anomaly_type == AnomalyType.STORAGE_LEAK)
    assert storage_anomaly.service_id == "AmazonS3"
    assert storage_anomaly.severity == AnomalySeverity.HIGH
    assert storage_anomaly.evidence["days_monitored"] == 30


def test_detect_idle_zombie_database():
    """Engine identifies persistently flat, unvarying staging databases running 24/7."""
    org_id = uuid.uuid4()
    engine = AnomalyDetectionEngine()

    records = []
    base_date = date(2026, 7, 1)

    # 40 days of flat $12.48/day on orphaned staging RDS replica
    for i in range(40):
        records.append({
            "organization_id": org_id,
            "billing_date": base_date + timedelta(days=i),
            "cloud_provider": "AWS",
            "service_id": "AmazonRDS",
            "resource_id": "db-staging-replica-orphaned",
            "workload_id": "database-cluster",
            "billing_amount": Decimal("12.48"),
        })

    summary = engine.detect_anomalies(org_id, records)

    zombie = next(a for a in summary.anomalies if a.anomaly_type == AnomalyType.UNDERUTILIZED_RESOURCE)
    assert zombie.service_id == "AmazonRDS"
    assert zombie.actual_cost == Decimal("12.48") * Decimal("40")


def test_detect_credits_and_refunds():
    """Negative billing adjustments are captured as CREDIT_REFUND anomalies."""
    org_id = uuid.uuid4()
    engine = AnomalyDetectionEngine()

    records = [
        {
            "organization_id": org_id,
            "billing_date": date(2026, 8, 15),
            "cloud_provider": "AWS",
            "service_id": "AWS Account Billing",
            "resource_id": "credit-aws-startup-grant",
            "billing_amount": Decimal("-2500.00"),
            "is_credit": True,
        }
    ]

    summary = engine.detect_anomalies(org_id, records)

    credit = next(a for a in summary.anomalies if a.anomaly_type == AnomalyType.CREDIT_REFUND)
    assert credit.actual_cost == Decimal("-2500.00")
    assert credit.severity == AnomalySeverity.LOW


# =============================================================================
# Benchmark Evaluation Against Ground Truth (Slide 08)
# =============================================================================

def test_ground_truth_benchmark_evaluation():
    """Evaluates AnomalyDetectionEngine against 120-day synthetic dataset and ground-truth manifest."""
    evaluator = AnomalyBenchmarkEvaluator()
    report = evaluator.evaluate()

    # Verify that all 5 ground-truth scenarios exist and are tested
    assert report.total_ground_truth_scenarios == 5
    assert report.true_positives >= 4  # Must detect at least 4 out of 5 scenarios
    assert report.recall >= 0.80       # Recall >= 80%
    assert report.f1_score >= 0.20     # Demonstrates non-zero statistical F1 baseline

    summary = report.summary()
    assert summary["total_ground_truth_scenarios"] == 5
    assert summary["true_positives"] >= 4
    assert len(summary["scenarios"]) == 5
