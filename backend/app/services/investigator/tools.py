"""Bounded, allowlisted read-only investigation tools for the AI Investigator (Slide 06)."""
import uuid
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence

from app.services.cost_attribution.models import TenantIsolationError


class BoundedInvestigationTools:
    """Allowlisted read-only diagnostic tools.

    Enforces strict tenant isolation and safety boundaries:
    - Zero write access to cloud providers.
    - Zero destructive mutations.
    - Strictly returns verifiable forensic records from PostgreSQL and MongoDB.
    """

    def __init__(
        self,
        cost_records: Optional[Sequence[Any]] = None,
        telemetry_events: Optional[Sequence[Any]] = None,
    ):
        """Initializes the bounded tool sandbox.

        Args:
            cost_records: Available PostgreSQL normalized cost records.
            telemetry_events: Available MongoDB telemetry events.
        """
        self._cost_records = cost_records or []
        self._telemetry_events = telemetry_events or []

    def _verify_tenant(self, organization_id: uuid.UUID, record_org_id: Any) -> None:
        """Enforces that tools cannot access records belonging to another tenant."""
        if record_org_id is not None and str(record_org_id) != str(organization_id):
            raise TenantIsolationError(
                f"Tool security violation: Cross-tenant access attempt to org '{record_org_id}' "
                f"from context org '{organization_id}'."
            )

    def query_cost_ledger(
        self,
        organization_id: uuid.UUID,
        service_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        """Bounded Tool 1: Queries verified historical spend records from the financial ledger."""
        matches: List[Dict[str, Any]] = []

        for r in self._cost_records:
            # Handle both dict and object
            rec_org = getattr(r, "organization_id", None) if not isinstance(r, dict) else r.get("organization_id")
            if rec_org is not None and str(rec_org) != str(organization_id):
                continue

            r_svc = str(getattr(r, "service_id", "") if not isinstance(r, dict) else r.get("service_id", ""))
            r_res = str(getattr(r, "resource_id", "") if not isinstance(r, dict) else r.get("resource_id", ""))
            r_date = getattr(r, "billing_date", None) if not isinstance(r, dict) else r.get("billing_date")
            if isinstance(r_date, str):
                r_date = date.fromisoformat(r_date)

            if service_id and service_id.lower() not in r_svc.lower():
                continue
            if resource_id and resource_id.lower() not in r_res.lower():
                continue
            if start_date and r_date and r_date < start_date:
                continue
            if end_date and r_date and r_date > end_date:
                continue

            raw_amt = getattr(r, "billing_amount", None) if not isinstance(r, dict) else r.get("billing_amount")
            if raw_amt is None:
                raw_amt = getattr(r, "cost", Decimal("0")) if not isinstance(r, dict) else r.get("cost", Decimal("0"))

            tags = getattr(r, "resource_tags", {}) if not isinstance(r, dict) else r.get("resource_tags", {})

            matches.append({
                "billing_date": r_date.isoformat() if r_date else None,
                "service_id": r_svc,
                "resource_id": r_res,
                "billing_amount": float(Decimal(str(raw_amt))),
                "tags": tags or {},
            })

        return sorted(matches, key=lambda x: x["billing_date"] or "")

    def query_telemetry_metrics(
        self,
        organization_id: uuid.UUID,
        feature_id: Optional[uuid.UUID] = None,
        model_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Bounded Tool 2: Queries verified token volume, latencies, and error rates from MongoDB."""
        total_requests = 0
        total_prompts = 0
        total_completions = 0
        latencies: List[float] = []
        errors = 0
        models_seen: Dict[str, int] = {}

        for ev in self._telemetry_events:
            ev_org = getattr(ev, "organization_id", None) if not isinstance(ev, dict) else ev.get("organization_id")
            if ev_org is not None and str(ev_org) != str(organization_id):
                continue

            ev_feat = getattr(ev, "product_feature_id", None) if not isinstance(ev, dict) else ev.get("product_feature_id")
            if feature_id and ev_feat and str(ev_feat) != str(feature_id):
                continue

            ev_model = getattr(ev, "ai_model", None) if not isinstance(ev, dict) else ev.get("ai_model")
            if model_name and ev_model and model_name.lower() not in str(ev_model).lower():
                continue

            total_requests += 1

            # Tokens
            tokens_obj = getattr(ev, "tokens", None) if not isinstance(ev, dict) else ev.get("tokens")
            if tokens_obj:
                p_tok = getattr(tokens_obj, "prompt_tokens", 0) if not isinstance(tokens_obj, dict) else tokens_obj.get("prompt_tokens", 0)
                c_tok = getattr(tokens_obj, "completion_tokens", 0) if not isinstance(tokens_obj, dict) else tokens_obj.get("completion_tokens", 0)
                total_prompts += p_tok
                total_completions += c_tok

            # Latency
            lat = getattr(ev, "latency_ms", None) if not isinstance(ev, dict) else ev.get("latency_ms")
            if lat is not None:
                latencies.append(float(lat))

            # Status
            stat = str(getattr(ev, "status", "success") if not isinstance(ev, dict) else ev.get("status", "success")).lower()
            if "error" in stat or "timeout" in stat:
                errors += 1

            if ev_model:
                models_seen[str(ev_model)] = models_seen.get(str(ev_model), 0) + 1

        avg_lat = sum(latencies) / len(latencies) if latencies else None

        return {
            "total_requests": total_requests,
            "total_tokens": total_prompts + total_completions,
            "prompt_tokens": total_prompts,
            "completion_tokens": total_completions,
            "error_count": errors,
            "error_rate_pct": round((errors / total_requests * 100.0), 2) if total_requests > 0 else 0.0,
            "avg_latency_ms": round(avg_lat, 2) if avg_lat is not None else None,
            "models_distribution": models_seen,
        }

    def inspect_resource_metadata(
        self,
        organization_id: uuid.UUID,
        resource_id: str,
    ) -> Dict[str, Any]:
        """Bounded Tool 3: Queries tag dimensions, environment, and ownership for a specific resource."""
        for r in self._cost_records:
            rec_org = getattr(r, "organization_id", None) if not isinstance(r, dict) else r.get("organization_id")
            if rec_org is not None and str(rec_org) != str(organization_id):
                continue

            r_res = str(getattr(r, "resource_id", "") if not isinstance(r, dict) else r.get("resource_id", ""))
            if resource_id.lower() in r_res.lower() or r_res.lower() in resource_id.lower():
                tags = getattr(r, "resource_tags", {}) if not isinstance(r, dict) else r.get("resource_tags", {})
                return {
                    "found": True,
                    "resource_id": r_res,
                    "service_id": str(getattr(r, "service_id", "") if not isinstance(r, dict) else r.get("service_id", "")),
                    "cloud_provider": str(getattr(r, "cloud_provider", "") if not isinstance(r, dict) else r.get("cloud_provider", "")),
                    "workload_id": getattr(r, "workload_id", None) if not isinstance(r, dict) else r.get("workload_id"),
                    "tags": tags or {},
                }

        return {"resource_id": resource_id, "found": False}

    def calculate_potential_savings(
        self,
        current_daily_spend: Decimal,
        reduction_percentage: Decimal,
    ) -> Decimal:
        """Bounded Tool 4: Pure deterministic projection of monthly cost savings."""
        monthly_current = current_daily_spend * Decimal("30.0")
        savings = (monthly_current * (reduction_percentage / Decimal("100.00"))).quantize(Decimal("0.01"))
        return max(Decimal("0.00"), savings)
