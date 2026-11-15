"""Pydantic models and data structures for synthetic cloud billing data generation."""
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class BillingRecord(BaseModel):
    """Pydantic model representing a single normalized cloud billing line item."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    billing_date: str = Field(..., description="Billing date in YYYY-MM-DD format")
    cloud_provider: str = Field(..., description="Cloud provider (AWS, GCP, Azure)")
    account_id: str = Field(..., description="Cloud account or subscription identifier")
    service_id: str = Field(..., description="Canonical service identifier")
    service_name: str = Field(..., description="Human-readable cloud service name")
    resource_id: str = Field(..., description="Unique cloud resource identifier or ARN")
    usage_type: str = Field(..., description="Provider usage type or operation code")
    usage_quantity: Decimal = Field(..., description="Quantity of service consumed")
    unit_of_measurement: str = Field(..., description="Unit of measurement (Hours, GB-Mo, Tokens, Requests)")
    currency: str = Field(default="USD", description="Billing currency")
    cost: Decimal = Field(..., description="Calculated usage cost before credits")
    billing_amount: Decimal = Field(..., description="Net billed amount (negative for credits/refunds)")
    workload_id: str = Field(..., description="Attributed engineering workload identifier")
    product_feature_id: str = Field(..., description="Attributed product feature identifier")
    resource_tags: str = Field(..., description="JSON-serialized key-value resource tags")

    def to_csv_row(self) -> List[str]:
        """Converts the billing record to a CSV row list."""
        return [
            self.billing_date,
            self.cloud_provider,
            self.account_id,
            self.service_id,
            self.service_name,
            self.resource_id,
            self.usage_type,
            f"{self.usage_quantity:.4f}",
            self.unit_of_measurement,
            self.currency,
            f"{self.cost:.4f}",
            f"{self.billing_amount:.4f}",
            self.workload_id,
            self.product_feature_id,
            self.resource_tags,
        ]

    @classmethod
    def csv_header(cls) -> List[str]:
        """Returns standard CSV header list."""
        return [
            "billing_date",
            "cloud_provider",
            "account_id",
            "service_id",
            "service_name",
            "resource_id",
            "usage_type",
            "usage_quantity",
            "unit_of_measurement",
            "currency",
            "cost",
            "billing_amount",
            "workload_id",
            "product_feature_id",
            "resource_tags",
        ]


class ScenarioGroundTruth(BaseModel):
    """Ground-truth metadata defining an injected FinOps scenario or billing anomaly."""
    scenario_id: str = Field(..., description="Unique scenario identifier (e.g., SCENARIO-COMPUTE-SPIKE-001)")
    scenario_type: str = Field(..., description="Type: compute_spike, storage_leak, ai_token_surge, underutilized_resource, credit_refund")
    title: str = Field(..., description="Short descriptive title of the scenario")
    description: str = Field(..., description="Detailed explanation of the cause, manifestation, and remediation")
    cloud_provider: str = Field(..., description="Affected cloud provider")
    target_service: str = Field(..., description="Affected cloud service")
    target_resource_id: str = Field(..., description="Affected resource identifier")
    target_workload_id: str = Field(..., description="Affected engineering workload identifier")
    target_product_feature_id: str = Field(..., description="Affected product feature identifier")
    start_date: str = Field(..., description="Inclusive start date (YYYY-MM-DD)")
    end_date: str = Field(..., description="Inclusive end date (YYYY-MM-DD)")
    expected_cost_impact: Decimal = Field(..., description="Estimated excess spend or credit magnitude in USD")
    currency: str = Field(default="USD", description="Currency of cost impact")
    detection_criteria: Dict[str, Any] = Field(..., description="Recommended detection metrics and threshold criteria")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional context or operational notes")


class DatasetManifest(BaseModel):
    """Overall dataset metadata and ground-truth scenario registry."""
    dataset_name: str
    version: str
    generated_at: str
    seed: int
    days_covered: int
    start_date: str
    end_date: str
    total_records: int
    total_gross_cost: Decimal
    total_credits: Decimal
    total_net_cost: Decimal
    currency: str = "USD"
    providers: List[str]
    services: List[str]
    workloads: List[str]
    features: List[str]
    scenarios: List[ScenarioGroundTruth]


class GenerationConfig(BaseModel):
    """Configuration options for synthetic billing simulation."""
    start_date: date = Field(default=date(2026, 7, 18), description="Starting date of the 120-day timeline")
    days: int = Field(default=120, ge=1, le=1000, description="Duration in days to generate")
    seed: int = Field(default=42, description="Random seed for deterministic reproducibility")
    currency: str = Field(default="USD", description="Default billing currency")
