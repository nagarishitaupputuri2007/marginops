"""Data models, enums, and results for deterministic cost attribution."""
import enum
import uuid
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import AllocationRuleType, AllocationTargetType, CloudProvider


class AttributionMethod(str, enum.Enum):
    """Categorization of how an infrastructure cost was attributed."""
    DIRECT_FEATURE = "DIRECT_FEATURE"
    DIRECT_WORKLOAD = "DIRECT_WORKLOAD"
    TAG_EXACT = "TAG_EXACT"
    TAG_PREFIX = "TAG_PREFIX"
    FIXED_PERCENTAGE = "FIXED_PERCENTAGE"
    USAGE_PROPORTIONAL = "USAGE_PROPORTIONAL"
    UNALLOCATED = "UNALLOCATED"


class UnallocatedReason(str, enum.Enum):
    """Specific explanation why a cost record or remainder could not be attributed."""
    NO_MATCHING_RULE = "NO_MATCHING_RULE"
    PARTIAL_ALLOCATION_REMAINDER = "PARTIAL_ALLOCATION_REMAINDER"
    MISSING_USAGE_WEIGHTS = "MISSING_USAGE_WEIGHTS"
    ZERO_TOTAL_WEIGHT = "ZERO_TOTAL_WEIGHT"
    INVALID_TARGET = "INVALID_TARGET"
    CROSS_ORG_REFERENCE_REJECTED = "CROSS_ORG_REFERENCE_REJECTED"
    UNMAPPED_WORKLOAD = "UNMAPPED_WORKLOAD"
    RULE_INACTIVE = "RULE_INACTIVE"


class CostAttributionError(Exception):
    """Base exception for cost attribution errors."""
    pass


class ReconciliationError(CostAttributionError):
    """Raised when the sum of allocated and unallocated costs does not equal source cost."""
    pass


class TenantIsolationError(CostAttributionError):
    """Raised when an operation attempts to breach tenant boundaries."""
    pass


class InvalidAllocationRuleError(CostAttributionError):
    """Raised when an allocation rule has invalid configurations or percentages."""
    pass


