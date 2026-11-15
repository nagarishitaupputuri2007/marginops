"""Unit tests for MarginOps Synthetic Cloud Billing Data Generator."""
import csv
from datetime import date, timedelta
from decimal import Decimal
import json
from pathlib import Path
import pytest

from app.services.synthetic_billing import (
    BillingRecord,
    DatasetManifest,
    GenerationConfig,
    ScenarioGroundTruth,
    SyntheticBillingGenerator,
)


@pytest.fixture
def default_generator():
    """Returns a generator instance with default seed 42 and 120 days."""
    config = GenerationConfig(start_date=date(2026, 7, 18), days=120, seed=42)
    return SyntheticBillingGenerator(config=config)


# ==============================================================================
# 1. Reproducibility Tests
# ==============================================================================

def test_deterministic_reproducibility():
    """Identical seeds must produce the exact same records and financial totals."""
    config_a = GenerationConfig(start_date=date(2026, 7, 18), days=120, seed=42)
    config_b = GenerationConfig(start_date=date(2026, 7, 18), days=120, seed=42)

    gen_a = SyntheticBillingGenerator(config=config_a)
    gen_b = SyntheticBillingGenerator(config=config_b)

    records_a, manifest_a = gen_a.generate()
    records_b, manifest_b = gen_b.generate()

    assert len(records_a) == len(records_b)
    assert manifest_a.total_gross_cost == manifest_b.total_gross_cost
    assert manifest_a.total_credits == manifest_b.total_credits
    assert manifest_a.total_net_cost == manifest_b.total_net_cost

    # Verify first and last records match exactly
    assert records_a[0].model_dump() == records_b[0].model_dump()
    assert records_a[-1].model_dump() == records_b[-1].model_dump()


def test_different_seeds_produce_different_distributions():
    """Different seeds should generate differing daily noise and totals."""
    gen_42 = SyntheticBillingGenerator(config=GenerationConfig(seed=42))
    gen_99 = SyntheticBillingGenerator(config=GenerationConfig(seed=99))

    _, manifest_42 = gen_42.generate()
    _, manifest_99 = gen_99.generate()

    assert manifest_42.total_gross_cost != manifest_99.total_gross_cost


# ==============================================================================
# 2. Date Coverage and Ordering Tests
# ==============================================================================

def test_date_coverage_and_order(default_generator):
    """Verifies that billing records cover exactly 120 distinct consecutive days."""
    records, manifest = default_generator.generate()

    assert manifest.days_covered == 120
    assert manifest.start_date == "2026-07-18"
    assert manifest.end_date == "2026-11-14"

    dates = [r.billing_date for r in records]
    unique_dates = sorted(list(set(dates)))
    assert len(unique_dates) == 120
    assert unique_dates[0] == "2026-07-18"
    assert unique_dates[-1] == "2026-11-14"

    # Verify chronological ordering
    for i in range(len(records) - 1):
        assert records[i].billing_date <= records[i + 1].billing_date


# ==============================================================================
# 3. Required Fields & Schema Integrity Tests
# ==============================================================================

def test_required_fields_and_types(default_generator):
    """Every record must contain all required fields and valid JSON tags."""
    records, _ = default_generator.generate()

    for r in records:
        assert r.billing_date
        assert r.cloud_provider in {"AWS", "GCP", "Azure"}
        assert r.account_id
        assert r.service_id
        assert r.service_name
        assert r.resource_id
        assert r.usage_type
        assert isinstance(r.usage_quantity, Decimal)
        assert r.unit_of_measurement
        assert r.currency == "USD"
        assert isinstance(r.cost, Decimal)
        assert isinstance(r.billing_amount, Decimal)
        assert r.cost == r.billing_amount
        assert r.workload_id.startswith("workload-")
        assert r.product_feature_id.startswith("feat-")

        # Tags must be valid JSON
        tags = json.loads(r.resource_tags)
        assert isinstance(tags, dict)
        assert len(tags) > 0


# ==============================================================================
# 4. Negative Credits & Refunds Tests
# ==============================================================================

