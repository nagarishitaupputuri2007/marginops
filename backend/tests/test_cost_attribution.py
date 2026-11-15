"""Comprehensive unit tests for the deterministic cost attribution engine."""
import uuid
from datetime import date
from decimal import Decimal
import pytest

from app.models.enums import AllocationRuleType, AllocationTargetType, CloudProvider
from app.models.cost_record import CostRecord
from app.models.allocation_rule import AllocationRule
from app.services.cost_attribution import (
    CostAttributionEngine,
    AttributionResult,
    AttributedCostItem,
    AttributionMethod,
    UnallocatedReason,
    CostAttributionError,
    ReconciliationError,
    TenantIsolationError,
    distribute_amount_by_weights,
)


# =============================================================================
# 1. Largest Remainder Method (Hare-Niemeyer) & Rounding Tests
# =============================================================================

def test_hare_niemeyer_3_way_split_no_penny_leak():
    """Splitting $100.00 three ways (1:1:1) with 2 decimals must give 33.34, 33.33, 33.33 summing to 100.00."""
    amount = Decimal("100.00")
    weights = [Decimal("1"), Decimal("1"), Decimal("1")]
    shares = distribute_amount_by_weights(amount, weights, precision=Decimal("0.01"))

    assert len(shares) == 3
    assert shares[0] == Decimal("33.34")
    assert shares[1] == Decimal("33.33")
    assert shares[2] == Decimal("33.33")
    assert sum(shares) == amount


def test_hare_niemeyer_negative_credit_symmetric():
    """Negative credits/refunds must be split symmetrically with zero discrepancy."""
    amount = Decimal("-100.00")
    weights = [Decimal("1"), Decimal("1"), Decimal("1")]
    shares = distribute_amount_by_weights(amount, weights, precision=Decimal("0.01"))

    assert len(shares) == 3
    assert shares[0] == Decimal("-33.34")
    assert shares[1] == Decimal("-33.33")
    assert shares[2] == Decimal("-33.33")
    assert sum(shares) == amount


def test_hare_niemeyer_4_decimal_places_precision():
    """High-precision financial figures matching Numeric(18, 4) must balance down to 0.0001."""
    amount = Decimal("17295.4074")
    weights = [Decimal("40"), Decimal("60")]
    shares = distribute_amount_by_weights(amount, weights, precision=Decimal("0.0001"))

    assert len(shares) == 2
    assert sum(shares) == amount
    # Verify shares are within expected proportional brackets
    assert shares[0] == Decimal("6918.1630")
    assert shares[1] == Decimal("10377.2444")


def test_distribute_amount_zero_amount():
    """Zero amount returns zero shares."""
    amount = Decimal("0.00")
    weights = [Decimal("1"), Decimal("2")]
    shares = distribute_amount_by_weights(amount, weights, precision=Decimal("0.01"))
    assert shares == [Decimal("0.00"), Decimal("0.00")]
    assert sum(shares) == Decimal("0.00")


# =============================================================================
# 2. Direct Attribution Tests (Features & Workloads)
# =============================================================================

def test_direct_attribution_by_product_feature():
    """CostRecord with explicit product_feature_id is attributed 100% directly."""
    org_id = uuid.uuid4()
    feat_id = uuid.uuid4()
    engine = CostAttributionEngine()

    record = {
        "id": uuid.uuid4(),
        "organization_id": org_id,
        "billing_date": date(2026, 3, 15),
        "cloud_provider": "AWS",
        "service_id": "AmazonEC2",
        "billing_amount": Decimal("150.2500"),
        "product_feature_id": feat_id,
        "workload_id": "api-backend",
        "resource_tags": {"env": "prod"},
    }

    items = engine.attribute_record(
        record=record,
        valid_feature_ids={feat_id},
    )

    assert len(items) == 1
    item = items[0]
    assert item.is_allocated is True
    assert item.attribution_method == AttributionMethod.DIRECT_FEATURE
    assert item.target_type == AllocationTargetType.PRODUCT_FEATURE
    assert item.product_feature_id == feat_id
    assert item.allocated_amount == Decimal("150.2500")
    assert item.allocation_percentage == Decimal("100.00")


