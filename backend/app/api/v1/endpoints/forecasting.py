"""Spend Forecasting & Budget Risk Analysis endpoints."""
from fastapi import APIRouter, Query
from app.services.forecasting import SpendForecastReport
from app.services.platform_state import PlatformStateService

router = APIRouter(prefix="/forecasting", tags=["Spend Forecasting"])


@router.get("/spend", response_model=SpendForecastReport)
async def get_spend_forecast(
    days: int = Query(default=30, ge=7, le=90, description="Forecast horizon in days"),
) -> SpendForecastReport:
    """Computes Holt's linear trend forecast across historical expenditure.
    
    Returns point estimates, 80% and 95% confidence intervals, daily burn rates,
    and budget overrun risk assessments.
    """
    state = PlatformStateService.get_instance()
    return state.get_spend_forecast(forecast_days=days)
