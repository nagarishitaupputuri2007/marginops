"""Product Unit Economics & Telemetry Fusion REST endpoints."""
from typing import Any, Dict
from fastapi import APIRouter
from app.services.platform_state import PlatformStateService
from app.services.unit_economics import UnitEconomicsReport

router = APIRouter(prefix="/unit-economics", tags=["Product Unit Economics"])


@router.get("/report", response_model=UnitEconomicsReport)
async def get_unit_economics_report() -> UnitEconomicsReport:
    """Retrieves fused unit economics report reconciling cloud COGS with telemetry traffic.
    
    Includes Cost per 1,000 Requests, Cost per 1,000,000 Tokens, and Gross Margin scorecards
    with HEALTHY, WARNING, CRITICAL, and NEGATIVE status classifications.
    """
    state = PlatformStateService.get_instance()
    return state.get_unit_economics_report()
