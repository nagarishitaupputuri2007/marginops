"""Time-series spend forecasting engine implementing Holt's Linear Trend with prediction intervals."""
import math
import uuid
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Sequence, Union

from app.services.forecasting.models import ForecastDataPoint, SpendForecastReport


class SpendForecastingEngine:
    """Production forecasting engine projecting future infrastructure spend and budget overrun risks."""

    def __init__(
        self,
        alpha: float = 0.3,
        beta: float = 0.1,
        precision: Decimal = Decimal("0.0001"),
    ):
        """Initializes the forecasting engine.

        Args:
            alpha: Level smoothing factor (0 < alpha < 1).
            beta: Trend smoothing factor (0 < beta < 1).
            precision: Decimal precision quantum.
        """
        self.alpha = alpha
        self.beta = beta
        self.precision = precision

    def forecast_spend(
        self,
        organization_id: uuid.UUID,
        daily_spend_series: Dict[date, Union[Decimal, float]],
        forecast_days: int = 30,
        budget_limit: Optional[Decimal] = None,
        service_id: Optional[str] = None,
    ) -> SpendForecastReport:
        """Projects daily future spend for a given historical time series.

        Args:
            organization_id: Organization boundary UUID.
            daily_spend_series: Mapping of historical date -> daily spend amount.
            forecast_days: Number of future days to project.
            budget_limit: Optional spending cap to test for overrun.
            service_id: Optional service name scope.

        Returns:
            SpendForecastReport with daily forecast points, confidence intervals, and budget risk analysis.
        """
        if not daily_spend_series:
            raise ValueError("daily_spend_series cannot be empty for forecasting")

        sorted_dates = sorted(daily_spend_series.keys())
        y_vals = [float(daily_spend_series[d]) for d in sorted_dates]
        n = len(y_vals)

        # Baseline parameters
        avg_hist = sum(y_vals) / n
        start_date = sorted_dates[-1]

        # Single point fallback
        if n == 1:
            level = y_vals[0]
            trend = 0.0
            residuals = [0.0]
        else:
            # Initialize Holt's Linear Trend
            level = y_vals[0]
            trend = y_vals[1] - y_vals[0]
            residuals: List[float] = []

            for t in range(1, n):
                y_t = y_vals[t]
                prev_level = level
                prev_trend = trend

                pred_t = prev_level + prev_trend
                residuals.append(y_t - pred_t)

                # Update equations
                level = self.alpha * y_t + (1 - self.alpha) * (prev_level + prev_trend)
                trend = self.beta * (level - prev_level) + (1 - self.beta) * prev_trend

        # Compute residual standard error
        if len(residuals) > 1:
            variance = sum(e ** 2 for e in residuals) / len(residuals)
            se = math.sqrt(variance)
        else:
            se = max(1.0, abs(y_vals[0]) * 0.1)

        # Classify trend direction
        if trend > 0.50:
            direction = "INCREASING"
        elif trend < -0.50:
            direction = "DECREASING"
        else:
            direction = "STABLE"

        forecast_points: List[ForecastDataPoint] = []
        cumulative_projected = Decimal("0.0000")

        # Generate future points
        for h in range(1, forecast_days + 1):
            target_date = start_date + timedelta(days=h)
            pred_h = max(0.0, level + h * trend)

            # Horizon-dependent prediction standard error
            se_h = se * math.sqrt(1.0 + (h - 1) * (self.alpha ** 2))

            # 80% interval (Z = 1.282), 95% interval (Z = 1.960)
            low_80 = max(0.0, pred_h - 1.282 * se_h)
            high_80 = max(0.0, pred_h + 1.282 * se_h)
            low_95 = max(0.0, pred_h - 1.960 * se_h)
            high_95 = max(0.0, pred_h + 1.960 * se_h)

            dec_pred = Decimal(str(round(pred_h, 4)))
            cumulative_projected += dec_pred

            forecast_points.append(
                ForecastDataPoint(
                    forecast_date=target_date,
                    predicted_amount=dec_pred,
                    lower_bound_80=Decimal(str(round(low_80, 4))),
                    upper_bound_80=Decimal(str(round(high_80, 4))),
                    lower_bound_95=Decimal(str(round(low_95, 4))),
                    upper_bound_95=Decimal(str(round(high_95, 4))),
                )
            )

        # Budget Risk Analysis
        budget_exceeded = False
        budget_variance: Optional[Decimal] = None
        if budget_limit is not None:
            budget_variance = (cumulative_projected - budget_limit).quantize(Decimal("0.01"))
            budget_exceeded = cumulative_projected > budget_limit

        latest_burn = forecast_points[0].predicted_amount if forecast_points else Decimal("0.0000")

        return SpendForecastReport(
            organization_id=organization_id,
            service_id=service_id,
            historical_days_evaluated=n,
            historical_daily_average=Decimal(str(round(avg_hist, 2))),
            forecast_days=forecast_days,
            projected_total_spend=cumulative_projected.quantize(Decimal("0.01")),
            daily_burn_rate=latest_burn.quantize(Decimal("0.01")),
            trend_slope=Decimal(str(round(trend, 4))),
            trend_direction=direction,
            budget_limit=budget_limit,
            budget_exceeded=budget_exceeded,
            projected_budget_variance=budget_variance,
            forecast_points=forecast_points,
        )