def test_direct_attribution_by_workload_mapping():
    """CostRecord without feature_id but with mapped workload_id is attributed directly."""
    org_id = uuid.uuid4()
    feat_id = uuid.uuid4()
    engine = CostAttributionEngine()

    record = {
        "id": uuid.uuid4(),
        "organization_id": org_id,
        "billing_date": date(2026, 3, 15),
        "cloud_provider": "GCP",
        "service_id": "VertexAI",
        "billing_amount": Decimal("240.5000"),
        "product_feature_id": None,
        "workload_id": "rag-indexing",
        "resource_tags": {},
    }

    workload_mapping = {
        "rag-indexing": {
            "organization_id": org_id,
            "target_type": AllocationTargetType.PRODUCT_FEATURE,
            "product_feature_id": feat_id,
        }
    }

    items = engine.attribute_record(
        record=record,
        valid_feature_ids={feat_id},
        workload_mapping=workload_mapping,
    )

    assert len(items) == 1
    item = items[0]
    assert item.is_allocated is True
    assert item.attribution_method == AttributionMethod.DIRECT_WORKLOAD
    assert item.product_feature_id == feat_id
    assert item.allocated_amount == Decimal("240.5000")


def test_direct_attribution_precedence_over_rules():
    """Direct product_feature_id takes precedence even if a rule matches resource tags."""
    org_id = uuid.uuid4()
    direct_feat_id = uuid.uuid4()
    rule_feat_id = uuid.uuid4()
    engine = CostAttributionEngine()

    rule = AllocationRule(
        id=uuid.uuid4(),
        organization_id=org_id,
        name="Tag Infra Match",
        rule_type=AllocationRuleType.TAG_EXACT,
        target_type=AllocationTargetType.PRODUCT_FEATURE,
        product_feature_id=rule_feat_id,
        tag_key="team",
        tag_value="search",
        priority=10,
        is_active=True,
    )

    record = {
        "id": uuid.uuid4(),
        "organization_id": org_id,
        "billing_amount": Decimal("88.0000"),
        "product_feature_id": direct_feat_id,
        "resource_tags": {"team": "search"},
    }

    items = engine.attribute_record(
        record=record,
        rules=[rule],
        valid_feature_ids={direct_feat_id, rule_feat_id},
    )

    assert len(items) == 1
    assert items[0].attribution_method == AttributionMethod.DIRECT_FEATURE
    assert items[0].product_feature_id == direct_feat_id


# =============================================================================
# 3. Shared Cost Allocation (TAG_EXACT, TAG_PREFIX, FIXED_PERCENTAGE, USAGE_PROPORTIONAL)
# =============================================================================

def test_shared_allocation_tag_exact():
    """TAG_EXACT rule matches exact tag key-value and attributes 100% to target."""
    org_id = uuid.uuid4()
    feat_id = uuid.uuid4()
    engine = CostAttributionEngine()

    rule = AllocationRule(
        id=uuid.uuid4(),
        organization_id=org_id,
        name="Search Exact Tag",
        rule_type=AllocationRuleType.TAG_EXACT,
        target_type=AllocationTargetType.PRODUCT_FEATURE,
        product_feature_id=feat_id,
        tag_key="component",
        tag_value="vector-db",
        priority=10,
        is_active=True,
    )

    record = {
        "id": uuid.uuid4(),
        "organization_id": org_id,
        "billing_amount": Decimal("500.0000"),
        "resource_tags": {"component": "vector-db", "env": "prod"},
    }

    items = engine.attribute_record(
        record=record,
        rules=[rule],
        valid_feature_ids={feat_id},
    )

    assert len(items) == 1
    item = items[0]
    assert item.is_allocated is True
    assert item.attribution_method == AttributionMethod.TAG_EXACT
    assert item.product_feature_id == feat_id
    assert item.allocated_amount == Decimal("500.0000")


