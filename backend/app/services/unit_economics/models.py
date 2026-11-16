"""Data models, enums, and calculation contracts for Product Unit Economics."""
import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import UnitMetricType


class MarginHealthStatus(str, enum.Enum):
    """Classification of feature margin compliance against product targets."""
    HEALTHY = "HEALTHY"            # Actual margin >= Target margin
    WARNING = "WARNING"            # Target - 15% <= Actual < Target
    CRITICAL = "CRITICAL"          # Actual < Target - 15%
    NEGATIVE_MARGIN = "NEGATIVE"   # Cost exceeds Revenue (burning cash)
    NO_REVENUE = "NO_REVENUE"      # Cost exists with no assigned revenue


class UnitCostStatus(str, enum.Enum):
    """Operational status of unit economic cost efficiency."""
    OPTIMAL = "OPTIMAL"                        # Below or equal to target unit cost
    ELEVATED = "ELEVATED"                      # Above target unit cost
    ZERO_TRAFFIC_IDLE_WASTE = "IDLE_WASTE"     # Cost incurred with zero traffic/requests
    ZERO_COST_UNBILLED = "ZERO_COST_UNBILLED"  # Requests processed with zero infrastructure cost
    UNDEFINED = "UNDEFINED"                    # Zero traffic and zero cost


class TelemetryAggregate(BaseModel):
    """Aggregated operational telemetry metrics over a specified time window."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    product_feature_id: Optional[uuid.UUID] = Field(default=None, description="Feature UUID if mapped")
    request_count: int = Field(default=0, ge=0, description="Total API / inference requests")
    success_count: int = Field(default=0, ge=0, description="Successful requests")
    error_count: int = Field(default=0, ge=0, description="Failed / error requests")
    prompt_tokens: int = Field(default=0, ge=0, description="Total input/prompt tokens consumed")
    completion_tokens: int = Field(default=0, ge=0, description="Total output/completion tokens consumed")
    total_tokens: int = Field(default=0, ge=0, description="Total tokens consumed")
    avg_latency_ms: Optional[float] = Field(default=None, ge=0.0, description="Average request latency in ms")
    p95_latency_ms: Optional[float] = Field(default=None, ge=0.0, description="95th percentile latency in ms")
    active_tenants_count: int = Field(default=1, ge=0, description="Number of distinct tenants/customers observed")
    by_model: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Detailed breakdown by AI model checkpoint (e.g., gpt-4o, claude-3-5-sonnet)",
    )


class UnitCostCalculation(BaseModel):
    """Normalized unit economic calculation for a single product driver."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, description="Unique calculation identifier")
    organization_id: uuid.UUID = Field(..., description="Organization boundary UUID")
    product_feature_id: Optional[uuid.UUID] = Field(default=None, description="Associated ProductFeature UUID")
    feature_name: Optional[str] = Field(default=None, description="Human-readable feature name")
    metric_type: UnitMetricType = Field(..., description="Type of unit economic driver")
    unit_name: str = Field(..., description="Measurement unit (e.g., 1k_requests, 1m_tokens)")
    
    # Financial inputs & outputs
    total_allocated_cost: Decimal = Field(..., description="Total COGS infrastructure cost in USD")
    total_usage_units: Decimal = Field(..., description="Raw usage quantity (e.g. raw requests or raw tokens)")
    scaling_factor: int = Field(default=1, description="Scaling factor (e.g., 1,000 for kReq, 1,000,000 for MTok)")
    scaled_units: Decimal = Field(..., description="Normalized usage units (total_usage_units / scaling_factor)")
    unit_cost: Optional[Decimal] = Field(
        default=None,
        description="Calculated cost per scaled unit in USD. None if usage is zero.",
    )
    target_cost_per_unit: Optional[Decimal] = Field(
        default=None,
        description="Budgeted target unit cost from UnitMetric definition",
    )
    cost_variance_percent: Optional[Decimal] = Field(
        default=None,
        description="Percentage deviation from target: ((unit_cost - target) / target) * 100",
    )
    currency: str = Field(default="USD", description="Currency code")
    status: UnitCostStatus = Field(default=UnitCostStatus.OPTIMAL, description="Operational cost health status")


