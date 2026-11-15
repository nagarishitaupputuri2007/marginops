"""Unit tests for MarginOps Cloud Billing Ingestion and Validation Service."""
from decimal import Decimal
from pathlib import Path
import pytest

from app.services.billing_ingestion import (
    BillingIngestionService,
    IngestionReport,
    ParsedBillingRecord,
    RowValidationError,
    NormalizedBillingParser,
    BaseBillingParser,
)


@pytest.fixture
def service():
    """Returns an initialized BillingIngestionService."""
    return BillingIngestionService()


@pytest.fixture
def synthetic_csv_path():
    """Path to the generated 120-day synthetic benchmark CSV."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    return repo_root / "data" / "synthetic" / "cloud_billing_120d.csv"


# ==============================================================================
# 1. Full Dataset Ingestion Tests
# ==============================================================================

def test_ingest_synthetic_120d_dataset(service, synthetic_csv_path):
    """Ingests the full 120-day benchmark CSV and verifies totals, line count, and zero errors."""
    assert synthetic_csv_path.exists(), f"Synthetic dataset not found at {synthetic_csv_path}"

    report = service.ingest_file(synthetic_csv_path)

    # Clean ingestion checks
    assert report.is_clean is True
    assert report.invalid_rows == 0
    assert len(report.errors) == 0
    assert report.valid_rows == 1803
    assert report.total_rows == 1803
    assert report.success_rate == 100.0

    # Financial balance checks: unrounded sums match full 4-decimal precision, and quantized matches manifest
    assert report.total_positive_charges.quantize(Decimal("0.01")) == Decimal("17295.41")
    assert report.total_credits.quantize(Decimal("0.01")) == Decimal("-4200.00")
    assert report.net_billing_amount.quantize(Decimal("0.01")) == Decimal("13095.41")
    assert report.net_billing_amount == report.total_positive_charges + report.total_credits

    # Record validation
    assert len(report.records) == 1803
    first_record = report.records[0]
    assert isinstance(first_record, ParsedBillingRecord)
    assert first_record.cloud_provider == "AWS"
    assert isinstance(first_record.cost, Decimal)
    assert isinstance(first_record.billing_amount, Decimal)


# ==============================================================================
# 2. Negative Credits and Refunds Tests
# ==============================================================================

def test_ingest_credits_and_refunds(service, synthetic_csv_path):
    """Verifies that credits and refunds are properly detected and flagged."""
    report = service.ingest_file(synthetic_csv_path)

    credits = [r for r in report.records if r.is_credit]
    assert len(credits) == 3

    credit_amounts = [c.billing_amount for c in credits]
    assert Decimal("-2500.0000") in credit_amounts
    assert Decimal("-450.0000") in credit_amounts
    assert Decimal("-1250.0000") in credit_amounts

    total_credits = sum(credit_amounts)
    assert total_credits == Decimal("-4200.0000")


# ==============================================================================
# 3. Malformed and Mixed-Validity File Tests
# ==============================================================================

def test_mixed_validity_csv_graceful_handling(service):
    """A file with mixed valid and invalid rows must parse valid items without stopping."""
    csv_content = """billing_date,cloud_provider,account_id,service_id,service_name,resource_id,usage_type,usage_quantity,unit_of_measurement,currency,cost,billing_amount,workload_id,product_feature_id,resource_tags