def test_shared_allocation_tag_prefix():
    """TAG_PREFIX rule matches tag starting with prefix."""
    org_id = uuid.uuid4()
    feat_id = uuid.uuid4()
    engine = CostAttributionEngine()

    rule = AllocationRule(
        id=uuid.uuid4(),
        organization_id=org_id,
        name="Search Prefix Tag",
        rule_type=AllocationRuleType.TAG_PREFIX,
        target_type=AllocationTargetType.PRODUCT_FEATURE,
        product_feature_id=feat_id,
        tag_key="k8s_ns",
        tag_value="search-",
        priority=10,
        is_active=True,
    )

    record = {
        "id": uuid.uuid4(),
        "organization_id": org_id,
        "billing_amount": Decimal("320.0000"),
        "resource_tags": {"k8s_ns": "search-indexing-worker"},
    }

    items = engine.attribute_record(
        record=record,
        rules=[rule],
        valid_feature_ids={feat_id},
    )

    assert len(items) == 1
    item = items[0]
    assert item.is_allocated is True
    assert item.attribution_method == AttributionMethod.TAG_PREFIX
    assert item.product_feature_id == feat_id
    assert item.allocated_amount == Decimal("320.0000")


def test_shared_allocation_fixed_percentage_split():
    """Multiple rules at the same priority level split cost by specified percentages."""
    org_id = uuid.uuid4()
    feat_a = uuid.uuid4()
    feat_b = uuid.uuid4()
    engine = CostAttributionEngine()

    rule_a = AllocationRule(
        id=uuid.uuid4(),
        organization_id=org_id,
        name="Shared DB 40%",
        rule_type=AllocationRuleType.FIXED_PERCENTAGE,
        target_type=AllocationTargetType.PRODUCT_FEATURE,
        product_feature_id=feat_a,
        tag_key="shared",
        tag_value="true",
        allocation_percentage=Decimal("40.00"),
        priority=20,
        is_active=True,
    )
    rule_b = AllocationRule(
        id=uuid.uuid4(),
        organization_id=org_id,
        name="Shared DB 60%",
        rule_type=AllocationRuleType.FIXED_PERCENTAGE,
        target_type=AllocationTargetType.PRODUCT_FEATURE,
        product_feature_id=feat_b,
        tag_key="shared",
        tag_value="true",
        allocation_percentage=Decimal("60.00"),
        priority=20,
        is_active=True,
    )

    record = {
        "id": uuid.uuid4(),
        "organization_id": org_id,
        "billing_amount": Decimal("1000.0000"),
        "resource_tags": {"shared": "true"},
    }

    items = engine.attribute_record(
        record=record,
        rules=[rule_a, rule_b],
        valid_feature_ids={feat_a, feat_b},
    )

    assert len(items) == 2
    assert all(i.is_allocated for i in items)
    assert sum(i.allocated_amount for i in items) == Decimal("1000.0000")

    item_a = next(i for i in items if i.product_feature_id == feat_a)
    item_b = next(i for i in items if i.product_feature_id == feat_b)
    assert item_a.allocated_amount == Decimal("400.0000")
    assert item_b.allocated_amount == Decimal("600.0000")


