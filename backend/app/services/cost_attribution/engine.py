"""Deterministic Cost Attribution Engine for multi-cloud infrastructure expenditures.

Enforces direct attribution, rule-based shared allocations, exact Decimal accounting,
negative credit preservation, tenant isolation, and Largest Remainder penny distribution.
"""
import uuid
from decimal import Decimal, ROUND_FLOOR, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple, Union

from app.models.enums import AllocationRuleType, AllocationTargetType, CloudProvider
from app.services.cost_attribution.models import (
    AttributedCostItem,
    AttributionMethod,
    AttributionResult,
    CostAttributionError,
    InvalidAllocationRuleError,
    ReconciliationError,
    TenantIsolationError,
    UnallocatedReason,
)


def distribute_amount_by_weights(
    amount: Decimal,
    weights: Sequence[Decimal],
    precision: Decimal = Decimal("0.0001"),
) -> List[Decimal]:
    """Distributes an amount proportionally according to weights using the Largest Remainder Method.

    Guarantees sum(result) == amount down to the exact precision quantum, preserving signs for
    credits and refunds with zero penny/sub-cent leakage.

    Args:
        amount: Exact Decimal amount to distribute (positive, negative, or zero).
        weights: Sequence of positive weights (proportions or percentages).
        precision: Quantization quantum (e.g., Decimal("0.0001") or Decimal("0.01")).

    Returns:
        List of Decimal amounts whose sum equals `amount` exactly.
    """
    if not weights:
        return []

    total_weight = sum(weights)
    if total_weight <= Decimal("0"):
        raise ValueError("Total weight must be strictly positive")

    if amount == Decimal("0"):
        return [Decimal("0").quantize(precision)] * len(weights)

    is_negative = amount < Decimal("0")
    abs_amount = abs(amount)

    # Compute unrounded theoretical shares
    exact_shares = [(abs_amount * w) / total_weight for w in weights]

    # Floor base shares to precision quantum
    base_shares = [s.quantize(precision, rounding=ROUND_FLOOR) for s in exact_shares]
    remainder_to_distribute = abs_amount - sum(base_shares)

    # Number of quanta needed to reconcile remainder
    quanta_to_distribute = int(
        (remainder_to_distribute / precision).to_integral_exact(rounding=ROUND_HALF_UP)
    )

    # Sort remainders descending by fractional magnitude, using original index as stable tie-breaker
    fractional_remainders = [
        (exact_shares[i] - base_shares[i], i) for i in range(len(weights))
    ]
    fractional_remainders.sort(key=lambda item: (item[0], -item[1]), reverse=True)

    final_shares = list(base_shares)
    for k in range(quanta_to_distribute):
        idx = fractional_remainders[k % len(fractional_remainders)][1]
        final_shares[idx] += precision

    if is_negative:
        return [-share for share in final_shares]
    return final_shares