class FeatureGrossMargin(BaseModel):
    """Gross margin calculation and health tracking for a product feature."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    organization_id: uuid.UUID = Field(..., description="Organization boundary UUID")
    product_feature_id: uuid.UUID = Field(..., description="ProductFeature UUID")
    feature_name: str = Field(..., description="Human-readable feature name")
    feature_slug: str = Field(..., description="URL/code slug for the feature")
    tier: str = Field(default="core", description="Feature tier (core, enterprise, experimental)")
    
    # Margin Economics
    target_gross_margin_percent: Decimal = Field(
        default=Decimal("75.00"),
        description="Target gross margin percentage from product strategy",
    )
    revenue: Decimal = Field(
        default=Decimal("0.00"),
        description="Actual gross revenue attributed to this feature",
    )
    cogs_cost: Decimal = Field(
        ...,
        description="Total attributed infrastructure expenditure (COGS)",
    )
    gross_profit: Decimal = Field(
        ...,
        description="Gross profit = Revenue - COGS Cost",
    )
    actual_gross_margin_percent: Optional[Decimal] = Field(
        default=None,
        description="Actual gross margin percentage = (Gross Profit / Revenue) * 100",
    )
    margin_delta_percent: Optional[Decimal] = Field(
        default=None,
        description="Variance from target = Actual Margin % - Target Margin %",
    )
    status: MarginHealthStatus = Field(..., description="Margin compliance status")
    currency: str = Field(default="USD", description="Currency code")


class UnitEconomicsReport(BaseModel):
    """Comprehensive executive and engineering audit of product unit economics."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    organization_id: uuid.UUID = Field(..., description="Tenant organization UUID")
    generated_at: datetime = Field(..., description="UTC timestamp of report generation")
    time_window_start: Optional[datetime] = Field(default=None, description="Start of evaluated time range")
    time_window_end: Optional[datetime] = Field(default=None, description="End of evaluated time range")
    
    # Global totals
    total_attributed_cost: Decimal = Field(default=Decimal("0.0000"), description="Total infrastructure COGS")
    total_revenue: Decimal = Field(default=Decimal("0.00"), description="Total revenue mapped")
    overall_gross_margin_percent: Optional[Decimal] = Field(default=None, description="Blended platform gross margin")
    total_requests: int = Field(default=0, description="Total API / inference operations evaluated")
    total_tokens: int = Field(default=0, description="Total AI tokens consumed across all features")
    
    # Granular items
    metrics: List[UnitCostCalculation] = Field(default_factory=list, description="Computed unit cost drivers")
    margins: List[FeatureGrossMargin] = Field(default_factory=list, description="Feature margin health scorecards")

    def summary(self) -> Dict[str, Any]:
        """Produces a clean executive summary dictionary."""
        return {
            "organization_id": str(self.organization_id),
            "generated_at": self.generated_at.isoformat(),
            "total_attributed_cost": f"{self.total_attributed_cost:.4f}",
            "total_revenue": f"{self.total_revenue:.2f}",
            "overall_gross_margin_percent": (
                f"{self.overall_gross_margin_percent:.2f}%"
                if self.overall_gross_margin_percent is not None
                else "N/A"
            ),
            "total_requests": self.total_requests,
            "total_tokens": self.total_tokens,
            "metrics_count": len(self.metrics),
            "features_evaluated": len(self.margins),
            "healthy_features": len([m for m in self.margins if m.status == MarginHealthStatus.HEALTHY]),
            "warning_features": len([m for m in self.margins if m.status == MarginHealthStatus.WARNING]),
            "critical_features": len([
                m for m in self.margins
                if m.status in (MarginHealthStatus.CRITICAL, MarginHealthStatus.NEGATIVE_MARGIN)
            ]),
        }