def test_shared_allocation_usage_proportional_with_weights():
    """USAGE_PROPORTIONAL rule splits cost proportionally based on supplied usage weights."""
    org_id = uuid.uuid4()
    feat_a = uuid.uuid4()
    feat_b = uuid.uuid4()
    engine = CostAttributionEngine()

    rule_a = AllocationRule(
        id=uuid.uuid4(),
        organization_id=org_id,
        name="Shared AI Cluster Feature A",
        rule_type=AllocationRuleType.USAGE_PROPORTIONAL,
        target_type=AllocationTargetType.PRODUCT_FEATURE,
        product_feature_id=feat_a,
        tag_key="service",
        tag_value="ai-gateway",
        priority=10,
        is_active=True,
    )
    rule_b = AllocationRule(
        id=uuid.uuid4(),
        organization_id=org_id,
        name="Shared AI Cluster Feature B",
        rule_type=AllocationRuleType.USAGE_PROPORTIONAL,
        target_type=AllocationTargetType.PRODUCT_FEATURE,
        product_feature_id=feat_b,
        tag_key="service",
        tag_value="ai-gateway",
        priority=10,
        is_active=True,
    )

    record = {
        "id": uuid.uuid4(),
        "organization_id": org_id,
        "billing_amount": Decimal("150.0000"),
        "resource_tags": {"service": "ai-gateway"},
    }

    # Feature A consumed 3000 tokens, Feature B consumed 7000 tokens (30% / 70%)
    usage_weights = {
        feat_a: Decimal("3000"),
        feat_b: Decimal("7000"),
    }

    items = engine.attribute_record(
        record=record,
        rules=[rule_a, rule_b],
        valid_feature_ids={feat_a, feat_b},
        usage_weights=usage_weights,
    )

    assert len(items) == 2
    assert all(i.is_allocated for i in items)
    assert sum(i.allocated_amount for i in items) == Decimal("150.0000")

    item_a = next(i for i in items if i.product_feature_id == feat_a)
    item_b = next(i for i in items if i.product_feature_id == feat_b)
    assert item_a.allocated_amount == Decimal("45.0000")
    assert item_b.allocated_amount == Decimal("105.0000")


def test_shared_allocation_usage_proportional_missing_weights():
    """USAGE_PROPORTIONAL rule with missing usage weights preserves cost as UNALLOCATED without inventing numbers."""
    org_id = uuid.uuid4()
    feat_a = uuid.uuid4()
    engine = CostAttributionEngine()

    rule = AllocationRule(
        id=uuid.uuid4(),
        organization_id=org_id,
        name="Usage Rule",
        rule_type=AllocationRuleType.USAGE_PROPORTIONAL,
        target_type=AllocationTargetType.PRODUCT_FEATURE,
        product_feature_id=feat_a,
        tag_key="service",
        tag_value="ai-gateway",
        priority=10,
        is_active=True,
    )

    record = {
        "id": uuid.uuid4(),
        "organization_id": org_id,
        "billing_amount": Decimal("150.0000"),
        "resource_tags": {"service": "ai-gateway"},
    }

    items = engine.attribute_record(
        record=record,
        rules=[rule],
        valid_feature_ids={feat_a},
        usage_weights=None,  # Missing weights!
    )

    assert len(items) == 1
    item = items[0]
    assert item.is_allocated is False
    assert item.attribution_method == AttributionMethod.UNALLOCATED
    assert item.unallocated_reason == UnallocatedReason.MISSING_USAGE_WEIGHTS
    assert item.allocated_amount == Decimal("150.0000")


# =============================================================================
# 4. Partial Allocation & Unallocated Remainder Tests
# =============================================================================

def test_partial_allocation_preserves_unallocated_remainder():
    """Rule specifying 40% allocates $40 and preserves $60 as unallocated remainder."""
    org_id = uuid.uuid4()
    feat_id = uuid.uuid4()
    engine = CostAttributionEngine()

    rule = AllocationRule(
        id=uuid.uuid4(),
        organization_id=org_id,
        name="Partial 40% Rule",
        rule_type=AllocationRuleType.TAG_EXACT,
        target_type=AllocationTargetType.PRODUCT_FEATURE,
        product_feature_id=feat_id,
        tag_key="env",
        tag_value="staging",
        allocation_percentage=Decimal("40.00"),
        priority=10,
        is_active=True,
    )

    record = {
        "id": uuid.uuid4(),
        "organization_id": org_id,
        "billing_amount": Decimal("100.0000"),
        "resource_tags": {"env": "staging"},
    }

    items = engine.attribute_record(
        record=record,
        rules=[rule],
        valid_feature_ids={feat_id},
    )

    assert len(items) == 2
    allocated_item = next(i for i in items if i.is_allocated)
    unallocated_item = next(i for i in items if not i.is_allocated)

    assert allocated_item.allocated_amount == Decimal("40.0000")
    assert allocated_item.product_feature_id == feat_id

    assert unallocated_item.allocated_amount == Decimal("60.0000")
    assert unallocated_item.unallocated_reason == UnallocatedReason.PARTIAL_ALLOCATION_REMAINDER
    assert sum(i.allocated_amount for i in items) == Decimal("100.0000")


