"""Domain data models and enums for Infrastructure Cost Anomaly Detection."""
import enum
import uuid
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class AnomalyType(str, enum.Enum):
    """Categorization of detected infrastructure anomalies."""
    COMPUTE_SPIKE = "compute_spike"
    STORAGE_LEAK = "storage_leak"
    AI_TOKEN_SURGE = "ai_token_surge"
    UNDERUTILIZED_RESOURCE = "underutilized_resource"
    CREDIT_REFUND = "credit_refund"
    GENERAL_COST_SPIKE = "general_cost_spike"


class AnomalySeverity(str, enum.Enum):
    """Business severity classification of the anomaly."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AnomalyStatus(str, enum.Enum):
    """Investigation lifecycle status for detected anomalies."""
    OPEN = "open"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"
    FALSE_POSITIVE = "false_positive"


class DetectedAnomaly(BaseModel):
    """Represents an anomalous cost pattern or outlier detected on the infrastructure ledger."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, description="Unique anomaly identifier")
    organization_id: uuid.UUID = Field(..., description="Organization boundary UUID")
    anomaly_type: AnomalyType = Field(..., description="Classification of the anomaly")
    severity: AnomalySeverity = Field(..., description="Severity level based on impact and deviation")
    status: AnomalyStatus = Field(default=AnomalyStatus.OPEN, description="Current investigation status")

    title: str = Field(..., description="Executive summary title of the anomaly")
    description: str = Field(..., description="Detailed description of the anomalous behavior")

    # Cloud context & entity lineage
    cloud_provider: str = Field(..., description="Cloud provider (AWS, GCP, Azure, etc.)")
    service_id: str = Field(..., description="Service identifier (e.g. AmazonEC2, AmazonBedrock)")
    resource_id: Optional[str] = Field(default=None, description="Resource ARN or ID if localized")
    workload_id: Optional[str] = Field(default=None, description="Engineering workload identifier")
    product_feature_id: Optional[str] = Field(default=None, description="Associated product feature identifier")

    # Time frame
    detected_date: date = Field(..., description="Date the anomaly was first identified")
    start_date: date = Field(..., description="Start date of the anomalous activity")
    end_date: Optional[date] = Field(default=None, description="End date of the anomalous activity if bounded")

    # Financial & Statistical metrics
    actual_cost: Decimal = Field(..., description="Actual aggregate cost during the anomalous window")
    expected_baseline_cost: Decimal = Field(..., description="Expected baseline cost for the same window")
    cost_impact: Decimal = Field(..., description="Dollar impact = Actual Cost - Baseline Cost")
    currency: str = Field(default="USD", description="Currency code")

    z_score: Optional[float] = Field(default=None, description="Standard deviations away from mean")
    percentage_increase: Optional[float] = Field(default=None, description="Percentage deviation over baseline")

    # Bounded Evidence for AI Agent investigation
    evidence: Dict[str, Any] = Field(
        default_factory=dict,
        description="Structured forensic evidence (daily costs, tokens, tags, metrics)",
    )
    root_cause_hint: Optional[str] = Field(default=None, description="Heuristic hint for the AI investigator")


class AnomalyDetectionSummary(BaseModel):
    """Aggregate execution summary from an anomaly detection scan."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    organization_id: uuid.UUID = Field(..., description="Organization boundary UUID")
    evaluated_records_count: int = Field(default=0, description="Total billing records analyzed")
    evaluated_days_count: int = Field(default=0, description="Number of distinct days covered")
    anomalies_detected_count: int = Field(default=0, description="Total anomalous events flagged")
    total_cost_impact: Decimal = Field(default=Decimal("0.0000"), description="Total dollar impact of anomalies")
    currency: str = Field(default="USD", description="Currency code")

    by_severity: Dict[str, int] = Field(default_factory=dict, description="Count breakdown by severity")
    by_type: Dict[str, int] = Field(default_factory=dict, description="Count breakdown by anomaly type")
    anomalies: List[DetectedAnomaly] = Field(default_factory=list, description="List of detected anomalies")

    def summary(self) -> Dict[str, Any]:
        """Produces a clean executive summary dictionary."""
        return {
            "organization_id": str(self.organization_id),
            "evaluated_records": self.evaluated_records_count,
            "evaluated_days": self.evaluated_days_count,
            "anomalies_detected": self.anomalies_detected_count,
            "total_cost_impact": f"{self.total_cost_impact:.2f}",
            "currency": self.currency,
            "by_severity": self.by_severity,
            "by_type": self.by_type,
        }
