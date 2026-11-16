"""Infrastructure Cost Anomaly Detection & Ground Truth Benchmark endpoints."""
from fastapi import APIRouter
from app.services.anomaly_detection import AnomalyDetectionSummary, AnomalyEvaluationReport
from app.services.platform_state import PlatformStateService

router = APIRouter(prefix="/anomalies", tags=["Anomaly Detection"])


@router.get("", response_model=AnomalyDetectionSummary)
async def get_active_anomalies() -> AnomalyDetectionSummary:
    """Scans multi-cloud expenditure and returns detected anomalies with statistical deviations.
    
    Identifies compute spikes, storage leaks, AI token surges, idle database replicas,
    and credit adjustments.
    """
    state = PlatformStateService.get_instance()
    return state.get_anomalies_summary()


@router.get("/benchmark", response_model=AnomalyEvaluationReport)
async def get_benchmark_evaluation() -> AnomalyEvaluationReport:
    """Evaluates the anomaly detection engine against the Slide 08 ground-truth manifest.
    
    Reports precision, recall (80%+ target), F1-score, and scenario-by-scenario verification.
    """
    state = PlatformStateService.get_instance()
    return state.get_ground_truth_benchmark_report()