def test_credits_and_refunds(default_generator):
    """Verifies negative billing amounts for promotional credits and refunds."""
    records, manifest = default_generator.generate()

    credit_records = [r for r in records if r.cost < 0]
    assert len(credit_records) == 3

    total_credit_sum = sum(r.cost for r in credit_records)
    assert total_credit_sum == Decimal("-4200.0000")
    assert manifest.total_credits == Decimal("-4200.00")

    # Check credit types
    credit_types = {r.usage_type for r in credit_records}
    assert "Credit:PromotionalDiscount" in credit_types
    assert "Refund:ServiceLevelAgreement" in credit_types
    assert "Credit:CommitmentRebate" in credit_types


# ==============================================================================
# 5. Ground Truth Scenarios & No Leakage Tests
# ==============================================================================

def test_ground_truth_scenarios_exist(default_generator):
    """Manifest must include all 5 required ground truth scenarios."""
    _, manifest = default_generator.generate()

    scenario_types = {s.scenario_type for s in manifest.scenarios}
    expected_types = {
        "compute_spike",
        "storage_leak",
        "ai_token_surge",
        "underutilized_resource",
        "credit_refund",
    }
    assert scenario_types == expected_types
    assert len(manifest.scenarios) == 5

    # Check specific scenario metrics
    sc_map = {s.scenario_type: s for s in manifest.scenarios}
    assert sc_map["compute_spike"].expected_cost_impact > Decimal("2000.00")
    assert sc_map["storage_leak"].expected_cost_impact > Decimal("200.00")
    assert sc_map["ai_token_surge"].expected_cost_impact > Decimal("2500.00")
    assert sc_map["underutilized_resource"].expected_cost_impact > Decimal("1400.00")
    assert sc_map["credit_refund"].expected_cost_impact == Decimal("-4200.00")


def test_no_ground_truth_leakage_in_billing_records(default_generator):
    """Raw billing records must NOT contain ground-truth or anomaly labels."""
    records, _ = default_generator.generate()

    forbidden_keywords = ["anomaly", "ground_truth", "is_anomaly", "spike", "zombie", "leak"]

    for r in records:
        # Check resource_id, usage_type, workload_id, and tags
        assert "is_anomaly" not in r.resource_tags.lower()
        assert "ground_truth" not in r.resource_tags.lower()
        assert "anomaly" not in r.usage_type.lower()


# ==============================================================================
# 6. Financial Calculations & Manifest Precision Tests
# ==============================================================================

def test_financial_calculations_precision(default_generator):
    """Gross cost, credits, and net cost must balance with exact Decimal precision."""
    records, manifest = default_generator.generate()

    calculated_gross = sum(r.cost for r in records if r.cost > 0).quantize(Decimal("0.01"))
    calculated_credits = sum(r.cost for r in records if r.cost < 0).quantize(Decimal("0.01"))
    calculated_net = calculated_gross + calculated_credits

    assert manifest.total_gross_cost == calculated_gross
    assert manifest.total_credits == calculated_credits
    assert manifest.total_net_cost == calculated_net
    assert manifest.total_net_cost > Decimal("0.00")


# ==============================================================================
# 7. File Export Tests
# ==============================================================================

def test_file_export_and_parsing(tmp_path, default_generator):
    """Tests writing and reading generated CSV dataset and JSON manifest."""
    csv_file = tmp_path / "test_billing.csv"
    json_file = tmp_path / "test_manifest.json"

    manifest = default_generator.generate_and_save(str(csv_file), str(json_file))

    # Verify CSV file
    assert csv_file.exists()
    with open(csv_file, "r", encoding="utf-8") as f:
        reader = list(csv.reader(f))
        header = reader[0]
        rows = reader[1:]

    assert header == BillingRecord.csv_header()
    assert len(rows) == manifest.total_records

    # Verify JSON manifest file
    assert json_file.exists()
    with open(json_file, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    reconstructed_manifest = DatasetManifest.model_validate(manifest_data)
    assert reconstructed_manifest.total_records == manifest.total_records
    assert len(reconstructed_manifest.scenarios) == 5
