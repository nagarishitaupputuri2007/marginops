"""High-precision engine fusing PostgreSQL infrastructure costs with MongoDB telemetry."""
import math
import uuid
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Sequence, Union

from app.models.enums import UnitMetricType
from app.schemas.telemetry import TelemetryEvent, TelemetryStatus
from app.services.cost_attribution.models import TenantIsolationError
from app.services.unit_economics.models import (
    FeatureGrossMargin,
    MarginHealthStatus,
    TelemetryAggregate,
    UnitCostCalculation,
    UnitCostStatus,
    UnitEconomicsReport,
)


class UnitEconomicsEngine:
    """Production-grade calculation engine for Product Economics and Telemetry Fusion.

    Fuses financial cost allocations with operational usage data to derive:
    - Cost per 1,000 API Requests ($/kReq)
    - Cost per 1,000,000 AI Tokens ($/MTok) split by prompt, completion, and blended
    - Feature Gross Margin compliance against strategic targets
    - Waste detection (idle infrastructure with zero throughput)
    """

    def __init__(
        self,
        cost_precision: Decimal = Decimal("0.0001"),
        unit_cost_precision: Decimal = Decimal("0.000001"),
        strict_tenant_isolation: bool = True,
    ):
        """Initializes the unit economics engine.

        Args:
            cost_precision: Monetary precision for financial aggregations (0.0001).
            unit_cost_precision: High-precision quantum for micro-unit costs (0.000001).
            strict_tenant_isolation: If True, raises TenantIsolationError on foreign tenant data.
        """
        self.cost_precision = cost_precision
        self.unit_cost_precision = unit_cost_precision
        self.strict_tenant_isolation = strict_tenant_isolation

    def aggregate_telemetry_events(
        self,
        organization_id: uuid.UUID,
        events: Sequence[Union[TelemetryEvent, Dict[str, Any]]],
    ) -> Dict[Optional[uuid.UUID], TelemetryAggregate]:
        """Aggregates raw MongoDB telemetry events into operational metrics grouped by feature.

        Args:
            organization_id: Expected tenant organization boundary UUID.
            events: Sequence of TelemetryEvent instances or MongoDB BSON dictionaries.

        Returns:
            Dictionary mapping feature UUID (or None for unmapped) to TelemetryAggregate.
        """
        grouped: Dict[Optional[uuid.UUID], Dict[str, Any]] = {}

        for ev in events:
            # Extract fields whether dict or TelemetryEvent
            if isinstance(ev, dict):
                ev_org_str = str(ev.get("organization_id", ""))
                feat_raw = ev.get("product_feature_id")
                feat_id = uuid.UUID(str(feat_raw)) if feat_raw else None
                status_raw = str(ev.get("status", "success")).lower()
                latency = ev.get("latency_ms")
                tokens_raw = ev.get("tokens") or {}
                prompt_tok = tokens_raw.get("prompt_tokens", 0) if isinstance(tokens_raw, dict) else 0
                comp_tok = tokens_raw.get("completion_tokens", 0) if isinstance(tokens_raw, dict) else 0
                total_tok = tokens_raw.get("total_tokens") or (prompt_tok + comp_tok)
                ai_model = ev.get("ai_model")
                attrs = ev.get("attributes") or {}
                sub_tenant = attrs.get("tenant_id") or attrs.get("customer_id")
            else:
                ev_org_str = str(ev.organization_id)
                feat_id = ev.product_feature_id
                status_raw = ev.status.value if isinstance(ev.status, TelemetryStatus) else str(ev.status).lower()
                latency = ev.latency_ms
                prompt_tok = ev.tokens.prompt_tokens if ev.tokens else 0
                comp_tok = ev.tokens.completion_tokens if ev.tokens else 0
                total_tok = ev.tokens.total_tokens if ev.tokens else (prompt_tok + comp_tok)
                ai_model = ev.ai_model
                sub_tenant = ev.attributes.get("tenant_id") or ev.attributes.get("customer_id")

            # Enforce multi-tenant isolation
            if ev_org_str != str(organization_id):
                if self.strict_tenant_isolation:
                    raise TenantIsolationError(
                        f"Tenant isolation breach: Telemetry event belongs to org {ev_org_str}, "
                        f"expected {organization_id}."
                    )
                continue

            if feat_id not in grouped:
                grouped[feat_id] = {
                    "product_feature_id": feat_id,
                    "request_count": 0,
                    "success_count": 0,
                    "error_count": 0,
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                    "latencies": [],
                    "sub_tenants": set(),
                    "by_model": {},
                }

            entry = grouped[feat_id]
            entry["request_count"] += 1

            if status_raw == "success":
                entry["success_count"] += 1
            elif status_raw in ("error", "timeout", "rate_limited"):
                entry["error_count"] += 1

            entry["prompt_tokens"] += prompt_tok
            entry["completion_tokens"] += comp_tok
            entry["total_tokens"] += total_tok

            if latency is not None:
                entry["latencies"].append(float(latency))

            if sub_tenant:
                entry["sub_tenants"].add(str(sub_tenant))

            if ai_model:
                m_entry = entry["by_model"].setdefault(
                    ai_model,
                    {"requests": 0, "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                )
                m_entry["requests"] += 1
                m_entry["prompt_tokens"] += prompt_tok
                m_entry["completion_tokens"] += comp_tok
                m_entry["total_tokens"] += total_tok

        # Transform raw lists into TelemetryAggregate models
        result: Dict[Optional[uuid.UUID], TelemetryAggregate] = {}
        for feat_id, d in grouped.items():
            lats = d["latencies"]
            avg_lat = sum(lats) / len(lats) if lats else None
            p95_lat = None
            if lats:
                sorted_lats = sorted(lats)
                idx = int(math.ceil(0.95 * len(sorted_lats))) - 1
                p95_lat = sorted_lats[max(0, idx)]

            tenant_cnt = max(1, len(d["sub_tenants"]))

            result[feat_id] = TelemetryAggregate(
                product_feature_id=feat_id,
                request_count=d["request_count"],
                success_count=d["success_count"],
                error_count=d["error_count"],
                prompt_tokens=d["prompt_tokens"],
                completion_tokens=d["completion_tokens"],
                total_tokens=d["total_tokens"],
                avg_latency_ms=round(avg_lat, 2) if avg_lat is not None else None,
                p95_latency_ms=round(p95_lat, 2) if p95_lat is not None else None,
                active_tenants_count=tenant_cnt,
                by_model=d["by_model"],
            )

        return result

    def calculate_unit_cost(
        self,
        organization_id: uuid.UUID,
        metric_type: UnitMetricType,
        total_cost: Decimal,
        raw_usage: Decimal,
        unit_name: str,
        scaling_factor: int = 1000,
        target_cost_per_unit: Optional[Decimal] = None,
        product_feature_id: Optional[uuid.UUID] = None,
        feature_name: Optional[str] = None,
    ) -> UnitCostCalculation:
        """Calculates normalized unit cost with defensive handling of idle waste and zero throughput."""
        dec_factor = Decimal(str(scaling_factor))
        scaled_units = (raw_usage / dec_factor) if dec_factor > Decimal("0") else raw_usage

        # Zero traffic but positive cost -> Idle Infrastructure Waste
        if raw_usage <= Decimal("0") and total_cost > Decimal("0"):
            return UnitCostCalculation(
                organization_id=organization_id,
                product_feature_id=product_feature_id,
                feature_name=feature_name,
                metric_type=metric_type,
                unit_name=unit_name,
                total_allocated_cost=total_cost.quantize(self.cost_precision),
                total_usage_units=raw_usage,
                scaling_factor=scaling_factor,
                scaled_units=scaled_units,
                unit_cost=None,
                target_cost_per_unit=target_cost_per_unit,
                cost_variance_percent=None,
                status=UnitCostStatus.ZERO_TRAFFIC_IDLE_WASTE,
            )

        # Usage observed with zero cost -> Unbilled / Free Tier
        if raw_usage > Decimal("0") and total_cost == Decimal("0"):
            return UnitCostCalculation(
                organization_id=organization_id,
                product_feature_id=product_feature_id,
                feature_name=feature_name,
                metric_type=metric_type,
                unit_name=unit_name,
                total_allocated_cost=Decimal("0.0000"),
                total_usage_units=raw_usage,
                scaling_factor=scaling_factor,
                scaled_units=scaled_units,
                unit_cost=Decimal("0.000000"),
                target_cost_per_unit=target_cost_per_unit,
                cost_variance_percent=Decimal("-100.00") if target_cost_per_unit else None,
                status=UnitCostStatus.ZERO_COST_UNBILLED,
            )

        # Zero usage and zero cost -> Undefined
        if raw_usage <= Decimal("0") and total_cost == Decimal("0"):
            return UnitCostCalculation(
                organization_id=organization_id,
                product_feature_id=product_feature_id,
                feature_name=feature_name,
                metric_type=metric_type,
                unit_name=unit_name,
                total_allocated_cost=Decimal("0.0000"),
                total_usage_units=Decimal("0"),
                scaling_factor=scaling_factor,
                scaled_units=Decimal("0"),
                unit_cost=None,
                target_cost_per_unit=target_cost_per_unit,
                cost_variance_percent=None,
                status=UnitCostStatus.UNDEFINED,
            )

        # Standard calculation: (Total Cost * Scaling Factor) / Raw Usage
        exact_unit_cost = (total_cost * dec_factor) / raw_usage
        unit_cost = exact_unit_cost.quantize(self.unit_cost_precision, rounding=ROUND_HALF_UP)

        variance_pct: Optional[Decimal] = None
        status = UnitCostStatus.OPTIMAL

        if target_cost_per_unit is not None and target_cost_per_unit > Decimal("0"):
            var_exact = ((unit_cost - target_cost_per_unit) / target_cost_per_unit) * Decimal("100.00")
            variance_pct = var_exact.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            if unit_cost > target_cost_per_unit:
                status = UnitCostStatus.ELEVATED

        return UnitCostCalculation(
            organization_id=organization_id,
            product_feature_id=product_feature_id,
            feature_name=feature_name,
            metric_type=metric_type,
            unit_name=unit_name,
            total_allocated_cost=total_cost.quantize(self.cost_precision),
            total_usage_units=raw_usage,
            scaling_factor=scaling_factor,
            scaled_units=scaled_units.quantize(Decimal("0.0001")),
            unit_cost=unit_cost,
            target_cost_per_unit=target_cost_per_unit,
            cost_variance_percent=variance_pct,
            status=status,
        )

    def calculate_feature_margin(
        self,
        organization_id: uuid.UUID,
        feature_id: uuid.UUID,
        feature_name: str,
        feature_slug: str,
        tier: str,
        target_gross_margin_percent: Decimal,
        cogs_cost: Decimal,
        revenue: Decimal = Decimal("0.00"),
    ) -> FeatureGrossMargin:
        """Calculates product feature gross margin and validates strategic compliance."""
        gross_profit = revenue - cogs_cost

        # Case 1: Zero revenue
        if revenue <= Decimal("0"):
            if revenue == Decimal("0") and cogs_cost > Decimal("0"):
                status = MarginHealthStatus.NO_REVENUE
            elif revenue == Decimal("0") and cogs_cost <= Decimal("0"):
                status = MarginHealthStatus.HEALTHY
            else:
                status = MarginHealthStatus.NEGATIVE_MARGIN

            return FeatureGrossMargin(
                organization_id=organization_id,
                product_feature_id=feature_id,
                feature_name=feature_name,
                feature_slug=feature_slug,
                tier=tier,
                target_gross_margin_percent=target_gross_margin_percent,
                revenue=revenue.quantize(Decimal("0.01")),
                cogs_cost=cogs_cost.quantize(self.cost_precision),
                gross_profit=gross_profit.quantize(self.cost_precision),
                actual_gross_margin_percent=None,
                margin_delta_percent=None,
                status=status,
            )

        # Case 2: Positive revenue -> compute percentage
        actual_margin = ((gross_profit / revenue) * Decimal("100.00")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        delta_pct = (actual_margin - target_gross_margin_percent).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        if actual_margin < Decimal("0"):
            status = MarginHealthStatus.NEGATIVE_MARGIN
        elif delta_pct < Decimal("-15.00"):
            status = MarginHealthStatus.CRITICAL
        elif delta_pct < Decimal("0.00"):
            status = MarginHealthStatus.WARNING
        else:
            status = MarginHealthStatus.HEALTHY

        return FeatureGrossMargin(
            organization_id=organization_id,
            product_feature_id=feature_id,
            feature_name=feature_name,
            feature_slug=feature_slug,
            tier=tier,
            target_gross_margin_percent=target_gross_margin_percent,
            revenue=revenue.quantize(Decimal("0.01")),
            cogs_cost=cogs_cost.quantize(self.cost_precision),
            gross_profit=gross_profit.quantize(Decimal("0.01")),
            actual_gross_margin_percent=actual_margin,
            margin_delta_percent=delta_pct,
            status=status,
        )

    def fuse_costs_and_telemetry(
        self,
        organization_id: uuid.UUID,
        attributed_costs_by_feature: Dict[uuid.UUID, Decimal],
        telemetry_events: Sequence[Union[TelemetryEvent, Dict[str, Any]]],
        features: Sequence[Any],
        feature_revenues: Optional[Dict[uuid.UUID, Decimal]] = None,
        unit_metric_targets: Optional[Dict[uuid.UUID, Dict[UnitMetricType, Decimal]]] = None,
        time_window_start: Optional[datetime] = None,
        time_window_end: Optional[datetime] = None,
    ) -> UnitEconomicsReport:
        """Fuses financial costs and operational telemetry into an executive Unit Economics Report.

        Args:
            organization_id: Tenant organization boundary UUID.
            attributed_costs_by_feature: Mapping of ProductFeature UUID -> attributed infrastructure cost.
            telemetry_events: Collection of TelemetryEvent instances.
            features: Collection of ProductFeature domain models or dicts.
            feature_revenues: Optional mapping of feature UUID -> gross revenue.
            unit_metric_targets: Optional mapping of feature UUID -> {UnitMetricType -> budgeted target}.
            time_window_start: Optional evaluation period start.
            time_window_end: Optional evaluation period end.

        Returns:
            UnitEconomicsReport with unit metrics, margin scorecards, and executive summaries.
        """
        # Step 1: Aggregate telemetry by feature
        telemetry_by_feature = self.aggregate_telemetry_events(organization_id, telemetry_events)

        feature_lookup: Dict[uuid.UUID, Any] = {}
        for f in features:
            f_id = getattr(f, "id", None) or (uuid.UUID(str(f["id"])) if "id" in f else None)
            if f_id:
                feature_lookup[f_id] = f

        metrics: List[UnitCostCalculation] = []
        margins: List[FeatureGrossMargin] = []

        total_attributed_cost = Decimal("0.0000")
        total_revenue = Decimal("0.00")
        total_requests = 0
        total_tokens = 0

        # Step 2: Iterate all known product features
        for f_id, feat in feature_lookup.items():
            f_name = getattr(feat, "name", None) or feat.get("name", "Unknown Feature")
            f_slug = getattr(feat, "slug", None) or feat.get("slug", "unknown")
            f_tier = getattr(feat, "tier", None) or feat.get("tier", "core")
            target_margin = getattr(feat, "target_gross_margin_percent", None) or feat.get(
                "target_gross_margin_percent", Decimal("75.00")
            )
            if not isinstance(target_margin, Decimal):
                target_margin = Decimal(str(target_margin))

            cost = attributed_costs_by_feature.get(f_id, Decimal("0.0000"))
            total_attributed_cost += cost

            rev = (feature_revenues.get(f_id, Decimal("0.00")) if feature_revenues else Decimal("0.00"))
            total_revenue += rev

            # Evaluate Feature Gross Margin
            margin_scorecard = self.calculate_feature_margin(
                organization_id=organization_id,
                feature_id=f_id,
                feature_name=f_name,
                feature_slug=f_slug,
                tier=f_tier,
                target_gross_margin_percent=target_margin,
                cogs_cost=cost,
                revenue=rev,
            )
            margins.append(margin_scorecard)

            # Retrieve telemetry aggregate for this feature
            telem = telemetry_by_feature.get(f_id)
            req_count = telem.request_count if telem else 0
            tok_count = telem.total_tokens if telem else 0
            total_requests += req_count
            total_tokens += tok_count

            targets_for_feat = (unit_metric_targets.get(f_id, {}) if unit_metric_targets else {})

            # Metric 1: Cost per 1k API Requests
            req_target = targets_for_feat.get(UnitMetricType.REQUEST_COUNT)
            req_calc = self.calculate_unit_cost(
                organization_id=organization_id,
                metric_type=UnitMetricType.REQUEST_COUNT,
                total_cost=cost,
                raw_usage=Decimal(str(req_count)),
                unit_name="1k_requests",
                scaling_factor=1000,
                target_cost_per_unit=req_target,
                product_feature_id=f_id,
                feature_name=f_name,
            )
            metrics.append(req_calc)

            # Metric 2: Cost per 1M AI Tokens (if tokens observed or AI feature)
            if tok_count > 0 or telem and (telem.prompt_tokens > 0 or telem.completion_tokens > 0):
                tok_target = targets_for_feat.get(UnitMetricType.AI_TOKEN)
                tok_calc = self.calculate_unit_cost(
                    organization_id=organization_id,
                    metric_type=UnitMetricType.AI_TOKEN,
                    total_cost=cost,
                    raw_usage=Decimal(str(tok_count)),
                    unit_name="1m_tokens",
                    scaling_factor=1000000,
                    target_cost_per_unit=tok_target,
                    product_feature_id=f_id,
                    feature_name=f_name,
                )
                metrics.append(tok_calc)

        # Step 3: Compute blended platform gross margin
        overall_margin: Optional[Decimal] = None
        if total_revenue > Decimal("0"):
            overall_profit = total_revenue - total_attributed_cost
            overall_margin = ((overall_profit / total_revenue) * Decimal("100.00")).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )

        return UnitEconomicsReport(
            organization_id=organization_id,
            generated_at=datetime.now(timezone.utc),
            time_window_start=time_window_start,
            time_window_end=time_window_end,
            total_attributed_cost=total_attributed_cost.quantize(self.cost_precision),
            total_revenue=total_revenue.quantize(Decimal("0.01")),
            overall_gross_margin_percent=overall_margin,
            total_requests=total_requests,
            total_tokens=total_tokens,
            metrics=metrics,
            margins=margins,
        )
