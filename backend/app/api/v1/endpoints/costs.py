"""Cost intelligence and infrastructure spend endpoints."""
import math
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, File, HTTPException, Query, Response, UploadFile, status
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


@router.post("/upload", response_model=Dict[str, Any])
async def upload_billing_dataset(
    file: UploadFile = File(..., description="Multi-cloud billing CSV export (AWS, GCP, Azure, or Normalized)"),
) -> Dict[str, Any]:
    """Uploads and ingests a custom cloud billing CSV dataset in real time.
    
    Validates line items, executes idempotency checking, runs deterministic attribution,
    and updates anomaly scans dynamically.
    """
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must be a valid .csv file",
        )

    try:
        content_bytes = await file.read()
        content_str = content_bytes.decode("utf-8")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read file content: {str(e)}",
        )

    state = PlatformStateService.get_instance()
    result = state.ingest_custom_billing_file(content_str, filename=file.filename)
    return result


@router.get("/export")
async def export_cost_audit_report(
    format: str = Query(default="json", description="Export format ('json' or 'csv')"),
):
    """Exports an auditable FinOps reconciliation certificate in CSV or JSON format.
    
    Certifies 100% conservation of money down to exact sub-cent precision.
    """
    state = PlatformStateService.get_instance()
    if format.lower() == "csv":
        csv_data = state.export_financial_audit(export_format="csv")
        return Response(
            content=csv_data,
            media_type="text/csv",
            headers={
                "Content-Disposition": "attachment; filename=marginops_reconciliation_audit.csv",
            },
        )
    return state.export_financial_audit(export_format="json")