class AttributedCostItem(BaseModel):
    """An individual attributed cost line item representing a target allocation or unallocated portion."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, description="Unique attribution item identifier")
    cost_record_id: Optional[uuid.UUID] = Field(default=None, description="Source CostRecord UUID if applicable")
    organization_id: uuid.UUID = Field(..., description="Organization (tenant) UUID")
    billing_date: Optional[date] = Field(default=None, description="Date of infrastructure consumption")
    cloud_provider: Optional[str] = Field(default=None, description="Cloud provider (AWS, GCP, Azure, etc.)")
    service_id: Optional[str] = Field(default=None, description="Identifier of the cloud service")
    resource_id: Optional[str] = Field(default=None, description="Identifier of the specific cloud resource")
    
    # Attribution destination
    target_type: Optional[AllocationTargetType] = Field(
        default=None,
        description="Target category (PRODUCT_FEATURE or COST_CENTER), or None if unallocated",
    )
    target_id: Optional[uuid.UUID] = Field(
        default=None,
        description="UUID of the destination ProductFeature or CostCenter",
    )
    product_feature_id: Optional[uuid.UUID] = Field(default=None, description="Resolved ProductFeature UUID")
    cost_center_id: Optional[uuid.UUID] = Field(default=None, description="Resolved CostCenter UUID")
    workload_id: Optional[str] = Field(default=None, description="Workload identifier from source record")

    # Method & rule tracking
    attribution_method: AttributionMethod = Field(..., description="Method used to attribute this cost")
    rule_id: Optional[uuid.UUID] = Field(default=None, description="UUID of the matching AllocationRule if applicable")
    rule_name: Optional[str] = Field(default=None, description="Name of the matching AllocationRule if applicable")
    allocation_percentage: Decimal = Field(
        default=Decimal("100.00"),
        description="Percentage of source line item represented by this item",
    )

    # Financial amount (exact Decimal, preserving negative signs for credits/refunds)
    allocated_amount: Decimal = Field(..., description="Exact financial amount allocated to this item")
    currency: str = Field(default="USD", description="Currency code (e.g., USD)")
    is_credit: bool = Field(default=False, description="Flag indicating if this item is a credit or refund")

    # Allocation status
    is_allocated: bool = Field(default=True, description="True if attributed to a feature/cost center; False if unallocated")
    unallocated_reason: Optional[UnallocatedReason] = Field(
        default=None,
        description="Reason why this item was not allocated, if applicable",
    )


class AttributionResult(BaseModel):
    """Aggregate result and financial audit report of a cost attribution execution."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    organization_id: uuid.UUID = Field(..., description="Organization (tenant) UUID")
    total_source_records: int = Field(default=0, description="Total input records evaluated")
    total_source_amount: Decimal = Field(default=Decimal("0.0000"), description="Sum of input record amounts")
    total_allocated_items: int = Field(default=0, description="Count of attributed items generated")
    total_allocated_amount: Decimal = Field(default=Decimal("0.0000"), description="Total amount successfully allocated")
    total_unallocated_items: int = Field(default=0, description="Count of unallocated items generated")
    total_unallocated_amount: Decimal = Field(default=Decimal("0.0000"), description="Total unallocated amount preserved")
    currency: str = Field(default="USD", description="Currency code")
    items: List[AttributedCostItem] = Field(default_factory=list, description="All attributed and unallocated items")

    @property
    def is_reconciled(self) -> bool:
        """Verifies strict conservation of money: Source == Allocated + Unallocated."""
        return self.reconciliation_delta == Decimal("0")

    @property
    def reconciliation_delta(self) -> Decimal:
        """Computes deviation between source amount and total accounted amount."""
        accounted = self.total_allocated_amount + self.total_unallocated_amount
        return self.total_source_amount - accounted

    @property
    def allocated_items(self) -> List[AttributedCostItem]:
        """Returns only successfully allocated cost items."""
        return [item for item in self.items if item.is_allocated]

    @property
    def unallocated_items(self) -> List[AttributedCostItem]:
        """Returns only unallocated cost items."""
        return [item for item in self.items if not item.is_allocated]

    @property
    def by_feature(self) -> Dict[uuid.UUID, Decimal]:
        """Aggregates allocated amounts by ProductFeature UUID."""
        summary: Dict[uuid.UUID, Decimal] = {}
        for item in self.allocated_items:
            if item.product_feature_id is not None:
                summary[item.product_feature_id] = (
                    summary.get(item.product_feature_id, Decimal("0.0000")) + item.allocated_amount
                )
        return summary

    @property
    def by_cost_center(self) -> Dict[uuid.UUID, Decimal]:
        """Aggregates allocated amounts by CostCenter UUID."""
        summary: Dict[uuid.UUID, Decimal] = {}
        for item in self.allocated_items:
            if item.cost_center_id is not None:
                summary[item.cost_center_id] = (
                    summary.get(item.cost_center_id, Decimal("0.0000")) + item.allocated_amount
                )
        return summary

    @property
    def by_method(self) -> Dict[str, Decimal]:
        """Aggregates amounts by attribution method."""
        summary: Dict[str, Decimal] = {}
        for item in self.items:
            method_key = item.attribution_method.value
            summary[method_key] = summary.get(method_key, Decimal("0.0000")) + item.allocated_amount
        return summary

    def reconcile_or_raise(self) -> None:
        """Raises ReconciliationError if financial conservation is violated."""
        if not self.is_reconciled:
            raise ReconciliationError(
                f"Financial reconciliation failed for organization {self.organization_id}: "
                f"source={self.total_source_amount}, "
                f"allocated={self.total_allocated_amount}, "
                f"unallocated={self.total_unallocated_amount}, "
                f"delta={self.reconciliation_delta}"
            )

    def summary(self) -> Dict[str, Any]:
        """Produces a human-readable summary dictionary of the attribution execution."""
        return {
            "organization_id": str(self.organization_id),
            "total_source_records": self.total_source_records,
            "total_source_amount": f"{self.total_source_amount:.4f}",
            "total_allocated_items": self.total_allocated_items,
            "total_allocated_amount": f"{self.total_allocated_amount:.4f}",
            "total_unallocated_items": self.total_unallocated_items,
            "total_unallocated_amount": f"{self.total_unallocated_amount:.4f}",
            "is_reconciled": self.is_reconciled,
            "reconciliation_delta": f"{self.reconciliation_delta:.4f}",
            "currency": self.currency,
            "by_method": {k: f"{v:.4f}" for k, v in self.by_method.items()},
        }