def test_unallocated_costs_no_matching_rules():
    """Record that matches no rules is 100% preserved as UNALLOCATED with NO_MATCHING_RULE."""
    org_id = uuid.uuid4()
    engine = CostAttributionEngine()

    record = {
        "id": uuid.uuid4(),
        "organization_id": org_id,
        "billing_amount": Decimal("75.5000"),
        "resource_tags": {"team": "unknown"},
    }

    items = engine.attribute_record(
        record=record,
        rules=[],
    )

    assert len(items) == 1
    item = items[0]
    assert item.is_allocated is False
    assert item.attribution_method == AttributionMethod.UNALLOCATED
    assert item.unallocated_reason == UnallocatedReason.NO_MATCHING_RULE
    assert item.allocated_amount == Decimal("75.5000")


def test_unallocated_costs_inactive_rules_ignored():
    """Rules with is_active=False are ignored and do not attribute costs."""
    org_id = uuid.uuid4()
    feat_id = uuid.uuid4()
    engine = CostAttributionEngine()

    rule = AllocationRule(
        id=uuid.uuid4(),
        organization_id=org_id,
        name="Inactive Rule",
        rule_type=AllocationRuleType.TAG_EXACT,
        target_type=AllocationTargetType.PRODUCT_FEATURE,
        product_feature_id=feat_id,
        tag_key="env",
        tag_value="prod",
        priority=10,
        is_active=False,  # Inactive!
    )

    record = {
        "id": uuid.uuid4(),
        "organization_id": org_id,
        "billing_amount": Decimal("200.0000"),
        "resource_tags": {"env": "prod"},
    }

    items = engine.attribute_record(
        record=record,
        rules=[rule],
        valid_feature_ids={feat_id},
    )

    assert len(items) == 1
    assert items[0].is_allocated is False
    assert items[0].unallocated_reason == UnallocatedReason.NO_MATCHING_RULE


# =============================================================================
# 5. Negative Credits and Refunds Tests
# =============================================================================

def test_negative_credit_direct_attribution():
    """Negative billing amounts (credits/refunds) are preserved with sign and credit flag."""
    org_id = uuid.uuid4()
    feat_id = uuid.uuid4()
    engine = CostAttributionEngine()

    record = {
        "id": uuid.uuid4(),
        "organization_id": org_id,
        "billing_amount": Decimal("-250.7500"),
        "product_feature_id": feat_id,
        "is_credit": True,
    }

    items = engine.attribute_record(
        record=record,
        valid_feature_ids={feat_id},
    )

    assert len(items) == 1
    item = items[0]
    assert item.is_allocated is True
    assert item.is_credit is True
    assert item.allocated_amount == Decimal("-250.7500")


