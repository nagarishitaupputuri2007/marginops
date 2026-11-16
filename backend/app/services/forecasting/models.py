"""Data contracts and schemas for Infrastructure Spend Forecasting."""
import uuid
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ForecastDataPoint(BaseModel):
    """Daily projected expenditure point with confidence intervals."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    forecast_date: date = Field(..., description="Projected calendar date")
    predicted_amount: Decimal = Field(..., description="Projected daily spend in USD")
    lower_bound_80: Decimal = Field(..., description="80% confidence lower bound")
    upper_bound_80: Decimal = Field(..., description="80% confidence upper bound")
    lower_bound_95: Decimal = Field(..., description="95% confidence lower bound")
    upper_bound_95: Decimal = Field(..., description="95% confidence upper bound")


class SpendForecastReport(BaseModel):
    """Holistic spend forecast report comparing future projections against budget limits."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    organization_id: uuid.UUID = Field(..., description="Tenant organization boundary UUID")
    service_id: Optional[str] = Field(default=None, description="Service identifier if scoped, or None for platform")
    currency: str = Field(default="USD", description="Currency code")

    # Historical parameters
    historical_days_evaluated: int = Field(..., description="Days of historical data used for model calibration")
    historical_daily_average: Decimal = Field(..., description="Mean daily expenditure over historical window")

    # Projections
    forecast_days: int = Field(..., description="Number of future days projected")
    projected_total_spend: Decimal = Field(..., description="Cumulative projected spend over forecast horizon")
    daily_burn_rate: Decimal = Field(..., description="Current projected daily burn rate")
    trend_slope: Decimal = Field(..., description="Estimated daily trend slope in USD/day")
    trend_direction: str = Field(..., description="Trend classification: INCREASING, DECREASING, or STABLE")

    # Budget Risk Analysis
    budget_limit: Optional[Decimal] = Field(default=None, description="Optional period budget ceiling")
    budget_exceeded: bool = Field(default=False, description="True if projected spend exceeds budget limit")
    projected_budget_variance: Optional[Decimal] = Field(
        default=None,
        description="Projected overage (+) or surplus (-) relative to budget",
    )

    forecast_points: List[ForecastDataPoint] = Field(
        default_factory=list,
        description="Chronological sequence of projected daily spend points",
    )

    def summary(self) -> Dict[str, Any]:
        """Produces a clean executive summary dictionary."""
        return {
            "organization_id": str(self.organization_id),
            "service_id": self.service_id or "ALL_SERVICES",
            "historical_days": self.historical_days_evaluated,
            "forecast_days": self.forecast_days,
            "historical_daily_average": f"{self.historical_daily_average:.2f}",
            "projected_total_spend": f"{self.projected_total_spend:.2f}",
            "daily_burn_rate": f"{self.daily_burn_rate:.2f}",
            "trend_direction": self.trend_direction,
            "trend_slope": f"{self.trend_slope:.4f}",
            "budget_limit": f"{self.budget_limit:.2f}" if self.budget_limit else "N/A",
            "budget_exceeded": self.budget_exceeded,
            "projected_budget_variance": (
                f"{self.projected_budget_variance:.2f}" if self.projected_budget_variance else "N/A"
            ),
            "currency": self.currency,
        }
