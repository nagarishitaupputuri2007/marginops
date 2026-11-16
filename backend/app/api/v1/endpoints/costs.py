"""Cost intelligence and infrastructure spend endpoints."""
import math
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Query
from app.services.platform_state import PlatformStateService

router = APIRouter(prefix="/costs", tags=["Cost Intelligence"])


@router.get("/summary", response_model=Dict[str, Any])
async def get_costs_summary() -> Dict[str, Any]:
    """Retrieves high-level FinOps KPI metrics, budget burn, and provider breakdown."""
    state = PlatformStateService.get_instance()
    return state.get_kpi_summary()


@router.get("/explorer", response_model=Dict[str, Any])
async def get_cost_explorer(
    provider: Optional[str] = Query(default=None, description="Filter by cloud provider (AWS, GCP, Azure)"),
    service: Optional[str] = Query(default=None, description="Filter by service name or ID"),
    workload: Optional[str] = Query(default=None, description="Filter by workload identifier"),
    page: int = Query(default=1, ge=1, description="1-based page number"),
    limit: int = Query(default=50, ge=1, le=500, description="Items per page"),
) -> Dict[str, Any]:
    """Retrieves filtered chronological billing records and daily aggregated spend time series."""
    state = PlatformStateService.get_instance()
    all_items = state.get_cost_explorer_data(provider=provider, service=service, workload=workload)

    # Paginate items
    total_items = len(all_items)
    total_pages = math.ceil(total_items / limit) if total_items > 0 else 1
    start_idx = (page - 1) * limit
    paginated_items = all_items[start_idx : start_idx + limit]

    # Daily aggregation for interactive charting
    daily_spend_map: Dict[str, Dict[str, float]] = {}
    for item in all_items:
        d = item["billing_date"]
        prov = item["cloud_provider"]
        amt = item["billing_amount"]

        if d not in daily_spend_map:
            daily_spend_map[d] = {"date": d, "total": 0.0, "AWS": 0.0, "GCP": 0.0, "Azure": 0.0}

        daily_spend_map[d]["total"] = round(daily_spend_map[d]["total"] + amt, 4)
        if prov in daily_spend_map[d]:
            daily_spend_map[d][prov] = round(daily_spend_map[d][prov] + amt, 4)

    daily_series = sorted(daily_spend_map.values(), key=lambda x: x["date"])

    return {
        "total_items": total_items,
        "page": page,
        "limit": limit,
        "total_pages": total_pages,
        "items": paginated_items,
        "daily_time_series": daily_series,
    }


@router.get("/attribution", response_model=Dict[str, Any])
async def get_cost_attribution() -> Dict[str, Any]:
    """Executes the Deterministic Cost Attribution Engine and returns an audit breakdown.
    
    Demonstrates 100% reconciliation (Source == Allocated + Unallocated) with zero penny leakage
    via the Hare-Niemeyer Largest Remainder method.
    """
    state = PlatformStateService.get_instance()
    return state.get_attribution_summary()