class CostAttributionEngine:
    """Modular, deterministic calculation engine for infrastructure cost attribution.

    Decoupled from database sessions and HTTP frameworks to allow pure in-memory execution,
    streaming batch processing, and offline auditing.
    """

    def __init__(
        self,
        precision: Decimal = Decimal("0.0001"),
        amount_field: str = "billing_amount",
        strict_tenant_isolation: bool = True,
    ):
        """Initializes the attribution engine.

        Args:
            precision: Monetary quantum for calculations (default 0.0001 matching Numeric(18, 4)).
            amount_field: Attribute name to extract from records ('billing_amount' or 'cost').
            strict_tenant_isolation: If True, raises TenantIsolationError on tenant mismatches;
                                     if False, preserves mismatched items as UNALLOCATED.
        """
        self.precision = precision
        self.amount_field = amount_field
        self.strict_tenant_isolation = strict_tenant_isolation

    def _extract_record_attributes(self, record: Any) -> Dict[str, Any]:
        """Extracts normalized billing fields from SQLAlchemy models, Pydantic schemas, or dicts."""
        if isinstance(record, dict):
            org_id = record.get("organization_id")
            if isinstance(org_id, str):
                org_id = uuid.UUID(org_id)

            feat_id = record.get("product_feature_id")
            if isinstance(feat_id, str) and feat_id:
                try:
                    feat_id = uuid.UUID(feat_id)
                except ValueError:
                    feat_id = None

            raw_amount = record.get(self.amount_field)
            if raw_amount is None and self.amount_field != "cost":
                raw_amount = record.get("cost", Decimal("0"))
            amount = Decimal(str(raw_amount)) if raw_amount is not None else Decimal("0")

            provider = record.get("cloud_provider")
            if isinstance(provider, CloudProvider):
                provider_str = provider.value
            else:
                provider_str = str(provider) if provider else None

            is_credit = bool(record.get("is_credit", amount < Decimal("0")))

            return {
                "id": record.get("id"),
                "organization_id": org_id,
                "billing_date": record.get("billing_date"),
                "cloud_provider": provider_str,
                "service_id": record.get("service_id", ""),
                "resource_id": record.get("resource_id", ""),
                "amount": amount.quantize(self.precision),
                "product_feature_id": feat_id,
                "workload_id": record.get("workload_id"),
                "resource_tags": record.get("resource_tags", {}) or {},
                "currency": record.get("currency", "USD"),
                "is_credit": is_credit,
            }

        # Object / SQLAlchemy / Pydantic model
        org_id = getattr(record, "organization_id", None)
        if isinstance(org_id, str):
            org_id = uuid.UUID(org_id)

        feat_id = getattr(record, "product_feature_id", None)
        if isinstance(feat_id, str) and feat_id:
            try:
                feat_id = uuid.UUID(feat_id)
            except ValueError:
                feat_id = None

        raw_amount = getattr(record, self.amount_field, None)
        if raw_amount is None and self.amount_field != "cost":
            raw_amount = getattr(record, "cost", Decimal("0"))
        amount = Decimal(str(raw_amount)) if raw_amount is not None else Decimal("0")

        provider = getattr(record, "cloud_provider", None)
        if isinstance(provider, CloudProvider):
            provider_str = provider.value
        else:
            provider_str = str(provider) if provider else None

        is_credit = bool(getattr(record, "is_credit", amount < Decimal("0")))

        return {
            "id": getattr(record, "id", None),
            "organization_id": org_id,
            "billing_date": getattr(record, "billing_date", None),
            "cloud_provider": provider_str,
            "service_id": getattr(record, "service_id", ""),
            "resource_id": getattr(record, "resource_id", ""),
            "amount": amount.quantize(self.precision),
            "product_feature_id": feat_id,
            "workload_id": getattr(record, "workload_id", None),
            "resource_tags": getattr(record, "resource_tags", {}) or {},
            "currency": getattr(record, "currency", "USD"),
            "is_credit": is_credit,
        }

    def _matches_rule(self, rule: Any, resource_tags: Dict[str, Any]) -> bool:
        """Determines if a resource's tags satisfy an allocation rule's criteria."""
        rule_type = getattr(rule, "rule_type", None)
        if isinstance(rule_type, str):
            try:
                rule_type = AllocationRuleType(rule_type)
            except ValueError:
                return False

        tag_key = getattr(rule, "tag_key", None)
        tag_value = getattr(rule, "tag_value", None)

        # Rules without tag criteria match unconditionally for their tier
        if not tag_key and not tag_value:
            return True

        if not tag_key or tag_key not in resource_tags:
            return False

        val_in_resource = str(resource_tags[tag_key])

        if rule_type == AllocationRuleType.TAG_EXACT:
            return val_in_resource == str(tag_value)
        elif rule_type == AllocationRuleType.TAG_PREFIX:
            return val_in_resource.startswith(str(tag_value))
        elif rule_type in (AllocationRuleType.FIXED_PERCENTAGE, AllocationRuleType.USAGE_PROPORTIONAL):
            # If tags are specified on fixed/usage rules, require exact tag match
            return val_in_resource == str(tag_value)

        return False

    def attribute_record(
        self,
        record: Any,
        rules: Optional[Sequence[Any]] = None,
        valid_feature_ids: Optional[Set[uuid.UUID]] = None,
        valid_cost_center_ids: Optional[Set[uuid.UUID]] = None,
        workload_mapping: Optional[Dict[str, Dict[str, Any]]] = None,
        usage_weights: Optional[Dict[uuid.UUID, Decimal]] = None,
    ) -> List[AttributedCostItem]:
        """Attributes a single infrastructure cost record into one or more AttributedCostItems.

        Follows deterministic attribution hierarchy:
        1. Direct product feature attribution (if present and tenant-valid).
        2. Direct workload mapping attribution (if mapped and tenant-valid).
        3. Priority-ordered AllocationRule matching (TAG_EXACT, TAG_PREFIX, FIXED_PERCENTAGE, USAGE_PROPORTIONAL).
        4. Residual or unmatchable costs preserved as UNALLOCATED with full diagnostic reason.

        Args:
            record: CostRecord instance, ParsedBillingRecord, or dict.
            rules: Sequence of active AllocationRule instances for the organization.
            valid_feature_ids: Set of valid ProductFeature UUIDs belonging to this organization.
            valid_cost_center_ids: Set of valid CostCenter UUIDs belonging to this organization.
            workload_mapping: Optional mapping of workload_id -> {target_type, target_id, organization_id, ...}.
            usage_weights: Target or rule UUID -> usage weight for USAGE_PROPORTIONAL allocations.

        Returns:
            List of AttributedCostItem whose sum of allocated_amount equals record amount.
        """
        rec = self._extract_record_attributes(record)
        org_id = rec["organization_id"]
        amount = rec["amount"]
        is_credit = rec["is_credit"]
        currency = rec["currency"]

        base_item_kwargs = {
            "cost_record_id": rec["id"],
            "organization_id": org_id,
            "billing_date": rec["billing_date"],
            "cloud_provider": rec["cloud_provider"],
            "service_id": rec["service_id"],
            "resource_id": rec["resource_id"],
            "currency": currency,
            "is_credit": is_credit,
        }

        # -------------------------------------------------------------
        # Step 1: Direct Feature Attribution
        # -------------------------------------------------------------
        raw_feat_id = rec["product_feature_id"]
        if raw_feat_id is not None:
            # Check tenant boundary if valid features set is provided
            if valid_feature_ids is not None and raw_feat_id not in valid_feature_ids:
                if self.strict_tenant_isolation:
                    raise TenantIsolationError(
                        f"Cross-organization reference detected: ProductFeature {raw_feat_id} "
                        f"does not belong to Organization {org_id}."
                    )
                return [
                    AttributedCostItem(
                        **base_item_kwargs,
                        target_type=None,
                        target_id=None,
                        product_feature_id=None,
                        workload_id=rec["workload_id"],
                        attribution_method=AttributionMethod.UNALLOCATED,
                        allocation_percentage=Decimal("100.00"),
                        allocated_amount=amount,
                        is_allocated=False,
                        unallocated_reason=UnallocatedReason.CROSS_ORG_REFERENCE_REJECTED,
                    )
                ]

            return [
                AttributedCostItem(
                    **base_item_kwargs,
                    target_type=AllocationTargetType.PRODUCT_FEATURE,
                    target_id=raw_feat_id,
                    product_feature_id=raw_feat_id,
                    workload_id=rec["workload_id"],
                    attribution_method=AttributionMethod.DIRECT_FEATURE,
                    allocation_percentage=Decimal("100.00"),
                    allocated_amount=amount,
                    is_allocated=True,
                )
            ]

        # -------------------------------------------------------------
        # Step 2: Direct Workload Attribution
        # -------------------------------------------------------------
        workload_id = rec["workload_id"]
        if workload_id and workload_mapping and workload_id in workload_mapping:
            wl_info = workload_mapping[workload_id]
            wl_org_id = wl_info.get("organization_id")
            if wl_org_id and wl_org_id != org_id:
                if self.strict_tenant_isolation:
                    raise TenantIsolationError(
                        f"Cross-organization workload mapping detected for '{workload_id}'."
                    )
                return [
                    AttributedCostItem(
                        **base_item_kwargs,
                        target_type=None,
                        target_id=None,
                        workload_id=workload_id,
                        attribution_method=AttributionMethod.UNALLOCATED,
                        allocation_percentage=Decimal("100.00"),
                        allocated_amount=amount,
                        is_allocated=False,
                        unallocated_reason=UnallocatedReason.CROSS_ORG_REFERENCE_REJECTED,
                    )
                ]

            target_type = wl_info.get("target_type")
            target_id = wl_info.get("target_id")
            p_feat_id = wl_info.get("product_feature_id") or (
                target_id if target_type == AllocationTargetType.PRODUCT_FEATURE else None
            )
            c_center_id = wl_info.get("cost_center_id") or (
                target_id if target_type == AllocationTargetType.COST_CENTER else None
            )

            # Validate target boundary if lookups exist
            if p_feat_id and valid_feature_ids is not None and p_feat_id not in valid_feature_ids:
                if self.strict_tenant_isolation:
                    raise TenantIsolationError(f"Workload target feature {p_feat_id} not in org {org_id}.")
                return [
                    AttributedCostItem(
                        **base_item_kwargs,
                        workload_id=workload_id,
                        attribution_method=AttributionMethod.UNALLOCATED,
                        allocation_percentage=Decimal("100.00"),
                        allocated_amount=amount,
                        is_allocated=False,
                        unallocated_reason=UnallocatedReason.CROSS_ORG_REFERENCE_REJECTED,
                    )
                ]

            return [
                AttributedCostItem(
                    **base_item_kwargs,
                    target_type=target_type,
                    target_id=target_id,
                    product_feature_id=p_feat_id,
                    cost_center_id=c_center_id,
                    workload_id=workload_id,
                    attribution_method=AttributionMethod.DIRECT_WORKLOAD,
                    allocation_percentage=Decimal("100.00"),
                    allocated_amount=amount,
                    is_allocated=True,
                )
            ]

        # -------------------------------------------------------------
        # Step 3: Rule-Based Shared Allocation
        # -------------------------------------------------------------
        if rules:
            # Filter active rules belonging strictly to this organization
            org_rules = [
                r for r in rules
                if getattr(r, "is_active", True)
                and (getattr(r, "organization_id", org_id) == org_id)
            ]

            # Sort rules deterministically by priority ASC, name ASC, id ASC
            org_rules.sort(
                key=lambda r: (
                    getattr(r, "priority", 100),
                    getattr(r, "name", ""),
                    str(getattr(r, "id", "")),
                )
            )

            # Group rules by priority tier to evaluate in waterfall order
            priority_groups: Dict[int, List[Any]] = {}
            for r in org_rules:
                p = getattr(r, "priority", 100)
                priority_groups.setdefault(p, []).append(r)

            for priority in sorted(priority_groups.keys()):
                tier_rules = priority_groups[priority]
                matching_rules = [r for r in tier_rules if self._matches_rule(r, rec["resource_tags"])]

                if not matching_rules:
                    continue

                # Validate tenant targets of matching rules
                valid_matching_rules = []
                for mr in matching_rules:
                    r_target_type = getattr(mr, "target_type", None)
                    r_feat_id = getattr(mr, "product_feature_id", None)
                    r_cc_id = getattr(mr, "cost_center_id", None)

                    if (
                        r_feat_id
                        and valid_feature_ids is not None
                        and r_feat_id not in valid_feature_ids
                    ):
                        if self.strict_tenant_isolation:
                            raise TenantIsolationError(
                                f"Rule '{getattr(mr, 'name', '')}' targets cross-org feature {r_feat_id}."
                            )
                        continue

                    if (
                        r_cc_id
                        and valid_cost_center_ids is not None
                        and r_cc_id not in valid_cost_center_ids
                    ):
                        if self.strict_tenant_isolation:
                            raise TenantIsolationError(
                                f"Rule '{getattr(mr, 'name', '')}' targets cross-org cost center {r_cc_id}."
                            )
                        continue

                    valid_matching_rules.append(mr)

                if not valid_matching_rules:
                    continue

                # Check if this tier is USAGE_PROPORTIONAL
                has_usage_prop = any(
                    getattr(r, "rule_type", None) == AllocationRuleType.USAGE_PROPORTIONAL
                    for r in valid_matching_rules
                )

                if has_usage_prop:
                    # Allocate based on usage weights provided for targets
                    weights: List[Decimal] = []
                    target_rules: List[Any] = []
                    for mr in valid_matching_rules:
                        target_key = getattr(mr, "product_feature_id", None) or getattr(mr, "cost_center_id", None) or getattr(mr, "id", None)
                        w = usage_weights.get(target_key, Decimal("0")) if usage_weights else Decimal("0")
                        if w > Decimal("0"):
                            weights.append(Decimal(str(w)))
                            target_rules.append(mr)

                    if not weights or sum(weights) <= Decimal("0"):
                        # Cannot invent numbers when usage weights are missing
                        return [
                            AttributedCostItem(
                                **base_item_kwargs,
                                workload_id=rec["workload_id"],
                                attribution_method=AttributionMethod.UNALLOCATED,
                                allocation_percentage=Decimal("100.00"),
                                allocated_amount=amount,
                                is_allocated=False,
                                unallocated_reason=UnallocatedReason.MISSING_USAGE_WEIGHTS,
                            )
                        ]

                    shares = distribute_amount_by_weights(amount, weights, self.precision)
                    total_w = sum(weights)
                    items: List[AttributedCostItem] = []
                    for mr, share, w in zip(target_rules, shares, weights):
                        r_pct = ((w / total_w) * Decimal("100.00")).quantize(Decimal("0.01"))
                        t_type = getattr(mr, "target_type", None)
                        p_feat_id = getattr(mr, "product_feature_id", None)
                        c_center_id = getattr(mr, "cost_center_id", None)
                        t_id = p_feat_id or c_center_id

                        items.append(
                            AttributedCostItem(
                                **base_item_kwargs,
                                target_type=t_type,
                                target_id=t_id,
                                product_feature_id=p_feat_id,
                                cost_center_id=c_center_id,
                                workload_id=rec["workload_id"],
                                attribution_method=AttributionMethod.USAGE_PROPORTIONAL,
                                rule_id=getattr(mr, "id", None),
                                rule_name=getattr(mr, "name", None),
                                allocation_percentage=r_pct,
                                allocated_amount=share,
                                is_allocated=True,
                            )
                        )
                    return items

                # Otherwise, FIXED_PERCENTAGE or TAG rules with percentages
                weights: List[Decimal] = []
                assigned_rules: List[Any] = []
                remaining_pct_cap = Decimal("100.00")

                for mr in valid_matching_rules:
                    raw_pct = getattr(mr, "allocation_percentage", None)
                    if raw_pct is not None:
                        pct = Decimal(str(raw_pct))
                    else:
                        # Single matching rule with unspecified percentage implies 100%
                        pct = Decimal("100.00") if len(valid_matching_rules) == 1 else (Decimal("100.00") / Decimal(len(valid_matching_rules))).quantize(Decimal("0.01"))

                    # Defensive waterfall capping against duplicate / over-allocation
                    effective_pct = min(pct, remaining_pct_cap)
                    if effective_pct > Decimal("0"):
                        weights.append(effective_pct)
                        assigned_rules.append((mr, effective_pct))
                        remaining_pct_cap -= effective_pct

                total_allocated_pct = sum(weights)
                has_remainder = total_allocated_pct < Decimal("100.00")
                remainder_pct = Decimal("100.00") - total_allocated_pct

                if has_remainder:
                    weights_with_remainder = weights + [remainder_pct]
                else:
                    weights_with_remainder = weights

                shares = distribute_amount_by_weights(amount, weights_with_remainder, self.precision)
                items: List[AttributedCostItem] = []

                for (mr, eff_pct), share in zip(assigned_rules, shares[:len(assigned_rules)]):
                    rule_type = getattr(mr, "rule_type", None)
                    method = (
                        AttributionMethod(rule_type.value)
                        if isinstance(rule_type, AllocationRuleType)
                        else AttributionMethod.TAG_EXACT
                    )
                    t_type = getattr(mr, "target_type", None)
                    p_feat_id = getattr(mr, "product_feature_id", None)
                    c_center_id = getattr(mr, "cost_center_id", None)
                    t_id = p_feat_id or c_center_id

                    items.append(
                        AttributedCostItem(
                            **base_item_kwargs,
                            target_type=t_type,
                            target_id=t_id,
                            product_feature_id=p_feat_id,
                            cost_center_id=c_center_id,
                            workload_id=rec["workload_id"],
                            attribution_method=method,
                            rule_id=getattr(mr, "id", None),
                            rule_name=getattr(mr, "name", None),
                            allocation_percentage=eff_pct,
                            allocated_amount=share,
                            is_allocated=True,
                        )
                    )

                if has_remainder:
                    remainder_share = shares[-1]
                    items.append(
                        AttributedCostItem(
                            **base_item_kwargs,
                            workload_id=rec["workload_id"],
                            attribution_method=AttributionMethod.UNALLOCATED,
                            allocation_percentage=remainder_pct,
                            allocated_amount=remainder_share,
                            is_allocated=False,
                            unallocated_reason=UnallocatedReason.PARTIAL_ALLOCATION_REMAINDER,
                        )
                    )

                return items

        # -------------------------------------------------------------
        # Step 4: Residual Unallocated Preservation
        # -------------------------------------------------------------
        return [
            AttributedCostItem(
                **base_item_kwargs,
                workload_id=rec["workload_id"],
                attribution_method=AttributionMethod.UNALLOCATED,
                allocation_percentage=Decimal("100.00"),
                allocated_amount=amount,
                is_allocated=False,
                unallocated_reason=UnallocatedReason.NO_MATCHING_RULE,
            )
        ]

    def attribute_batch(
        self,
        organization_id: uuid.UUID,
        records: Sequence[Any],
        rules: Optional[Sequence[Any]] = None,
        valid_feature_ids: Optional[Set[uuid.UUID]] = None,
        valid_cost_center_ids: Optional[Set[uuid.UUID]] = None,
        workload_mapping: Optional[Dict[str, Dict[str, Any]]] = None,
        usage_weights: Optional[Dict[uuid.UUID, Decimal]] = None,
        reconcile: bool = True,
    ) -> AttributionResult:
        """Executes deterministic attribution over a batch of infrastructure cost records.

        Guarantees that total source amount == total allocated amount + total unallocated amount.

        Args:
            organization_id: Organization (tenant) UUID.
            records: Collection of CostRecords, ParsedBillingRecords, or dicts.
            rules: Active AllocationRules.
            valid_feature_ids: Set of valid ProductFeature UUIDs belonging to this organization.
            valid_cost_center_ids: Set of valid CostCenter UUIDs belonging to this organization.
            workload_mapping: Workload identifier to target mapping.
            usage_weights: Target or rule weights for USAGE_PROPORTIONAL allocations.
            reconcile: If True, raises ReconciliationError if financial conservation is violated.

        Returns:
            AttributionResult with aggregate statistics and itemized breakdown.
        """
        all_items: List[AttributedCostItem] = []
        total_source_amount = Decimal("0").quantize(self.precision)
        total_allocated_amount = Decimal("0").quantize(self.precision)
        total_unallocated_amount = Decimal("0").quantize(self.precision)

        for record in records:
            rec_attrs = self._extract_record_attributes(record)
            rec_org = rec_attrs["organization_id"]

            if rec_org != organization_id:
                if self.strict_tenant_isolation:
                    raise TenantIsolationError(
                        f"Record {rec_attrs['id']} belongs to organization {rec_org}, "
                        f"not the target batch organization {organization_id}."
                    )
                continue

            total_source_amount += rec_attrs["amount"]

            record_items = self.attribute_record(
                record=record,
                rules=rules,
                valid_feature_ids=valid_feature_ids,
                valid_cost_center_ids=valid_cost_center_ids,
                workload_mapping=workload_mapping,
                usage_weights=usage_weights,
            )

            for item in record_items:
                all_items.append(item)
                if item.is_allocated:
                    total_allocated_amount += item.allocated_amount
                else:
                    total_unallocated_amount += item.allocated_amount

        result = AttributionResult(
            organization_id=organization_id,
            total_source_records=len(records),
            total_source_amount=total_source_amount,
            total_allocated_items=len([i for i in all_items if i.is_allocated]),
            total_allocated_amount=total_allocated_amount,
            total_unallocated_items=len([i for i in all_items if not i.is_allocated]),
            total_unallocated_amount=total_unallocated_amount,
            items=all_items,
        )

        if reconcile:
            result.reconcile_or_raise()

        return result
