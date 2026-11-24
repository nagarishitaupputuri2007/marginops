"""Integration tests for MarginOps FastAPI REST API endpoints."""
import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.platform_state import PlatformStateService


@pytest.fixture(scope="module")
def client():
    """Provides a synchronous test client for FastAPI endpoints."""
    with TestClient(app) as c:
        yield c


def test_costs_summary_endpoint(client):
    """Verifies /api/v1/costs/summary returns valid KPI metrics and reconciliation guarantees."""
    res = client.get("/api/v1/costs/summary")
    assert res.status_code == 200
    data = res.json()

    assert "total_net_spend" in data
    assert data["total_net_spend"] > 0
    assert "mtd_spend" in data
    assert "burn_rate_percent" in data
    assert "active_anomalies_count" in data
    assert "providers_breakdown" in data
    assert len(data["providers_breakdown"]) >= 3
    assert data["is_reconciled"] is True
    assert data["reconciliation_delta"] == "0.0000"


def test_costs_explorer_pagination_and_filtering(client):
    """Verifies /api/v1/costs/explorer supports pagination and query filtering."""
    # 1. Unfiltered page 1
    res = client.get("/api/v1/costs/explorer?page=1&limit=25")
    assert res.status_code == 200
    data = res.json()

    assert data["total_items"] > 1000
    assert data["page"] == 1
    assert data["limit"] == 25
    assert len(data["items"]) == 25
    assert len(data["daily_time_series"]) > 0

    # 2. Filter by provider
    aws_res = client.get("/api/v1/costs/explorer?provider=AWS&limit=10")
    assert aws_res.status_code == 200
    aws_data = aws_res.json()
    assert all("AWS" in item["cloud_provider"] for item in aws_data["items"])


def test_cost_attribution_endpoint(client):
    """Verifies /api/v1/costs/attribution guarantees Largest Remainder zero-penny leakage."""
    res = client.get("/api/v1/costs/attribution")
    assert res.status_code == 200
    data = res.json()

    assert data["is_reconciled"] is True
    assert data["reconciliation_delta"] == "0.0000"
    assert data["total_source_amount"] > 0
    assert data["total_allocated_amount"] > 0
    assert data["algorithm"] == "Hare-Niemeyer Largest Remainder Method"
    assert len(data["by_feature"]) >= 3


def test_unit_economics_report_endpoint(client):
    """Verifies /api/v1/unit-economics/report fuses financial COGS with telemetry metrics."""
    res = client.get("/api/v1/unit-economics/report")
    assert res.status_code == 200
    data = res.json()

    assert "organization_id" in data
    assert "overall_gross_margin_percent" in data
    assert "total_attributed_cost" in data
    assert "metrics" in data
    assert "margins" in data
    assert len(data["margins"]) >= 4

    # Verify margin statuses include expected classifications
    statuses = [m["status"] for m in data["margins"]]
    assert "HEALTHY" in statuses
    assert "CRITICAL" in statuses


def test_anomalies_active_endpoint(client):
    """Verifies /api/v1/anomalies returns multi-cloud detected anomalies."""
    res = client.get("/api/v1/anomalies")
    assert res.status_code == 200
    data = res.json()

    assert "anomalies" in data
    assert len(data["anomalies"]) > 0
    assert "by_severity" in data
    assert "total_cost_impact" in data

    first = data["anomalies"][0]
    assert "anomaly_type" in first
    assert "severity" in first
    assert "cost_impact" in first


def test_anomalies_benchmark_evaluation_endpoint(client):
    """Verifies /api/v1/anomalies/benchmark achieves 80%+ recall on Slide 08 ground-truth."""
    res = client.get("/api/v1/anomalies/benchmark")
    assert res.status_code == 200
    data = res.json()

    assert data["total_ground_truth_scenarios"] == 5
    assert data["true_positives"] >= 4
    assert data["recall"] >= 0.80
    assert data["f1_score"] > 0.5
    assert len(data["scenario_results"]) == 5


def test_spend_forecasting_endpoint(client):
    """Verifies /api/v1/forecasting/spend returns Holt's linear trend with confidence bounds."""
    res = client.get("/api/v1/forecasting/spend?days=30")
    assert res.status_code == 200
    data = res.json()

    assert data["forecast_days"] == 30
    assert "projected_total_spend" in data
    assert "daily_burn_rate" in data
    assert len(data["forecast_points"]) == 30

    pt = data["forecast_points"][0]
    assert "predicted_amount" in pt
    assert "lower_bound_80" in pt
    assert "upper_bound_80" in pt
    assert "lower_bound_95" in pt
    assert "upper_bound_95" in pt
    assert float(pt["lower_bound_95"]) <= float(pt["lower_bound_80"])
    assert float(pt["upper_bound_80"]) <= float(pt["upper_bound_95"])


