"""Integrity tests verifying database-level multi-tenant isolation and composite FK constraints."""
import uuid
from datetime import date
from decimal import Decimal
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models import (
    Base,
    Organization,
    CostCenter,
    Budget,
    ProductFeature,
    UnitMetric,
    AllocationRule,
    BudgetPeriod,
    BudgetStatus,
    UnitMetricType,
    AllocationRuleType,
    AllocationTargetType,
)


@pytest.fixture
def db_session():
    """Provides an isolated in-memory relational SQLite database with strict foreign key enforcement."""
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, _):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


@pytest.fixture
def two_orgs(db_session: Session):
    """Creates two distinct organizations to test cross-tenant boundary integrity."""
    org_a = Organization(
        id=uuid.uuid4(),
        name="Tenant Alpha Corp",
        slug="tenant-alpha",
        currency="USD",
        is_active=True,
    )
    org_b = Organization(
        id=uuid.uuid4(),
        name="Tenant Beta Ltd",
        slug="tenant-beta",
        currency="USD",
        is_active=True,
    )
    db_session.add_all([org_a, org_b])
    db_session.commit()
    return org_a, org_b


def test_cross_org_cost_center_parent_rejected(db_session: Session, two_orgs):
    """Confirms the database rejects parenting a cost center to another organization's cost center."""
    org_a, org_b = two_orgs

    cc_a = CostCenter(
        id=uuid.uuid4(),
        organization_id=org_a.id,
        name="Alpha Engineering",
        code="CC-ENG-A",
    )
    db_session.add(cc_a)
    db_session.commit()

    # Attempt cross-organization hierarchy: Org B's CC points to Org A's CC as parent
    invalid_cc_b = CostCenter(
        id=uuid.uuid4(),
        organization_id=org_b.id,
        name="Beta Sub-team",
        code="CC-SUB-B",
        parent_id=cc_a.id,
    )
    db_session.add(invalid_cc_b)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_cross_org_budget_cost_center_rejected(db_session: Session, two_orgs):
    """Confirms the database rejects attaching a budget to another organization's cost center."""
    org_a, org_b = two_orgs

    cc_a = CostCenter(
        id=uuid.uuid4(),
        organization_id=org_a.id,
        name="Alpha Infrastructure",
        code="CC-INFRA-A",
    )
    db_session.add(cc_a)
    db_session.commit()

    # Attempt cross-organization budget: Org B's Budget attaches to Org A's CostCenter
    invalid_budget_b = Budget(
        id=uuid.uuid4(),
        organization_id=org_b.id,
        cost_center_id=cc_a.id,
        name="Beta Q1 Budget",
        amount=Decimal("50000.0000"),
        period=BudgetPeriod.QUARTERLY,
        start_date=date(2026, 1, 1),
        status=BudgetStatus.ACTIVE,
    )
    db_session.add(invalid_budget_b)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_cross_org_product_feature_cost_center_rejected(db_session: Session, two_orgs):
    """Confirms the database rejects linking a product feature to another organization's cost center."""
    org_a, org_b = two_orgs

    cc_a = CostCenter(
        id=uuid.uuid4(),
        organization_id=org_a.id,
        name="Alpha Product Group",
        code="CC-PROD-A",
    )
    db_session.add(cc_a)
    db_session.commit()

    # Attempt cross-organization feature: Org B's Feature attaches to Org A's CostCenter
    invalid_feature_b = ProductFeature(
        id=uuid.uuid4(),
        organization_id=org_b.id,
        cost_center_id=cc_a.id,
        name="Beta Analytics Feature",
        slug="beta-analytics",
        is_active=True,
    )
    db_session.add(invalid_feature_b)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_cross_org_unit_metric_product_feature_rejected(db_session: Session, two_orgs):
    """Confirms the database rejects associating a unit metric with another organization's product feature."""
    org_a, org_b = two_orgs

    pf_a = ProductFeature(
        id=uuid.uuid4(),
        organization_id=org_a.id,
        name="Alpha Search Engine",
        slug="alpha-search",
        is_active=True,
    )
    db_session.add(pf_a)
    db_session.commit()

    # Attempt cross-organization metric: Org B's Metric attaches to Org A's ProductFeature
    invalid_metric_b = UnitMetric(
        id=uuid.uuid4(),
        organization_id=org_b.id,
        product_feature_id=pf_a.id,
        name="Beta Cost Per Search",
        metric_type=UnitMetricType.REQUEST_COUNT,
        unit_name="query",
        target_cost_per_unit=Decimal("0.000500"),
    )
    db_session.add(invalid_metric_b)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_cross_org_allocation_rule_product_feature_rejected(db_session: Session, two_orgs):
    """Confirms the database rejects routing an allocation rule to another organization's product feature."""
    org_a, org_b = two_orgs

    pf_a = ProductFeature(
        id=uuid.uuid4(),
        organization_id=org_a.id,
        name="Alpha Video Encoding",
        slug="alpha-video",
        is_active=True,
    )
    db_session.add(pf_a)
    db_session.commit()

    # Attempt cross-organization rule: Org B's rule routes to Org A's ProductFeature
    invalid_rule_b = AllocationRule(
        id=uuid.uuid4(),
        organization_id=org_b.id,
        name="Beta Video Tag Routing",
        rule_type=AllocationRuleType.TAG_EXACT,
        target_type=AllocationTargetType.PRODUCT_FEATURE,
        product_feature_id=pf_a.id,
        tag_key="service",
        tag_value="video-transcoder",
        is_active=True,
    )
    db_session.add(invalid_rule_b)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_cross_org_allocation_rule_cost_center_rejected(db_session: Session, two_orgs):
    """Confirms the database rejects routing an allocation rule to another organization's cost center."""
    org_a, org_b = two_orgs

    cc_a = CostCenter(
        id=uuid.uuid4(),
        organization_id=org_a.id,
        name="Alpha Machine Learning",
        code="CC-ML-A",
    )
    db_session.add(cc_a)
    db_session.commit()

    # Attempt cross-organization rule: Org B's rule routes to Org A's CostCenter
    invalid_rule_b = AllocationRule(
        id=uuid.uuid4(),
        organization_id=org_b.id,
        name="Beta GPU Allocation",
        rule_type=AllocationRuleType.TAG_EXACT,
        target_type=AllocationTargetType.COST_CENTER,
        cost_center_id=cc_a.id,
        tag_key="accelerator",
        tag_value="nvidia-h100",
        is_active=True,
    )
    db_session.add(invalid_rule_b)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_valid_same_org_relationships_succeed(db_session: Session, two_orgs):
    """Confirms that intra-organization entity relationships are fully valid and permitted."""
    org_a, _ = two_orgs

    parent_cc = CostCenter(
        id=uuid.uuid4(),
        organization_id=org_a.id,
        name="Engineering Division",
        code="CC-ENG",
    )
    child_cc = CostCenter(
        id=uuid.uuid4(),
        organization_id=org_a.id,
        name="Platform Squad",
        code="CC-ENG-PLATFORM",
        parent_id=parent_cc.id,
    )
    budget = Budget(
        id=uuid.uuid4(),
        organization_id=org_a.id,
        cost_center_id=child_cc.id,
        name="Platform Cloud Budget",
        amount=Decimal("75000.0000"),
        period=BudgetPeriod.MONTHLY,
        start_date=date(2026, 11, 1),
        status=BudgetStatus.ACTIVE,
    )
    feature = ProductFeature(
        id=uuid.uuid4(),
        organization_id=org_a.id,
        cost_center_id=child_cc.id,
        name="Vector Embeddings Engine",
        slug="vector-embeddings",
        is_active=True,
    )
    metric = UnitMetric(
        id=uuid.uuid4(),
        organization_id=org_a.id,
        product_feature_id=feature.id,
        name="Cost Per 1k Embedding Calls",
        metric_type=UnitMetricType.AI_TOKEN,
        unit_name="1k_embeddings",
        target_cost_per_unit=Decimal("0.000120"),
    )
    rule = AllocationRule(
        id=uuid.uuid4(),
        organization_id=org_a.id,
        name="Direct Embeddings Cluster Allocation",
        rule_type=AllocationRuleType.TAG_EXACT,
        target_type=AllocationTargetType.PRODUCT_FEATURE,
        product_feature_id=feature.id,
        tag_key="cluster",
        tag_value="embeddings-prod",
        allocation_percentage=Decimal("100.00"),
        is_active=True,
    )

    db_session.add_all([parent_cc, child_cc, budget, feature, metric, rule])
    db_session.commit()

    # Assert all entities persist cleanly within org_a
    assert child_cc.parent_id == parent_cc.id
    assert budget.cost_center_id == child_cc.id
    assert feature.cost_center_id == child_cc.id
    assert metric.product_feature_id == feature.id
    assert rule.product_feature_id == feature.id
