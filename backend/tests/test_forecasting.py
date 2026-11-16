"""Comprehensive test suite for the Spend Forecasting Engine."""
import uuid
from datetime import date, timedelta
from decimal import Decimal
import pytest

from app.services.forecasting import (
    ForecastDataPoint,
    SpendForecastReport,
    SpendForecastingEngine,
)


def test_forecast_spend_stable_trend():
    """Engine projects flat spend for a stable historical expenditure series."""
    org_id = uuid.uuid4()
    engine = SpendForecastingEngine(alpha=0.3, beta=0.1)

    daily_spend = {}
    base_date = date(2026, 5, 1)

    # 30 days of constant $100/day spend
    for i in range(30):
        d = base_date + timedelta(days=i)
        daily_spend[d] = Decimal("100.00")

    report = engine.forecast_spend(
        organization_id=org_id,
        daily_spend_series=daily_spend,
        forecast_days=30,
    )

    assert report.forecast_days == 30
    assert report.historical_days_evaluated == 30
    assert report.historical_daily_average == Decimal("100.00")
    assert report.trend_direction == "STABLE"
    assert report.daily_burn_rate == pytest.approx(Decimal("100.00"), abs=Decimal("1.00"))
    # Cumulative 30 days ~ $3,000
    assert report.projected_total_spend == pytest.approx(Decimal("3000.00"), abs=Decimal("50.00"))

    # Confidence interval checks
    p1 = report.forecast_points[0]
    assert p1.lower_bound_80 <= p1.predicted_amount <= p1.upper_bound_80
    assert p1.lower_bound_95 <= p1.predicted_amount <= p1.upper_bound_95


def test_forecast_spend_increasing_trend_and_budget_overage():
    """Engine detects upward trajectory and flags risk of exceeding budget cap."""
    org_id = uuid.uuid4()
    engine = SpendForecastingEngine(alpha=0.4, beta=0.2)

    daily_spend = {}
    base_date = date(2026, 6, 1)

    # 20 days increasing from $50 by $5 each day (Day 20 = $145)
    for i in range(20):
        d = base_date + timedelta(days=i)
        daily_spend[d] = Decimal(str(50 + (i * 5)))

    budget_cap = Decimal("3000.00")

    report = engine.forecast_spend(
        organization_id=org_id,
        daily_spend_series=daily_spend,
        forecast_days=30,
        budget_limit=budget_cap,
    )

    assert report.trend_direction == "INCREASING"
    assert report.trend_slope > Decimal("0.0")
    # Projections continue to grow, exceeding $3,000
    assert report.budget_exceeded is True
    assert report.projected_budget_variance is not None and report.projected_budget_variance > Decimal("0.0")


def test_forecast_empty_series_raises_error():
    """Forecasting on empty historical series raises ValueError."""
    org_id = uuid.uuid4()
    engine = SpendForecastingEngine()

    with pytest.raises(ValueError, match="daily_spend_series cannot be empty"):
        engine.forecast_spend(
            organization_id=org_id,
            daily_spend_series={},
        )
