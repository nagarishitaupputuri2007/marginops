"""Comprehensive test suite for the Product Unit Economics & Telemetry Fusion Engine."""
import uuid
from datetime import datetime, timezone
from decimal import Decimal
import pytest

from app.models.enums import UnitMetricType
from app.schemas.telemetry import TelemetryEvent, TelemetryEventType, TelemetryStatus, TokenUsage
from app.services.cost_attribution.models import TenantIsolationError
from app.services.unit_economics import (
    FeatureGrossMargin,
    MarginHealthStatus,
    TelemetryAggregate,
    UnitCostCalculation,
    UnitCostStatus,
    UnitEconomicsEngine,
    UnitEconomicsReport,
)


# =============================================================================
# 1. Telemetry Aggregation & Operational Metrics Tests
# =============================================================================

def test_aggregate_telemetry_events_grouping_and_metrics():
    """Telemetry events are accurately aggregated by feature with latencies and token counts."""
    org_id = uuid.uuid4()
    feat_id = uuid.uuid4()
    engine = UnitEconomicsEngine()

    events = [
        TelemetryEvent(
            organization_id=org_id,
            product_feature_id=feat_id,
            event_type=TelemetryEventType.LLM_INFERENCE,
            ai_model="gpt-4o",
            tokens=TokenUsage(prompt_tokens=500, completion_tokens=200),
            latency_ms=120.0,
            status=TelemetryStatus.SUCCESS,
            attributes={"customer_id": "cust-1"},
        ),
        TelemetryEvent(
            organization_id=org_id,
            product_feature_id=feat_id,
            event_type=TelemetryEventType.LLM_INFERENCE,
            ai_model="gpt-4o",
            tokens=TokenUsage(prompt_tokens=1000, completion_tokens=400),
            latency_ms=250.0,
            status=TelemetryStatus.SUCCESS,
            attributes={"customer_id": "cust-2"},
        ),
        TelemetryEvent(
            organization_id=org_id,
            product_feature_id=feat_id,
            event_type=TelemetryEventType.LLM_INFERENCE,
            ai_model="claude-3-5-sonnet",
            tokens=TokenUsage(prompt_tokens=300, completion_tokens=100),
            latency_ms=500.0,
            status=TelemetryStatus.ERROR,
            attributes={"customer_id": "cust-1"},
        ),
    ]

    aggregates = engine.aggregate_telemetry_events(org_id, events)

    assert feat_id in aggregates
    agg = aggregates[feat_id]
    assert agg.request_count == 3
    assert agg.success_count == 2
    assert agg.error_count == 1
    assert agg.prompt_tokens == 1800
    assert agg.completion_tokens == 700
    assert agg.total_tokens == 2500
    assert agg.active_tenants_count == 2  # cust-1, cust-2
    assert agg.avg_latency_ms == pytest.approx(290.0, rel=1e-2)
    assert agg.p95_latency_ms is not None
    assert "gpt-4o" in agg.by_model
    assert agg.by_model["gpt-4o"]["requests"] == 2
    assert agg.by_model["gpt-4o"]["total_tokens"] == 2100
    assert "claude-3-5-sonnet" in agg.by_model


def test_telemetry_aggregation_tenant_isolation():
    """Aggregating telemetry containing events from a foreign tenant raises TenantIsolationError."""
    org_a = uuid.uuid4()
    org_b = uuid.uuid4()
    engine = UnitEconomicsEngine(strict_tenant_isolation=True)

    events = [
        TelemetryEvent(
            organization_id=org_a,
            event_type=TelemetryEventType.API_REQUEST,
            status=TelemetryStatus.SUCCESS,
        ),
        TelemetryEvent(
            organization_id=org_b,  # Foreign tenant!
            event_type=TelemetryEventType.API_REQUEST,
            status=TelemetryStatus.SUCCESS,
        ),
    ]

    with pytest.raises(TenantIsolationError, match="Tenant isolation breach"):
        engine.aggregate_telemetry_events(org_a, events)


# =============================================================================
# 2. Unit Cost Calculation Tests ($/kReq and $/MTok)
# =============================================================================

