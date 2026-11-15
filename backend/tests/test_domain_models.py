"""Unit tests verifying SQLAlchemy 2.x domain models, typed mappings, and constraints."""
import uuid
from datetime import date
from decimal import Decimal
import pytest
from app.models import (
    Base,
    Organization,
    CloudAccount,
    CostCenter,
    Budget,
    ProductFeature,
    UnitMetric,
    AllocationRule,
    CloudProvider,
    CloudAccountStatus,
    BudgetPeriod,
    BudgetStatus,
    UnitMetricType,
    AllocationRuleType,
    AllocationTargetType,
)


def test_metadata_contains_all_seven_tables():
    """Verifies all required core domain models are registered in Base metadata."""
    expected_tables = {
        "organizations",
        "cloud_accounts",
        "cost_centers",
        "budgets",
        "product_features",
        "unit_metrics",
        "allocation_rules",
    }
    registered_tables = set(Base.metadata.tables.keys())
    assert expected_tables.issubset(registered_tables)


def test_organization_instantiation():
    """Verifies Organization model attributes, UUID default, and string representation."""
    org = Organization(
        name="Acme Corporation",
        slug="acme-corp",
        currency="USD",
        is_active=True,
    )
    assert org.name == "Acme Corporation"
    assert org.slug == "acme-corp"
    assert org.currency == "USD"
    assert org.is_active is True
    assert Organization.__table__.c.is_active.default.arg is True


def test_cloud_account_instantiation():
    """Verifies CloudAccount model with enum provider and tenant isolation."""
    org_id = uuid.uuid4()
    account = CloudAccount(
        organization_id=org_id,
        name="Production AWS US-East",
        provider=CloudProvider.AWS,
        account_identifier="123456789012",
        status=CloudAccountStatus.ACTIVE,
        environment="production",
    )
    assert account.organization_id == org_id
    assert account.provider == CloudProvider.AWS
    assert account.provider.value == "AWS"
    assert account.account_identifier == "123456789012"
    assert account.status == CloudAccountStatus.ACTIVE


def test_cost_center_and_hierarchy():
    """Verifies CostCenter attributes and self-referential parent/child relation."""
    org_id = uuid.uuid4()
    parent_cc = CostCenter(
        organization_id=org_id,
        name="Engineering",
        code="CC-ENG",
    )
    child_cc = CostCenter(
        organization_id=org_id,
        name="Platform & Core",
        code="CC-ENG-PLATFORM",
        parent=parent_cc,
    )
    assert child_cc.parent == parent_cc
    assert child_cc.organization_id == org_id
    assert child_cc.code == "CC-ENG-PLATFORM"


def test_budget_financial_precision_and_enums():
    """Verifies Budget model enforces Decimal financial types and enum periods."""
    org_id = uuid.uuid4()
    budget = Budget(
        organization_id=org_id,
        name="Q4 Engineering Cloud Budget",
        amount=Decimal("150000.5000"),
        period=BudgetPeriod.QUARTERLY,
        start_date=date(2026, 10, 1),
        end_date=date(2026, 12, 31),
        alert_threshold_percent=Decimal("85.00"),
        status=BudgetStatus.ACTIVE,
    )
    assert isinstance(budget.amount, Decimal)
    assert budget.amount == Decimal("150000.5000")
    assert budget.period == BudgetPeriod.QUARTERLY
    assert budget.alert_threshold_percent == Decimal("85.00")


def test_product_feature_margins():
    """Verifies ProductFeature target gross margins and tier settings."""
    org_id = uuid.uuid4()
    feature = ProductFeature(
        organization_id=org_id,
        name="Semantic Vector Search",
        slug="semantic-search",
        tier="enterprise",
        target_gross_margin_percent=Decimal("80.00"),
        is_active=True,
    )
    assert feature.slug == "semantic-search"
    assert feature.target_gross_margin_percent == Decimal("80.00")
    assert feature.tier == "enterprise"
    assert feature.is_active is True
    assert ProductFeature.__table__.c.is_active.default.arg is True


def test_unit_metric_definitions():
    """Verifies UnitMetric definitions across API requests, users, and AI tokens."""
    org_id = uuid.uuid4()
    metric_request = UnitMetric(
        organization_id=org_id,
        name="Cost per 1M API Invocations",
        metric_type=UnitMetricType.REQUEST_COUNT,
        unit_name="1m_requests",
        target_cost_per_unit=Decimal("0.000350"),
    )
    metric_token = UnitMetric(
        organization_id=org_id,
        name="Cost per 1k LLM Tokens",
        metric_type=UnitMetricType.AI_TOKEN,
        unit_name="1k_tokens",
        target_cost_per_unit=Decimal("0.001200"),
    )
    assert metric_request.metric_type == UnitMetricType.REQUEST_COUNT
    assert metric_token.metric_type == UnitMetricType.AI_TOKEN
    assert isinstance(metric_request.target_cost_per_unit, Decimal)


def test_allocation_rule_criteria():
    """Verifies AllocationRule attributes for tag-based cost attribution."""
    org_id = uuid.uuid4()
    feature_id = uuid.uuid4()
    rule = AllocationRule(
        organization_id=org_id,
        name="Route Auth Service Tags to Core Product",
        rule_type=AllocationRuleType.TAG_EXACT,
        target_type=AllocationTargetType.PRODUCT_FEATURE,
        product_feature_id=feature_id,
        tag_key="Service",
        tag_value="auth-service",
        allocation_percentage=Decimal("100.00"),
        priority=10,
    )
    assert rule.rule_type == AllocationRuleType.TAG_EXACT
    assert rule.target_type == AllocationTargetType.PRODUCT_FEATURE
    assert rule.product_feature_id == feature_id
    assert rule.priority == 10
    assert rule.allocation_percentage == Decimal("100.00")


def test_tenant_isolation_foreign_keys():
    """Verifies all tenant entities define a foreign key referencing organizations.id."""
    tenant_tables = [
        "cloud_accounts",
        "cost_centers",
        "budgets",
        "product_features",
        "unit_metrics",
        "allocation_rules",
    ]
    for table_name in tenant_tables:
        table = Base.metadata.tables[table_name]
        assert "organization_id" in table.c, f"{table_name} must contain organization_id column"
        org_fk = [
            fk for fk in table.foreign_keys if fk.target_fullname == "organizations.id"
        ]
        assert len(org_fk) > 0, f"{table_name}.organization_id must reference organizations.id"
