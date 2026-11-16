"""Benchmark evaluator validating Anomaly Detection against Ground Truth scenarios (Slide 08)."""
import json
import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from app.services.anomaly_detection.engine import AnomalyDetectionEngine
from app.services.anomaly_detection.models import DetectedAnomaly
from app.services.billing_ingestion import BillingIngestionService


@dataclass
class ScenarioMatchResult:
    """Detailed matching audit for a single ground truth anomaly scenario."""
    scenario_id: str
    scenario_type: str
    title: str
    target_service: str
    target_resource_id: str
    is_detected: bool
    matched_anomaly: Optional[DetectedAnomaly] = None
    expected_impact: Optional[Decimal] = None
    detected_impact: Optional[Decimal] = None


@dataclass
class AnomalyEvaluationReport:
    """Scientific evaluation metrics report benchmarked against synthetic ground truth."""
    total_ground_truth_scenarios: int
    true_positives: int
    false_positives: int
    false_negatives: int
    precision: float
    recall: float
    f1_score: float
    scenario_results: List[ScenarioMatchResult]

    def summary(self) -> Dict[str, Any]:
        """Produces a clean dictionary for evaluation reporting."""
        return {
            "total_ground_truth_scenarios": self.total_ground_truth_scenarios,
            "true_positives": self.true_positives,
            "false_positives": self.false_positives,
            "false_negatives": self.false_negatives,
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "f1_score": round(self.f1_score, 4),
            "scenarios": [
                {
                    "scenario_id": r.scenario_id,
                    "title": r.title,
                    "is_detected": r.is_detected,
                    "matched_anomaly_id": str(r.matched_anomaly.id) if r.matched_anomaly else None,
                }
                for r in self.scenario_results
            ],
        }


class AnomalyBenchmarkEvaluator:
    """Evaluates the AnomalyDetectionEngine against labeled ground-truth scenarios."""

    def __init__(
        self,
        ground_truth_path: Optional[Path] = None,
        billing_csv_path: Optional[Path] = None,
    ):
        base_dir = Path(__file__).resolve().parents[4]  # repo root (marginops)
        self.ground_truth_path = ground_truth_path or (base_dir / "data" / "evaluation" / "ground_truth_anomalies.json")
        self.billing_csv_path = billing_csv_path or (base_dir / "data" / "synthetic" / "cloud_billing_120d.csv")

    def load_ground_truth(self) -> Dict[str, Any]:
        """Loads the isolated ground truth anomaly manifest."""
        with open(self.ground_truth_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def load_billing_records(self) -> List[Any]:
        """Ingests the 120-day synthetic billing dataset using BillingIngestionService."""
        ingest_service = BillingIngestionService()
        report = ingest_service.ingest_file(str(self.billing_csv_path))
        return report.records

    def evaluate(
        self,
        engine: Optional[AnomalyDetectionEngine] = None,
        organization_id: Optional[uuid.UUID] = None,
    ) -> AnomalyEvaluationReport:
        """Executes the benchmark evaluation and computes Precision, Recall, and F1."""
        org_id = organization_id or uuid.uuid4()
        detector = engine or AnomalyDetectionEngine()

        gt_data = self.load_ground_truth()
        scenarios = gt_data.get("scenarios", [])
        billing_records = self.load_billing_records()

        # Run anomaly detection across the full 120-day dataset
        detection_summary = detector.detect_anomalies(org_id, billing_records)
        detected_anomalies = detection_summary.anomalies

        matched_anomaly_ids = set()
        scenario_results: List[ScenarioMatchResult] = []
        tp_count = 0

        for sc in scenarios:
            sc_id = sc["scenario_id"]
            sc_type = sc["scenario_type"]
            sc_svc = sc["target_service"]
            sc_res = sc["target_resource_id"]
            sc_start = date.fromisoformat(sc["start_date"])
            sc_end = date.fromisoformat(sc["end_date"])
            sc_impact = Decimal(str(sc["expected_cost_impact"]))

            matched_a: Optional[DetectedAnomaly] = None

            # Find matching detected anomaly
            for a in detected_anomalies:
                if a.id in matched_anomaly_ids:
                    continue

                type_match = a.anomaly_type.value == sc_type

                target_resources = [p.strip() for p in sc_res.split(",") if p.strip()]
                res_match = any(
                    (r_target in (a.resource_id or "") or (a.resource_id or "") in r_target)
                    for r_target in target_resources
                )

                svc_match = (
                    a.service_id == sc_svc
                    or sc_svc in a.service_id
                    or ("billing" in sc_svc.lower() and "billing" in a.service_id.lower())
                )

                # Overlap in date window
                date_overlap = not (a.end_date and a.end_date < sc_start or a.start_date > sc_end)

                # Criteria: must match resource or (type and service) during overlapping window
                if date_overlap and (res_match or (type_match and svc_match)):
                    matched_a = a
                    matched_anomaly_ids.add(a.id)
                    break

            is_det = matched_a is not None
            if is_det:
                tp_count += 1

            scenario_results.append(
                ScenarioMatchResult(
                    scenario_id=sc_id,
                    scenario_type=sc_type,
                    title=sc["title"],
                    target_service=sc_svc,
                    target_resource_id=sc_res,
                    is_detected=is_det,
                    matched_anomaly=matched_a,
                    expected_impact=sc_impact,
                    detected_impact=matched_a.cost_impact if matched_a else None,
                )
            )

        fn_count = len(scenarios) - tp_count
        # Non-credit False Positives
        fp_count = len([a for a in detected_anomalies if a.id not in matched_anomaly_ids])

        precision = tp_count / (tp_count + fp_count) if (tp_count + fp_count) > 0 else 1.0
        recall = tp_count / len(scenarios) if scenarios else 1.0
        f1 = (
            (2 * precision * recall) / (precision + recall)
            if (precision + recall) > 0
            else 0.0
        )

        return AnomalyEvaluationReport(
            total_ground_truth_scenarios=len(scenarios),
            true_positives=tp_count,
            false_positives=fp_count,
            false_negatives=fn_count,
            precision=precision,
            recall=recall,
            f1_score=f1,
            scenario_results=scenario_results,
        )