def test_calculate_unit_cost_requests_cpm():
    """Calculates cost per 1,000 API requests (CPM) with high precision."""
    org_id = uuid.uuid4()
    feat_id = uuid.uuid4()
    engine = UnitEconomicsEngine()

    # Cost = $150.00 for 500,000 requests -> ($150 / 500,000) * 1,000 = $0.300000 / kReq
    calc = engine.calculate_unit_cost(
        organization_id=org_id,
        metric_type=UnitMetricType.REQUEST_COUNT,
        total_cost=Decimal("150.0000"),
        raw_usage=Decimal("500000"),
        unit_name="1k_requests",
        scaling_factor=1000,
        target_cost_per_unit=Decimal("0.350000"),
        product_feature_id=feat_id,
        feature_name="Semantic Search",
    )

    assert calc.unit_cost == Decimal("0.300000")
    assert calc.scaled_units == Decimal("500.0000")
    assert calc.status == UnitCostStatus.OPTIMAL
    # Variance against target 0.35: ((0.30 - 0.35) / 0.35) * 100 = -14.29%
    assert calc.cost_variance_percent == Decimal("-14.29")


def test_calculate_unit_cost_ai_tokens_per_million():
    """Calculates cost per 1,000,000 AI tokens ($/MTok)."""
    org_id = uuid.uuid4()
    feat_id = uuid.uuid4()
    engine = UnitEconomicsEngine()

    # Cost = $450.00 for 150,000,000 tokens -> ($450 / 150M) * 1M = $3.000000 / MTok
    calc = engine.calculate_unit_cost(
        organization_id=org_id,
        metric_type=UnitMetricType.AI_TOKEN,
        total_cost=Decimal("450.0000"),
        raw_usage=Decimal("150000000"),
        unit_name="1m_tokens",
        scaling_factor=1000000,
        target_cost_per_unit=Decimal("2.500000"),
        product_feature_id=feat_id,
        feature_name="RAG Assistant",
    )

    assert calc.unit_cost == Decimal("3.000000")
    assert calc.scaled_units == Decimal("150.0000")
    assert calc.status == UnitCostStatus.ELEVATED
    # Variance against target 2.50: ((3.00 - 2.50) / 2.50) * 100 = +20.00%
    assert calc.cost_variance_percent == Decimal("20.00")


def test_calculate_unit_cost_zero_traffic_idle_waste():
    """Positive infrastructure expenditure with zero requests is classified as IDLE_WASTE."""
    org_id = uuid.uuid4()
    engine = UnitEconomicsEngine()

    calc = engine.calculate_unit_cost(
        organization_id=org_id,
        metric_type=UnitMetricType.REQUEST_COUNT,
        total_cost=Decimal("85.0000"),
        raw_usage=Decimal("0"),
        unit_name="1k_requests",
    )

    assert calc.status == UnitCostStatus.ZERO_TRAFFIC_IDLE_WASTE
    assert calc.unit_cost is None
    assert calc.total_allocated_cost == Decimal("85.0000")


def test_calculate_unit_cost_zero_cost_unbilled():
    """Requests processed with zero infrastructure cost are classified as ZERO_COST_UNBILLED."""
    org_id = uuid.uuid4()
    engine = UnitEconomicsEngine()

    calc = engine.calculate_unit_cost(
        organization_id=org_id,
        metric_type=UnitMetricType.REQUEST_COUNT,
        total_cost=Decimal("0.0000"),
        raw_usage=Decimal("12000"),
        unit_name="1k_requests",
    )

    assert calc.status == UnitCostStatus.ZERO_COST_UNBILLED
    assert calc.unit_cost == Decimal("0.000000")


# =============================================================================
# 3. Feature Gross Margin & Strategic Health Scorecards
# =============================================================================

