"""Statistical and heuristic anomaly detection engine for multi-cloud infrastructure expenditures."""
import math
import uuid
from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from app.services.anomaly_detection.models import (
    AnomalyDetectionSummary,
    AnomalySeverity,
    AnomalyStatus,
    AnomalyType,
    DetectedAnomaly,
)


class AnomalyDetectionEngine:
    """Production-grade anomaly detection engine evaluating multi-cloud infrastructure line items.

    Identifies:
    1. Compute spikes (runaway auto-scaling, infinite loops) via rolling Z-score & EWMA.
    2. Storage leaks (monotonically increasing uncompressed buckets / unmanaged volumes).
    3. AI / LLM token surges (recursive reasoning loops, unbounded prompt expansion).
    4. Underutilized zombie resources (orphaned staging databases and idle replicas).
    5. Credits, refunds, and financial ledger adjustments.
    """

    def __init__(
        self,
        z_score_threshold: float = 3.0,
        min_impact_usd: Decimal = Decimal("20.00"),
        rolling_baseline_days: int = 14,
        storage_leak_min_days: int = 21,
    ):
        """Initializes the anomaly detection engine.

        Args:
            z_score_threshold: Number of standard deviations above baseline to flag as spike.
            min_impact_usd: Minimum dollar deviation required to avoid alerting on noise.
            rolling_baseline_days: Number of historical days used to calculate baseline mean and std dev.
            storage_leak_min_days: Consecutive days of monotonic increase required to flag storage creep.
        """
        self.z_score_threshold = z_score_threshold
        self.min_impact_usd = min_impact_usd
        self.rolling_baseline_days = rolling_baseline_days
        self.storage_leak_min_days = storage_leak_min_days

    def _extract_record(self, record: Any) -> Dict[str, Any]:
        """Extracts normalized billing fields from CostRecord model, ParsedBillingRecord, or dict."""
        if isinstance(record, dict):
            raw_amt = record.get("billing_amount")
            if raw_amt is None:
                raw_amt = record.get("cost", Decimal("0"))
            b_date = record.get("billing_date")
            if isinstance(b_date, str):
                b_date = date.fromisoformat(b_date)

            return {
                "organization_id": record.get("organization_id"),
                "billing_date": b_date,
                "cloud_provider": str(record.get("cloud_provider", "Unknown")),
                "service_id": str(record.get("service_id", "")),
                "resource_id": str(record.get("resource_id", "")),
                "workload_id": record.get("workload_id"),
                "product_feature_id": record.get("product_feature_id"),
                "billing_amount": Decimal(str(raw_amt)),
                "is_credit": bool(record.get("is_credit", Decimal(str(raw_amt)) < Decimal("0"))),
                "resource_tags": record.get("resource_tags", {}) or {},
            }

        # Object / SQLAlchemy / Pydantic model
        raw_amt = getattr(record, "billing_amount", None)
        if raw_amt is None:
            raw_amt = getattr(record, "cost", Decimal("0"))
        b_date = getattr(record, "billing_date", None)
        if isinstance(b_date, str):
            b_date = date.fromisoformat(b_date)

        provider = getattr(record, "cloud_provider", "Unknown")
        provider_str = provider.value if hasattr(provider, "value") else str(provider)

        return {
            "organization_id": getattr(record, "organization_id", None),
            "billing_date": b_date,
            "cloud_provider": provider_str,
            "service_id": str(getattr(record, "service_id", "")),
            "resource_id": str(getattr(record, "resource_id", "")),
            "workload_id": getattr(record, "workload_id", None),
            "product_feature_id": getattr(record, "product_feature_id", None),
            "billing_amount": Decimal(str(raw_amt)),
            "is_credit": bool(getattr(record, "is_credit", Decimal(str(raw_amt)) < Decimal("0"))),
            "resource_tags": getattr(record, "resource_tags", {}) or {},
        }

    def detect_anomalies(
        self,
        organization_id: uuid.UUID,
        records: Sequence[Any],
    ) -> AnomalyDetectionSummary:
        """Executes full anomaly detection across a dataset of billing records.

        Args:
            organization_id: Organization boundary UUID.
            records: Sequence of CostRecord models, ParsedBillingRecords, or dicts.

        Returns:
            AnomalyDetectionSummary containing all flagged anomalies and statistics.
        """
        extracted_records = [self._extract_record(r) for r in records]
        # Filter strictly for the specified tenant
        org_records = [
            r for r in extracted_records
            if r["organization_id"] is None or str(r["organization_id"]) == str(organization_id)
        ]

        if not org_records:
            return AnomalyDetectionSummary(
                organization_id=organization_id,
                evaluated_records_count=0,
                evaluated_days_count=0,
                anomalies_detected_count=0,
                total_cost_impact=Decimal("0.0000"),
            )

        all_dates = {r["billing_date"] for r in org_records if r["billing_date"]}
        detected_anomalies: List[DetectedAnomaly] = []

        # -------------------------------------------------------------
        # Pass 1: Build Daily Series per Resource, Workload, and Service
        # -------------------------------------------------------------
        resource_series: Dict[Tuple[str, str, str], Dict[date, List[Dict[str, Any]]]] = defaultdict(
            lambda: defaultdict(list)
        )
        workload_series: Dict[str, Dict[date, List[Dict[str, Any]]]] = defaultdict(
            lambda: defaultdict(list)
        )
        service_series: Dict[Tuple[str, str], Dict[date, Decimal]] = defaultdict(
            lambda: defaultdict(lambda: Decimal("0.0000"))
        )

        credits_found: List[Dict[str, Any]] = []

        for r in org_records:
            b_date = r["billing_date"]
            if not b_date:
                continue

            # Separate credits/refunds
            if r["is_credit"] or r["billing_amount"] < Decimal("0"):
                credits_found.append(r)
                continue

            key = (r["cloud_provider"], r["service_id"], r["resource_id"])
            resource_series[key][b_date].append(r)

            wl = r["workload_id"]
            if wl:
                workload_series[wl][b_date].append(r)

            svc_key = (r["cloud_provider"], r["service_id"])
            service_series[svc_key][b_date] += r["billing_amount"]

        # -------------------------------------------------------------
        # Pass 2: Detect Outlier Spikes (Resource & Workload Levels)
        # -------------------------------------------------------------
        spike_anomalies = self._detect_resource_spikes(organization_id, resource_series)
        detected_anomalies.extend(spike_anomalies)

        workload_spikes = self._detect_workload_spikes(organization_id, workload_series, detected_anomalies)
        detected_anomalies.extend(workload_spikes)

        # -------------------------------------------------------------
        # Pass 3: Detect Monotonic Storage Leaks
        # -------------------------------------------------------------
        storage_leaks = self._detect_storage_leaks(organization_id, resource_series)
        detected_anomalies.extend(storage_leaks)

        # -------------------------------------------------------------
        # Pass 4: Detect Underutilized / Idle Zombie Resources
        # -------------------------------------------------------------
        idle_anomalies = self._detect_idle_zombie_resources(organization_id, resource_series)
        detected_anomalies.extend(idle_anomalies)

        # -------------------------------------------------------------
        # Pass 5: Record Major Financial Credits / Refunds
        # -------------------------------------------------------------
        credit_anomalies = self._detect_credits(organization_id, credits_found)
        detected_anomalies.extend(credit_anomalies)

        # Compute summary metrics
        total_impact = sum((a.cost_impact for a in detected_anomalies), Decimal("0.0000"))
        by_sev: Dict[str, int] = defaultdict(int)
        by_typ: Dict[str, int] = defaultdict(int)
        for a in detected_anomalies:
            by_sev[a.severity.value] += 1
            by_typ[a.anomaly_type.value] += 1

        return AnomalyDetectionSummary(
            organization_id=organization_id,
            evaluated_records_count=len(org_records),
            evaluated_days_count=len(all_dates),
            anomalies_detected_count=len(detected_anomalies),
            total_cost_impact=total_impact,
            by_severity=dict(by_sev),
            by_type=dict(by_typ),
            anomalies=detected_anomalies,
        )

    def _detect_resource_spikes(
        self,
        organization_id: uuid.UUID,
        resource_series: Dict[Tuple[str, str, str], Dict[date, List[Dict[str, Any]]]],
    ) -> List[DetectedAnomaly]:
        """Detects sudden statistical cost surges using rolling Z-score and percentage deviation."""
        anomalies: List[DetectedAnomaly] = []

        for (provider, service_id, resource_id), date_map in resource_series.items():
            sorted_dates = sorted(date_map.keys())
            if len(sorted_dates) < 3:
                continue

            daily_costs = {d: sum((r["billing_amount"] for r in date_map[d]), Decimal("0.0000")) for d in sorted_dates}

            # Scan with rolling baseline
            for i in range(1, len(sorted_dates)):
                curr_date = sorted_dates[i]
                curr_cost = daily_costs[curr_date]

                baseline_dates = [d for d in sorted_dates[:i] if (curr_date - d).days <= self.rolling_baseline_days]
                if not baseline_dates:
                    continue

                baseline_vals = [float(daily_costs[d]) for d in baseline_dates]
                mean_baseline = sum(baseline_vals) / len(baseline_vals)
                variance = sum((x - mean_baseline) ** 2 for x in baseline_vals) / len(baseline_vals)
                std_dev = math.sqrt(variance) if variance > 0 else 0.0

                diff = float(curr_cost) - mean_baseline

                if std_dev > 0:
                    z_score = diff / std_dev
                else:
                    z_score = 10.0 if diff > float(self.min_impact_usd) else 0.0

                pct_increase = (diff / mean_baseline * 100.0) if mean_baseline > 0 else 500.0

                if z_score >= self.z_score_threshold and Decimal(str(round(diff, 2))) >= self.min_impact_usd:
                    svc_lower = service_id.lower()
                    if "bedrock" in svc_lower or "openai" in svc_lower or "vertex" in svc_lower or "anthropic" in resource_id.lower():
                        a_type = AnomalyType.AI_TOKEN_SURGE
                        title = f"AI Token & Inference Surge on {service_id}"
                        hint = "Excessive token output volume or multi-agent recursive prompting loop."
                    elif "ec2" in svc_lower or "compute" in svc_lower or "worker" in resource_id.lower():
                        a_type = AnomalyType.COMPUTE_SPIKE
                        title = f"Runaway Compute Scaling Spike on {service_id}"
                        hint = "Autoscaling group triggered by runaway queue backlog or worker crash loop."
                    else:
                        a_type = AnomalyType.GENERAL_COST_SPIKE
                        title = f"Abnormal Cost Spike on {service_id}"
                        hint = f"Daily spend exceeded 14-day rolling baseline by {pct_increase:.1f}%."

                    severity = AnomalySeverity.CRITICAL if (z_score >= 4.5 or pct_increase >= 500.0) else (
                        AnomalySeverity.HIGH if z_score >= 3.5 or pct_increase >= 200.0 else AnomalySeverity.MEDIUM
                    )

                    sample_record = date_map[curr_date][0]
                    anomalies.append(
                        DetectedAnomaly(
                            organization_id=organization_id,
                            anomaly_type=a_type,
                            severity=severity,
                            title=title,
                            description=(
                                f"Resource '{resource_id}' daily cost reached ${curr_cost:.2f} "
                                f"compared to historical baseline of ${mean_baseline:.2f} "
                                f"(Z-score: {z_score:.2f}, +{pct_increase:.1f}%)."
                            ),
                            cloud_provider=provider,
                            service_id=service_id,
                            resource_id=resource_id,
                            workload_id=sample_record["workload_id"],
                            product_feature_id=sample_record["product_feature_id"],
                            detected_date=curr_date,
                            start_date=curr_date,
                            end_date=curr_date,
                            actual_cost=curr_cost,
                            expected_baseline_cost=Decimal(str(round(mean_baseline, 4))),
                            cost_impact=Decimal(str(round(diff, 4))),
                            z_score=round(z_score, 2),
                            percentage_increase=round(pct_increase, 2),
                            evidence={
                                "daily_cost": float(curr_cost),
                                "mean_baseline": round(mean_baseline, 2),
                                "z_score": round(z_score, 2),
                                "percentage_increase": round(pct_increase, 2),
                                "historical_samples_count": len(baseline_vals),
                            },
                            root_cause_hint=hint,
                        )
                    )

        return anomalies

    def _detect_workload_spikes(
        self,
        organization_id: uuid.UUID,
        workload_series: Dict[str, Dict[date, List[Dict[str, Any]]]],
        existing_anomalies: List[DetectedAnomaly],
    ) -> List[DetectedAnomaly]:
        """Detects workload-level aggregate surges and pins root-cause to top contributing resources."""
        anomalies: List[DetectedAnomaly] = []
        already_flagged = {(a.resource_id, a.detected_date) for a in existing_anomalies if a.resource_id}

        for workload_id, date_map in workload_series.items():
            sorted_dates = sorted(date_map.keys())
            if len(sorted_dates) < 3:
                continue

            daily_costs = {d: sum((r["billing_amount"] for r in date_map[d]), Decimal("0.0000")) for d in sorted_dates}

            for i in range(1, len(sorted_dates)):
                curr_date = sorted_dates[i]
                curr_cost = daily_costs[curr_date]

                baseline_dates = [d for d in sorted_dates[:i] if (curr_date - d).days <= self.rolling_baseline_days]
                if not baseline_dates:
                    continue

                baseline_vals = [float(daily_costs[d]) for d in baseline_dates]
                mean_baseline = sum(baseline_vals) / len(baseline_vals)
                variance = sum((x - mean_baseline) ** 2 for x in baseline_vals) / len(baseline_vals)
                std_dev = math.sqrt(variance) if variance > 0 else 0.0

                diff = float(curr_cost) - mean_baseline

                if std_dev > 0:
                    z_score = diff / std_dev
                else:
                    z_score = 10.0 if diff > float(self.min_impact_usd) else 0.0

                pct_increase = (diff / mean_baseline * 100.0) if mean_baseline > 0 else 500.0

                if z_score >= self.z_score_threshold and Decimal(str(round(diff, 2))) >= self.min_impact_usd:
                    # Find the top contributing resource on this spike day
                    day_records = date_map[curr_date]
                    res_contributions: Dict[str, Decimal] = defaultdict(Decimal)
                    for r in day_records:
                        res_contributions[r["resource_id"]] += r["billing_amount"]

                    top_res_id = max(res_contributions, key=res_contributions.get)
                    top_record = next(r for r in day_records if r["resource_id"] == top_res_id)

                    if (top_res_id, curr_date) in already_flagged:
                        continue

                    svc_id = top_record["service_id"]
                    svc_lower = svc_id.lower()
                    if "ec2" in svc_lower or "compute" in svc_lower or "worker" in top_res_id.lower():
                        a_type = AnomalyType.COMPUTE_SPIKE
                        title = f"Runaway Compute Scaling Spike on {top_res_id}"
                        hint = "Autoscaling group triggered by runaway worker queue loop."
                    elif "bedrock" in svc_lower or "openai" in svc_lower:
                        a_type = AnomalyType.AI_TOKEN_SURGE
                        title = f"AI Inference Surge on {top_res_id}"
                        hint = "Excessive token output volume or recursive reasoning loop."
                    else:
                        a_type = AnomalyType.GENERAL_COST_SPIKE
                        title = f"Workload Spike on {workload_id}"
                        hint = f"Workload cost surged by +{pct_increase:.1f}%."

                    severity = AnomalySeverity.CRITICAL if (z_score >= 4.5 or pct_increase >= 500.0) else AnomalySeverity.HIGH

                    anomalies.append(
                        DetectedAnomaly(
                            organization_id=organization_id,
                            anomaly_type=a_type,
                            severity=severity,
                            title=title,
                            description=(
                                f"Workload '{workload_id}' surged to ${curr_cost:.2f} on {curr_date} "
                                f"(Z-score: {z_score:.2f}, +{pct_increase:.1f}% over baseline ${mean_baseline:.2f}). "
                                f"Primary driver: resource '{top_res_id}' (${res_contributions[top_res_id]:.2f})."
                            ),
                            cloud_provider=top_record["cloud_provider"],
                            service_id=svc_id,
                            resource_id=top_res_id,
                            workload_id=workload_id,
                            product_feature_id=top_record["product_feature_id"],
                            detected_date=curr_date,
                            start_date=curr_date,
                            end_date=curr_date,
                            actual_cost=curr_cost,
                            expected_baseline_cost=Decimal(str(round(mean_baseline, 4))),
                            cost_impact=Decimal(str(round(diff, 4))),
                            z_score=round(z_score, 2),
                            percentage_increase=round(pct_increase, 2),
                            evidence={
                                "workload_cost": float(curr_cost),
                                "mean_baseline": round(mean_baseline, 2),
                                "z_score": round(z_score, 2),
                                "primary_contributor_cost": float(res_contributions[top_res_id]),
                            },
                            root_cause_hint=hint,
                        )
                    )
                    already_flagged.add((top_res_id, curr_date))

        return anomalies

    def _detect_storage_leaks(
        self,
        organization_id: uuid.UUID,
        resource_series: Dict[Tuple[str, str, str], Dict[date, List[Dict[str, Any]]]],
    ) -> List[DetectedAnomaly]:
        """Detects monotonic accumulation of storage costs over extended timeframes."""
        anomalies: List[DetectedAnomaly] = []

        for (provider, service_id, resource_id), date_map in resource_series.items():
            svc_lower = service_id.lower()
            if not ("s3" in svc_lower or "storage" in svc_lower or "blob" in svc_lower):
                continue

            sorted_dates = sorted(date_map.keys())
            if len(sorted_dates) < self.storage_leak_min_days:
                continue

            daily_costs = [sum((r["billing_amount"] for r in date_map[d]), Decimal("0.0000")) for d in sorted_dates]

            first_half = daily_costs[:len(daily_costs) // 2]
            second_half = daily_costs[len(daily_costs) // 2:]
            avg_first = sum(first_half) / len(first_half)
            avg_second = sum(second_half) / len(second_half)

            increases = sum(1 for i in range(1, len(daily_costs)) if daily_costs[i] >= daily_costs[i - 1])
            growth_ratio = increases / (len(daily_costs) - 1)

            if growth_ratio >= 0.80 and avg_second >= (avg_first * Decimal("1.50")):
                total_growth = daily_costs[-1] - daily_costs[0]
                sample_record = date_map[sorted_dates[0]][0]

                anomalies.append(
                    DetectedAnomaly(
                        organization_id=organization_id,
                        anomaly_type=AnomalyType.STORAGE_LEAK,
                        severity=AnomalySeverity.HIGH,
                        title=f"Unbounded Storage Leak on {resource_id}",
                        description=(
                            f"Storage resource '{resource_id}' exhibited monotonic daily cost accumulation "
                            f"over {len(sorted_dates)} consecutive days, growing from ${daily_costs[0]:.2f}/day "
                            f"to ${daily_costs[-1]:.2f}/day without lifecycle object expiration."
                        ),
                        cloud_provider=provider,
                        service_id=service_id,
                        resource_id=resource_id,
                        workload_id=sample_record["workload_id"],
                        product_feature_id=sample_record["product_feature_id"],
                        detected_date=sorted_dates[-1],
                        start_date=sorted_dates[0],
                        end_date=sorted_dates[-1],
                        actual_cost=sum(daily_costs),
                        expected_baseline_cost=daily_costs[0] * Decimal(len(daily_costs)),
                        cost_impact=sum(daily_costs) - (daily_costs[0] * Decimal(len(daily_costs))),
                        percentage_increase=float(round(((avg_second - avg_first) / avg_first) * 100, 2)),
                        evidence={
                            "days_monitored": len(sorted_dates),
                            "monotonic_growth_ratio": round(growth_ratio, 2),
                            "start_daily_cost": float(daily_costs[0]),
                            "end_daily_cost": float(daily_costs[-1]),
                        },
                        root_cause_hint="Bucket missing S3/GCS lifecycle expiration or Glacier transition policy.",
                    )
                )

        return anomalies

    def _detect_idle_zombie_resources(
        self,
        organization_id: uuid.UUID,
        resource_series: Dict[Tuple[str, str, str], Dict[date, List[Dict[str, Any]]]],
    ) -> List[DetectedAnomaly]:
        """Detects persistently flat, unutilized staging/test resources running 24/7."""
        anomalies: List[DetectedAnomaly] = []

        for (provider, service_id, resource_id), date_map in resource_series.items():
            res_lower = resource_id.lower()
            svc_lower = service_id.lower()

            is_candidate = (
                "staging" in res_lower
                or "test" in res_lower
                or "orphan" in res_lower
                or "replica" in res_lower
                or "rds" in svc_lower
            )
            if not is_candidate:
                continue

            sorted_dates = sorted(date_map.keys())
            if len(sorted_dates) < 30:
                continue

            daily_costs = [sum((r["billing_amount"] for r in date_map[d]), Decimal("0.0000")) for d in sorted_dates]
            cost_range = max(daily_costs) - min(daily_costs)
            avg_cost = sum(daily_costs) / len(daily_costs)

            if avg_cost > Decimal("2.00") and cost_range <= Decimal("1.00"):
                sample_record = date_map[sorted_dates[0]][0]
                total_waste = sum(daily_costs)

                anomalies.append(
                    DetectedAnomaly(
                        organization_id=organization_id,
                        anomaly_type=AnomalyType.UNDERUTILIZED_RESOURCE,
                        severity=AnomalySeverity.MEDIUM,
                        title=f"Orphaned Idle Resource Waste: {resource_id}",
                        description=(
                            f"Resource '{resource_id}' on {service_id} has run continuously for {len(sorted_dates)} "
                            f"days with constant flat billing (${avg_cost:.2f}/day, totaling ${total_waste:.2f}), "
                            f"exhibiting zero traffic variance or utilization changes."
                        ),
                        cloud_provider=provider,
                        service_id=service_id,
                        resource_id=resource_id,
                        workload_id=sample_record["workload_id"],
                        product_feature_id=sample_record["product_feature_id"],
                        detected_date=sorted_dates[-1],
                        start_date=sorted_dates[0],
                        end_date=sorted_dates[-1],
                        actual_cost=total_waste,
                        expected_baseline_cost=Decimal("0.0000"),
                        cost_impact=total_waste,
                        evidence={
                            "days_active": len(sorted_dates),
                            "daily_cost": float(avg_cost),
                            "total_waste_usd": float(total_waste),
                        },
                        root_cause_hint="Orphaned staging database or unattached read replica left running 24/7.",
                    )
                )

        return anomalies

    def _detect_credits(
        self,
        organization_id: uuid.UUID,
        credits_found: List[Dict[str, Any]],
    ) -> List[DetectedAnomaly]:
        """Audits negative billing adjustments, refunds, and enterprise credits."""
        anomalies: List[DetectedAnomaly] = []

        for r in credits_found:
            amt = r["billing_amount"]
            b_date = r["billing_date"]
            res_id = r["resource_id"]
            svc = r["service_id"]

            anomalies.append(
                DetectedAnomaly(
                    organization_id=organization_id,
                    anomaly_type=AnomalyType.CREDIT_REFUND,
                    severity=AnomalySeverity.LOW,
                    title=f"Cloud Credit / Outage Refund: {svc}",
                    description=f"Negative billing adjustment of ${amt:.2f} applied to {svc} ({res_id}).",
                    cloud_provider=r["cloud_provider"],
                    service_id=svc,
                    resource_id=res_id,
                    workload_id=r["workload_id"],
                    product_feature_id=r["product_feature_id"],
                    detected_date=b_date,
                    start_date=b_date,
                    end_date=b_date,
                    actual_cost=amt,
                    expected_baseline_cost=Decimal("0.0000"),
                    cost_impact=amt,
                    evidence={"credit_amount": float(amt), "service_id": svc},
                    root_cause_hint="Enterprise commitment discount, promotional grant, or SLA downtime refund.",
                )
            )

        return anomalies