2026-08-01,AWS,aws-123,AmazonEC2,Amazon Elastic Compute Cloud,i-01,BoxUsage:m6i,24.0,Hours,USD,10.00,10.00,workload-api,feat-ci,"{""env"": ""prod""}"
2026-99-99,AWS,aws-123,AmazonEC2,Amazon Elastic Compute Cloud,i-02,BoxUsage:m6i,24.0,Hours,USD,10.00,10.00,workload-api,feat-ci,"{}"
2026-08-02,GCP,gcp-456,GoogleComputeEngine,Compute Engine,vm-01,N2-Core,24.0,Hours,USD,20.00,20.00,workload-data,feat-um,"{}"
2026-08-03,AWS,aws-123,AmazonEC2,Amazon Elastic Compute Cloud,,BoxUsage:m6i,24.0,Hours,USD,10.00,10.00,workload-api,feat-ci,"{}"
2026-08-04,UNKNOWN_CLOUD,sub-789,SomeService,Some Service,res-01,Usage,1.0,Units,USD,5.00,5.00,workload-api,feat-ci,"{}"
2026-08-05,AWS,aws-123,AmazonEC2,Amazon Elastic Compute Cloud,i-03,BoxUsage:m6i,not_a_number,Hours,USD,10.00,10.00,workload-api,feat-ci,"{}"
2026-08-06,AWS,aws-123,AmazonEC2,Amazon Elastic Compute Cloud,i-04,BoxUsage:m6i,24.0,Hours,USD,free,10.00,workload-api,feat-ci,"{}"
2026-08-07,AWS,aws-123,AmazonEC2,Amazon Elastic Compute Cloud,i-05,BoxUsage:m6i,24.0,Hours,USD_DOLLARS,10.00,10.00,workload-api,feat-ci,"{}"
2026-08-08,AWS,aws-123,AmazonEC2,Amazon Elastic Compute Cloud,i-06,BoxUsage:m6i,24.0,Hours,USD,10.00,10.00,workload-api,feat-ci,"{bad_json"
2026-08-09,Azure,sub-789,AzureBilling,Azure Billing,rebate-01,Credit:Rebate,1.0,Adjustment,USD,-5.00,-5.00,workload-fin,feat-ci,"{}"
"""
    report = service.ingest_string(csv_content)

    assert report.total_rows == 10
    assert report.valid_rows == 3  # Lines 2, 4, 11
    assert report.invalid_rows == 7  # Lines 3, 5, 6, 7, 8, 9, 10
    assert len(report.errors) == 7

    # Verify Financial Totals on valid rows: $10.00 (AWS) + $20.00 (GCP) = $30.00; Credit: -$5.00 (Azure)
    assert report.total_positive_charges == Decimal("30.0000")
    assert report.total_credits == Decimal("-5.0000")
    assert report.net_billing_amount == Decimal("25.0000")

    # Verify specific error reporting line numbers
    error_lines = [e.row_number for e in report.errors]
    assert 3 in error_lines  # Malformed date line
    assert 5 in error_lines  # Missing resource_id line
    assert 6 in error_lines  # Unsupported cloud provider
    assert 7 in error_lines  # Non-numeric quantity
    assert 8 in error_lines  # Non-numeric cost
    assert 9 in error_lines  # Invalid currency
    assert 10 in error_lines  # Malformed JSON tags


# ==============================================================================
# 4. Header and Column Count Validation Tests
# ==============================================================================

def test_missing_header_columns_explicit_parser(service):
    """When explicit normalized parser is invoked, reports missing required columns."""
    csv_missing_columns = """billing_date,cloud_provider,account_id,resource_id,cost,billing_amount
2026-08-01,AWS,aws-123,i-01,10.00,10.00
"""
    report = service.ingest_string(csv_missing_columns, parser_name="normalized_csv")

    assert report.total_rows == 0
    assert report.valid_rows == 0
    assert len(report.errors) == 1
    assert "missing required columns" in report.errors[0].error


def test_missing_header_columns_autodetect_failure(service):
    """When header is unrecognized and parser not specified, reports auto-detection failure."""
    csv_unrecognized = """foo,bar,baz
1,2,3
"""
    report = service.ingest_string(csv_unrecognized)

    assert report.total_rows == 0
    assert report.valid_rows == 0
    assert len(report.errors) == 1
    assert "Unable to auto-detect" in report.errors[0].error


def test_empty_string_input(service):
    """Empty CSV string produces an error report without unhandled exceptions."""
    report = service.ingest_string("")
    assert report.total_rows == 0
    assert report.valid_rows == 0
    assert len(report.errors) == 1
    assert "Empty" in report.errors[0].error


# ==============================================================================
# 5. Cloud Provider Canonical Normalization Tests
# ==============================================================================

def test_provider_name_canonical_normalization(service):
    """Tests case-insensitive normalization of provider names."""
    csv_content = """billing_date,cloud_provider,account_id,service_id,service_name,resource_id,usage_type,usage_quantity,unit_of_measurement,currency,cost,billing_amount,workload_id,product_feature_id,resource_tags
2026-08-01,amazon web services,aws-1,AmazonEC2,EC2,i-01,BoxUsage,1.0,Hours,USD,1.00,1.00,workload-1,feat-1,"{}"
2026-08-01,google cloud platform,gcp-1,ComputeEngine,GCE,vm-01,N2,1.0,Hours,USD,2.00,2.00,workload-1,feat-1,"{}"
2026-08-01,microsoft azure,az-1,VirtualMachines,VM,az-01,D2s,1.0,Hours,USD,3.00,3.00,workload-1,feat-1,"{}"
"""
    report = service.ingest_string(csv_content)

    assert report.valid_rows == 3
    assert report.invalid_rows == 0

    providers = [r.cloud_provider for r in report.records]
    assert providers == ["AWS", "GCP", "Azure"]


# ==============================================================================
# 6. Modular Parser Dispatch & Extension Tests
# ==============================================================================

def test_custom_parser_registration(service):
    """Confirms custom parsers can be registered and dispatched."""

    class MockCustomParser(BaseBillingParser):
        @property
        def parser_name(self) -> str:
            return "custom_mock"

        def can_parse(self, header_row):
            return "custom_marker" in [c.lower() for c in header_row]

        def parse(self, stream):
            r = IngestionReport()
            r.total_rows = 1
            r.valid_rows = 1
            r.net_billing_amount = Decimal("99.9900")
            return r

    service.register_parser(MockCustomParser())
    assert service.get_parser("custom_mock") is not None

    custom_csv = "custom_marker,value\nfoo,bar\n"
    report = service.ingest_string(custom_csv)
    assert report.valid_rows == 1
    assert report.net_billing_amount == Decimal("99.9900")