def test_investigations_lifecycle_and_governed_gate(client):
    """Verifies the complete AI Investigator lifecycle and Governed Human Approval Gate (Slide 06)."""
    # 1. List investigations
    res = client.get("/api/v1/investigations")
    assert res.status_code == 200
    investigations = res.json()
    assert len(investigations) > 0

    first_inv = investigations[0]
    inv_id = first_inv["id"]

    # 2. Get specific investigation by UUID
    detail_res = client.get(f"/api/v1/investigations/{inv_id}")
    assert detail_res.status_code == 200
    report = detail_res.json()
    assert report["id"] == inv_id
    assert len(report["evidence"]) > 0
    assert len(report["options"]) > 0
    assert report["approval_card"] is not None

    # 3. Governed Human Approval Gate: Approve recommendation
    approve_res = client.post(
        f"/api/v1/investigations/{inv_id}/approve",
        json={
            "reviewer_email": "finops-director@acme.com",
            "notes": "Approved for staging deployment per Q3 cost policy",
        },
    )
    assert approve_res.status_code == 200
    card = approve_res.json()
    assert card["status"] == "approved"
    assert card["reviewed_by"] == "finops-director@acme.com"
    assert card["review_notes"] == "Approved for staging deployment per Q3 cost policy"
    assert len(card["audit_hash"]) == 64  # Valid SHA-256 length

    # 4. Reject recommendation
    reject_res = client.post(
        f"/api/v1/investigations/{inv_id}/reject",
        json={
            "reviewer_email": "cto@acme.com",
            "notes": "Cannot downscale: compute quota needed for marketing campaign",
        },
    )
    assert reject_res.status_code == 200
    rejected_card = reject_res.json()
    assert rejected_card["status"] == "rejected"
    assert rejected_card["reviewed_by"] == "cto@acme.com"


def test_investigation_not_found(client):
    """Verifies 404 is returned when querying an invalid investigation UUID."""
    fake_id = str(uuid.uuid4())
    res = client.get(f"/api/v1/investigations/{fake_id}")
    assert res.status_code == 404


def test_costs_upload_and_reconciliation(client):
    """Verifies /api/v1/costs/upload accepts CSV billing uploads and recalculates state."""
    csv_content = (
        "billing_date,cloud_provider,account_id,service_id,service_name,resource_id,"
        "usage_type,usage_quantity,unit_of_measurement,currency,cost,billing_amount,workload_id,product_feature_id,resource_tags\n"
        "2026-11-20,AWS,aws-acct-test,AmazonEC2,Amazon Elastic Compute Cloud,i-custom-test-01,"
        "BoxUsage:m6i.large,24.0,Hours,USD,2.3040,2.3040,workload-custom,feat-cost-intelligence,\"{}\"\n"
        "2026-11-20,AWS,aws-acct-test,AWSBilling,AWS Billing,credit-test-grant,"
        "Credit:Promotional,1.0,Units,USD,-50.0000,-50.0000,workload-custom,feat-cost-intelligence,\"{}\"\n"
    )

    files = {"file": ("custom_billing.csv", csv_content.encode("utf-8"), "text/csv")}
    res = client.post("/api/v1/costs/upload", files=files)
    assert res.status_code == 200
    data = res.json()

    assert data["status"] == "PROCESSED_AND_RECONCILED"
    assert data["filename"] == "custom_billing.csv"
    assert data["valid_rows"] == 2
    assert data["positive_charges"] == 2.304
    assert data["credits"] == -50.0
    assert data["is_reconciled"] is True
    assert data["reconciliation_delta"] == "0.0000"


def test_costs_export_endpoint(client):
    """Verifies /api/v1/costs/export produces financial reconciliation certificates."""
    # 1. JSON export
    res_json = client.get("/api/v1/costs/export?format=json")
    assert res_json.status_code == 200
    data = res_json.json()
    assert data["reconciliation_status"] == "CERTIFIED_RECONCILED"
    assert data["reconciliation_delta"] == "0.0000"
    assert "feature_attribution" in data

    # 2. CSV export
    res_csv = client.get("/api/v1/costs/export?format=csv")
    assert res_csv.status_code == 200
    assert "text/csv" in res_csv.headers["content-type"]
    assert "attachment; filename=marginops_reconciliation_audit.csv" in res_csv.headers["content-disposition"]
    assert "Billing Date,Cloud Provider,Service Name" in res_csv.text