def test_negative_credit_shared_split():
    """Negative credit split 50/50 preserves exact negative numbers with zero delta."""
    org_id = uuid.uuid4()
    feat_a = uuid.uuid4()
    feat_b = uuid.uuid4()
    engine = CostAttributionEngine()

    rule_a = AllocationRule(
        id=uuid.uuid4(),
        organization_id=org_id,
        name="Credit Rule A",
        rule_type=AllocationRuleType.FIXED_PERCENTAGE,
        target_type=AllocationTargetType.PRODUCT_FEATURE,
        product_feature_id=feat_a,
        tag_key="account",
        tag_value="credits",
        allocation_percentage=Decimal("50.00"),
        priority=10,
        is_active=True,
    )
    rule_b = AllocationRule(
        id=uuid.uuid4(),
        organization_id=org_id,
        name="Credit Rule B",
        rule_type=AllocationRuleType.FIXED_PERCENTAGE,
        target_type=AllocationTargetType.PRODUCT_FEATURE,
        product_feature_id=feat_b,
        tag_key="account",
        tag_value="credits",
        allocation_percentage=Decimal("50.00"),
        priority=10,
        is_active=True,
    )

    record = {
        "id": uuid.uuid4(),
        "organization_id": org_id,
        "billing_amount": Decimal("-500.0000"),
        "resource_tags": {"account": "credits"},
        "is_credit": True,
    }

    items = engine.attribute_record(
        record=record,
        rules=[rule_a, rule_b],
        valid_feature_ids={feat_a, feat_b},
    )

    assert len(items) == 2
    assert sum(i.allocated_amount for i in items) == Decimal("-500.0000")
    assert all(i.is_credit is True for i in items)
    assert items[0].allocated_amount == Decimal("-250.0000")
    assert items[1].allocated_amount == Decimal("-250.0000")


# =============================================================================
# 6. Priority & Duplicate Allocation Prevention
# =============================================================================

def test_prevention_of_duplicate_allocation():
    """Once a higher priority rule allocates 100%, lower priority rules are not evaluated."""
    org_id = uuid.uuid4()
    feat_high = uuid.uuid4()
    feat_low = uuid.uuid4()
    engine = CostAttributionEngine()

    rule_high = AllocationRule(
        id=uuid.uuid4(),
        organization_id=org_id,
        name="Priority 10 Rule",
        rule_type=AllocationRuleType.TAG_EXACT,
        target_type=AllocationTargetType.PRODUCT_FEATURE,
        product_feature_id=feat_high,
        tag_key="env",
        tag_value="prod",
        priority=10,
        is_active=True,
    )
    rule_low = AllocationRule(
        id=uuid.uuid4(),
        organization_id=org_id,
        name="Priority 20 Rule",
        rule_type=AllocationRuleType.TAG_EXACT,
        target_type=AllocationTargetType.PRODUCT_FEATURE,
        product_feature_id=feat_low,
        tag_key="env",
        tag_value="prod",
        priority=20,
        is_active=True,
    )

    record = {
        "id": uuid.uuid4(),
        "organization_id": org_id,
        "billing_amount": Decimal("100.0000"),
        "resource_tags": {"env": "prod"},
    }

    items = engine.attribute_record(
        record=record,
        rules=[rule_high, rule_low],
        valid_feature_ids={feat_high, feat_low},
    )

    assert len(items) == 1
    assert items[0].product_feature_id == feat_high
    assert items[0].allocated_amount == Decimal("100.0000")


def test_waterfall_capping_prevents_over_allocation():
    """Rules whose percentages exceed 100% are capped so total allocation never exceeds 100%."""
    org_id = uuid.uuid4()
    feat_a = uuid.uuid4()
    feat_b = uuid.uuid4()
    engine = CostAttributionEngine()

    # Rule A asks for 70%, Rule B asks for 50% (total 120%)
    rule_a = AllocationRule(
        id=uuid.uuid4(),
        organization_id=org_id,
        name="Rule A 70%",
        rule_type=AllocationRuleType.FIXED_PERCENTAGE,
        target_type=AllocationTargetType.PRODUCT_FEATURE,
        product_feature_id=feat_a,
        tag_key="pool",
        tag_value="shared",
        allocation_percentage=Decimal("70.00"),
        priority=10,
        is_active=True,
    )
    rule_b = AllocationRule(
        id=uuid.uuid4(),
        organization_id=org_id,
        name="Rule B 50%",
        rule_type=AllocationRuleType.FIXED_PERCENTAGE,
        target_type=AllocationTargetType.PRODUCT_FEATURE,
        product_feature_id=feat_b,
        tag_key="pool",
        tag_value="shared",
        allocation_percentage=Decimal("50.00"),
        priority=10,
        is_active=True,
    )

    record = {
        "id": uuid.uuid4(),
        "organization_id": org_id,
        "billing_amount": Decimal("100.0000"),
        "resource_tags": {"pool": "shared"},
    }

    items = engine.attribute_record(
        record=record,
        rules=[rule_a, rule_b],
        valid_feature_ids={feat_a, feat_b},
    )

    # Rule A takes 70%, Rule B takes remaining 30%
    assert sum(i.allocated_amount for i in items) == Decimal("100.0000")
    item_a = next(i for i in items if i.product_feature_id == feat_a)
    item_b = next(i for i in items if i.product_feature_id == feat_b)
    assert item_a.allocated_amount == Decimal("70.0000")
    assert item_b.allocated_amount == Decimal("30.0000")