def test_feature_gross_margin_healthy():
    """Feature meeting or exceeding target margin is classified as HEALTHY."""
    org_id = uuid.uuid4()
    feat_id = uuid.uuid4()
    engine = UnitEconomicsEngine()

    # Revenue = $10,000, COGS Cost = $2,000 -> Profit = $8,000 -> Margin = 80.00% (Target: 75%)
    margin = engine.calculate_feature_margin(
        organization_id=org_id,
        feature_id=feat_id,
        feature_name="Core API",
        feature_slug="core-api",
        tier="core",
        target_gross_margin_percent=Decimal("75.00"),
        cogs_cost=Decimal("2000.0000"),
        revenue=Decimal("10000.00"),
    )

    assert margin.gross_profit == Decimal("8000.00")
    assert margin.actual_gross_margin_percent == Decimal("80.00")
    assert margin.margin_delta_percent == Decimal("5.00")
    assert margin.status == MarginHealthStatus.HEALTHY


def test_feature_gross_margin_warning_threshold():
    """Feature falling slightly below target (within 15%) is classified as WARNING."""
    org_id = uuid.uuid4()
    feat_id = uuid.uuid4()
    engine = UnitEconomicsEngine()

    # Revenue = $10,000, COGS Cost = $3,200 -> Profit = $6,800 -> Margin = 68.00% (Target: 75%, Delta: -7%)
    margin = engine.calculate_feature_margin(
        organization_id=org_id,
        feature_id=feat_id,
        feature_name="Analytics Engine",
        feature_slug="analytics",
        tier="enterprise",
        target_gross_margin_percent=Decimal("75.00"),
        cogs_cost=Decimal("3200.0000"),
        revenue=Decimal("10000.00"),
    )

    assert margin.actual_gross_margin_percent == Decimal("68.00")
    assert margin.margin_delta_percent == Decimal("-7.00")
    assert margin.status == MarginHealthStatus.WARNING


def test_feature_gross_margin_critical_threshold():
    """Feature falling more than 15% below target is classified as CRITICAL."""
    org_id = uuid.uuid4()
    feat_id = uuid.uuid4()
    engine = UnitEconomicsEngine()

    # Revenue = $10,000, COGS Cost = $5,500 -> Margin = 45.00% (Target: 75%, Delta: -30%)
    margin = engine.calculate_feature_margin(
        organization_id=org_id,
        feature_id=feat_id,
        feature_name="Document Parser",
        feature_slug="doc-parser",
        tier="core",
        target_gross_margin_percent=Decimal("75.00"),
        cogs_cost=Decimal("5500.0000"),
        revenue=Decimal("10000.00"),
    )

    assert margin.actual_gross_margin_percent == Decimal("45.00")
    assert margin.margin_delta_percent == Decimal("-30.00")
    assert margin.status == MarginHealthStatus.CRITICAL


def test_feature_gross_margin_negative_burn():
    """Feature where cost exceeds revenue is classified as NEGATIVE_MARGIN."""
    org_id = uuid.uuid4()
    feat_id = uuid.uuid4()
    engine = UnitEconomicsEngine()

    # Revenue = $5,000, COGS Cost = $7,500 -> Profit = -$2,500 -> Margin = -50.00%
    margin = engine.calculate_feature_margin(
        organization_id=org_id,
        feature_id=feat_id,
        feature_name="Model Training Lab",
        feature_slug="training-lab",
        tier="experimental",
        target_gross_margin_percent=Decimal("50.00"),
        cogs_cost=Decimal("7500.0000"),
        revenue=Decimal("5000.00"),
    )

    assert margin.gross_profit == Decimal("-2500.00")
    assert margin.actual_gross_margin_percent == Decimal("-50.00")
    assert margin.status == MarginHealthStatus.NEGATIVE_MARGIN


def test_feature_gross_margin_no_revenue():
    """Internal feature with cost but zero revenue is classified as NO_REVENUE."""
    org_id = uuid.uuid4()
    feat_id = uuid.uuid4()
    engine = UnitEconomicsEngine()

    margin = engine.calculate_feature_margin(
        organization_id=org_id,
        feature_id=feat_id,
        feature_name="Internal Audit",
        feature_slug="internal-audit",
        tier="internal",
        target_gross_margin_percent=Decimal("0.00"),
        cogs_cost=Decimal("450.0000"),
        revenue=Decimal("0.00"),
    )

    assert margin.actual_gross_margin_percent is None
    assert margin.status == MarginHealthStatus.NO_REVENUE


