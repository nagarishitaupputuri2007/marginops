"""Data structures and validation models for cloud billing ingestion."""
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class RowValidationError(BaseModel):
    """Encapsulates a validation or parsing error for a specific row."""
    row_number: int = Field(..., description="1-based file row number where the error occurred")
    field: Optional[str] = Field(default=None, description="Column or attribute that failed validation")
    error: str = Field(..., description="Human-readable explanation of why the row is invalid")
    raw_data: Optional[Dict[str, str]] = Field(default=None, description="Raw dictionary of row data if available")


class ParsedBillingRecord(BaseModel):
    """Normalized, strongly-typed billing record produced by ingestion parsers."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    row_number: int = Field(..., description="1-based row number in the ingested source")
    billing_date: date = Field(..., description="Date of service consumption")
    cloud_provider: str = Field(..., description="Canonical cloud provider (AWS, GCP, Azure)")
    account_id: str = Field(..., description="Cloud account, project, or subscription ID")
    service_id: str = Field(..., description="Canonical service identifier")
    service_name: str = Field(..., description="Human-readable service name")
    resource_id: str = Field(..., description="Unique resource identifier or ARN")
    usage_type: str = Field(..., description="Detailed usage type or SKU")
    usage_quantity: Decimal = Field(..., description="Quantity of service consumed")
    unit_of_measurement: str = Field(..., description="Unit of measurement")
    currency: str = Field(default="USD", description="Currency code (e.g., USD)")
    cost: Decimal = Field(..., description="Calculated charge before credits")
    billing_amount: Decimal = Field(..., description="Net billed amount (negative for credits/refunds)")
    workload_id: str = Field(..., description="Attributed engineering workload ID")
    product_feature_id: str = Field(..., description="Attributed product feature ID")
    resource_tags: Dict[str, Any] = Field(default_factory=dict, description="Parsed resource metadata tags")
    is_credit: bool = Field(default=False, description="Flag indicating if this record represents a credit or refund")


class IngestionReport(BaseModel):
    """Comprehensive execution report returned by the billing ingestion service."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    total_rows: int = Field(default=0, description="Total data rows evaluated")
    valid_rows: int = Field(default=0, description="Count of successfully parsed records")
    invalid_rows: int = Field(default=0, description="Count of rejected or malformed rows")
    total_positive_charges: Decimal = Field(default=Decimal("0.0000"), description="Sum of all positive billing amounts")
    total_credits: Decimal = Field(default=Decimal("0.0000"), description="Sum of all negative credit/refund amounts")
    net_billing_amount: Decimal = Field(default=Decimal("0.0000"), description="Net total: positive charges + credits")
    currency: str = Field(default="USD", description="Billing currency")
    errors: List[RowValidationError] = Field(default_factory=list, description="List of row-level validation errors")
    records: List[ParsedBillingRecord] = Field(default_factory=list, description="Parsed and validated billing records")

    @property
    def is_clean(self) -> bool:
        """Returns True if all rows passed validation with zero errors."""
        return self.invalid_rows == 0 and len(self.errors) == 0

    @property
    def success_rate(self) -> float:
        """Percentage of successfully parsed rows (0.0 to 100.0)."""
        if self.total_rows == 0:
            return 0.0
        return round((self.valid_rows / self.total_rows) * 100.0, 2)

    def summary(self) -> Dict[str, Any]:
        """Returns high-level dictionary summary of the ingestion outcome."""
        return {
            "total_rows": self.total_rows,
            "valid_rows": self.valid_rows,
            "invalid_rows": self.invalid_rows,
            "success_rate_pct": self.success_rate,
            "total_positive_charges": f"{self.total_positive_charges:.4f}",
            "total_credits": f"{self.total_credits:.4f}",
            "net_billing_amount": f"{self.net_billing_amount:.4f}",
            "currency": self.currency,
            "error_count": len(self.errors),
        }