# =============================================================================
# 7. Tenant Isolation Tests
# =============================================================================

def test_tenant_isolation_rejects_cross_org_feature_reference():
    """CostRecord of Org A referencing ProductFeature of Org B is rejected under strict mode."""
    org_a = uuid.uuid4()
    feat_org_b = uuid.uuid4()
    engine = CostAttributionEngine(strict_tenant_isolation=True)

    record = {
        "id": uuid.uuid4(),
        "organization_id": org_a,
        "billing_amount": Decimal("100.0000"),
        "product_feature_id": feat_org_b,
    }

    # Org A only contains feat_org_a
    with pytest.raises(TenantIsolationError, match="Cross-organization reference detected"):
        engine.attribute_record(
            record=record,
            valid_feature_ids={uuid.uuid4()},  # feat_org_b is missing
        )


def test_tenant_isolation_preserves_unallocated_when_non_strict():
    """Under non-strict mode, cross-org reference is preserved as UNALLOCATED instead of raising."""
    org_a = uuid.uuid4()
    feat_org_b = uuid.uuid4()
    engine = CostAttributionEngine(strict_tenant_isolation=False)

    record = {
        "id": uuid.uuid4(),
        "organization_id": org_a,
        "billing_amount": Decimal("100.0000"),
        "product_feature_id": feat_org_b,
    }

    items = engine.attribute_record(
        record=record,
        valid_feature_ids={uuid.uuid4()},
    )

    assert len(items) == 1
    assert items[0].is_allocated is False
    assert items[0].unallocated_reason == UnallocatedReason.CROSS_ORG_REFERENCE_REJECTED
    assert items[0].allocated_amount == Decimal("100.0000")


def test_tenant_isolation_ignores_rules_of_other_org():
    """Rules belonging to Org B never match or allocate records of Org A."""
    org_a = uuid.uuid4()
    org_b = uuid.uuid4()
    feat_b = uuid.uuid4()
    engine = CostAttributionEngine()

    rule_b = AllocationRule(
        id=uuid.uuid4(),
        organization_id=org_b,  # Belongs to Org B!
        name="Org B Rule",
        rule_type=AllocationRuleType.TAG_EXACT,
        target_type=AllocationTargetType.PRODUCT_FEATURE,
        product_feature_id=feat_b,
        tag_key="env",
        tag_value="prod",
        priority=10,
        is_active=True,
    )

    record_a = {
        "id": uuid.uuid4(),
        "organization_id": org_a,  # Belongs to Org A!
        "billing_amount": Decimal("100.0000"),
        "resource_tags": {"env": "prod"},
    }

    items = engine.attribute_record(
        record=record_a,
        rules=[rule_b],
    )

    # Rule B was ignored, so record remains unallocated
    assert len(items) == 1
    assert items[0].is_allocated is False
    assert items[0].unallocated_reason == UnallocatedReason.NO_MATCHING_RULE


def test_tenant_isolation_rejects_cross_org_batch_record():
    """Batch execution rejects records belonging to a different tenant."""
    org_a = uuid.uuid4()
    org_b = uuid.uuid4()
    engine = CostAttributionEngine(strict_tenant_isolation=True)

    records = [
        {"id": uuid.uuid4(), "organization_id": org_a, "billing_amount": Decimal("50.0000")},
        {"id": uuid.uuid4(), "organization_id": org_b, "billing_amount": Decimal("50.0000")},
    ]

    with pytest.raises(TenantIsolationError, match="not the target batch organization"):
        engine.attribute_batch(
            organization_id=org_a,
            records=records,
        )