# =============================================================================
# 4. End-to-End Multi-Feature Telemetry & Cost Fusion
# =============================================================================

def test_end_to_end_fusion_report_generation():
    """Comprehensive test fusing multi-feature PostgreSQL costs and MongoDB telemetry."""
    org_id = uuid.uuid4()
    feat_search = uuid.uuid4()
    feat_rag = uuid.uuid4()
    feat_idle = uuid.uuid4()

    features = [
        {
            "id": feat_search,
            "name": "Semantic Search",
            "slug": "search",
            "tier": "core",
            "target_gross_margin_percent": Decimal("75.00"),
        },
        {
            "id": feat_rag,
            "name": "AI Assistant RAG",
            "slug": "rag",
            "tier": "enterprise",
            "target_gross_margin_percent": Decimal("70.00"),
        },
        {
            "id": feat_idle,
            "name": "Legacy Sandbox",
            "slug": "legacy",
            "tier": "experimental",
            "target_gross_margin_percent": Decimal("60.00"),
        },
    ]

    # Costs attributed from PostgreSQL
    attributed_costs = {
        feat_search: Decimal("250.0000"),
        feat_rag: Decimal("600.0000"),
        feat_idle: Decimal("100.0000"),
    }

    # Revenue mapped
    revenues = {
        feat_search: Decimal("1200.00"),  # Search: $1200 rev, $250 cost -> ~79.17% margin (HEALTHY)
        feat_rag: Decimal("1000.00"),    # RAG: $1000 rev, $600 cost -> 40.00% margin (CRITICAL)
        feat_idle: Decimal("0.00"),      # Idle: $0 rev, $100 cost -> NO_REVENUE
    }

    # Telemetry events from MongoDB
    events = [
        # Search events (10k requests, no tokens)
        TelemetryEvent(
            organization_id=org_id,
            product_feature_id=feat_search,
            event_type=TelemetryEventType.API_REQUEST,
            status=TelemetryStatus.SUCCESS,
            latency_ms=45.0,
        ),
        # RAG events (50k tokens)
        TelemetryEvent(
            organization_id=org_id,
            product_feature_id=feat_rag,
            event_type=TelemetryEventType.LLM_INFERENCE,
            tokens=TokenUsage(prompt_tokens=30000, completion_tokens=20000),
            status=TelemetryStatus.SUCCESS,
            latency_ms=280.0,
        ),
    ]

    engine = UnitEconomicsEngine()

    report = engine.fuse_costs_and_telemetry(
        organization_id=org_id,
        attributed_costs_by_feature=attributed_costs,
        telemetry_events=events,
        features=features,
        feature_revenues=revenues,
    )

    assert report.total_attributed_cost == Decimal("950.0000")
    assert report.total_revenue == Decimal("2200.00")
    # Overall profit: 2200 - 950 = 1250 -> (1250 / 2200) * 100 = 56.82%
    assert report.overall_gross_margin_percent == Decimal("56.82")

    # Verify margin scorecards
    search_margin = next(m for m in report.margins if m.product_feature_id == feat_search)
    rag_margin = next(m for m in report.margins if m.product_feature_id == feat_rag)
    idle_margin = next(m for m in report.margins if m.product_feature_id == feat_idle)

    assert search_margin.status == MarginHealthStatus.HEALTHY
    assert search_margin.actual_gross_margin_percent == Decimal("79.17")
    assert rag_margin.status == MarginHealthStatus.CRITICAL
    assert rag_margin.actual_gross_margin_percent == Decimal("40.00")
    assert idle_margin.status == MarginHealthStatus.NO_REVENUE

    # Verify metrics
    idle_req_metric = next(
        m for m in report.metrics
        if m.product_feature_id == feat_idle and m.metric_type == UnitMetricType.REQUEST_COUNT
    )
    assert idle_req_metric.status == UnitCostStatus.ZERO_TRAFFIC_IDLE_WASTE

    summary = report.summary()
    assert summary["healthy_features"] == 1
    assert summary["critical_features"] == 1
    assert summary["total_requests"] == 2
    assert summary["total_tokens"] == 50000