# =============================================================================
# 8. Batch Reconciliation & Aggregations
# =============================================================================

def test_full_batch_reconciliation_mixed_dataset():
    """Comprehensive batch satisfies Source == Allocated + Unallocated down to 0.0000."""
    org_id = uuid.uuid4()
    feat_direct = uuid.uuid4()
    feat_rule = uuid.uuid4()
    feat_wl = uuid.uuid4()
    valid_features = {feat_direct, feat_rule, feat_wl}

    engine = CostAttributionEngine()

    rule = AllocationRule(
        id=uuid.uuid4(),
        organization_id=org_id,
        name="Database Rule 60%",
        rule_type=AllocationRuleType.TAG_EXACT,
        target_type=AllocationTargetType.PRODUCT_FEATURE,
        product_feature_id=feat_rule,
        tag_key="component",
        tag_value="database",
        allocation_percentage=Decimal("60.00"),
        priority=10,
        is_active=True,
    )

    workload_map = {
        "worker-rag": {
            "organization_id": org_id,
            "target_type": AllocationTargetType.PRODUCT_FEATURE,
            "product_feature_id": feat_wl,
        }
    }

    records = [
        # 1. Direct feature attribution ($250.00)
        {
            "id": uuid.uuid4(),
            "organization_id": org_id,
            "billing_amount": Decimal("250.0000"),
            "product_feature_id": feat_direct,
        },
        # 2. Direct workload attribution ($120.50)
        {
            "id": uuid.uuid4(),
            "organization_id": org_id,
            "billing_amount": Decimal("120.5000"),
            "workload_id": "worker-rag",
        },
        # 3. Partial rule match ($100.00 -> $60 allocated, $40 unallocated remainder)
        {
            "id": uuid.uuid4(),
            "organization_id": org_id,
            "billing_amount": Decimal("100.0000"),
            "resource_tags": {"component": "database"},
        },
        # 4. Completely unallocated record ($85.25)
        {
            "id": uuid.uuid4(),
            "organization_id": org_id,
            "billing_amount": Decimal("85.2500"),
            "resource_tags": {"unknown": "tag"},
        },
        # 5. Negative credit ($ -50.00 directly to feat_direct)
        {
            "id": uuid.uuid4(),
            "organization_id": org_id,
            "billing_amount": Decimal("-50.0000"),
            "product_feature_id": feat_direct,
            "is_credit": True,
        },
    ]

    # Expected arithmetic:
    # 250.0000 + 120.5000 + 100.0000 + 85.2500 - 50.0000 = 505.7500
    expected_source_total = Decimal("505.7500")

    result = engine.attribute_batch(
        organization_id=org_id,
        records=records,
        rules=[rule],
        valid_feature_ids=valid_features,
        workload_mapping=workload_map,
        reconcile=True,
    )

    assert result.is_reconciled is True
    assert result.reconciliation_delta == Decimal("0.0000")
    assert result.total_source_amount == expected_source_total
    assert (
        result.total_source_amount
        == result.total_allocated_amount + result.total_unallocated_amount
    )

    # Check aggregations
    assert feat_direct in result.by_feature
    assert result.by_feature[feat_direct] == Decimal("200.0000")  # 250 - 50
    assert result.by_feature[feat_rule] == Decimal("60.0000")
    assert result.by_feature[feat_wl] == Decimal("120.5000")

    # Check unallocated breakdown
    assert result.total_unallocated_amount == Decimal("125.2500")  # 40 (remainder) + 85.25 (no rule)
    assert len(result.unallocated_items) == 2

    # Verify summary dict
    summary = result.summary()
    assert summary["is_reconciled"] is True
    assert summary["total_source_amount"] == "505.7500"
    assert summary["total_allocated_amount"] == "380.5000"
    assert summary["total_unallocated_amount"] == "125.2500"
