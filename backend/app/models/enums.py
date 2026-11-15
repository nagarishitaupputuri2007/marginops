"""Domain enumerations for MarginOps infrastructure, budgeting, and unit economics."""
import enum


class CloudProvider(str, enum.Enum):
    """Supported cloud infrastructure and orchestration providers."""
    AWS = "AWS"
    GCP = "GCP"
    AZURE = "AZURE"
    KUBERNETES = "KUBERNETES"


class CloudAccountStatus(str, enum.Enum):
    """Operational connection status of a linked cloud account."""
    ACTIVE = "ACTIVE"
    PENDING_VERIFICATION = "PENDING_VERIFICATION"
    DISCONNECTED = "DISCONNECTED"
    ERROR = "ERROR"


class BudgetPeriod(str, enum.Enum):
    """Time cadence for budget tracking."""
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    ANNUAL = "ANNUAL"


class BudgetStatus(str, enum.Enum):
    """Current state of a budget limit."""
    ACTIVE = "ACTIVE"
    EXCEEDED = "EXCEEDED"
    EXPIRED = "EXPIRED"
    ARCHIVED = "ARCHIVED"


class UnitMetricType(str, enum.Enum):
    """Classification of product unit economic drivers."""
    REQUEST_COUNT = "REQUEST_COUNT"
    ACTIVE_USER = "ACTIVE_USER"
    AI_TOKEN = "AI_TOKEN"
    DATA_VOLUME_GB = "DATA_VOLUME_GB"
    COMPUTE_HOUR = "COMPUTE_HOUR"
    CUSTOM = "CUSTOM"


class AllocationRuleType(str, enum.Enum):
    """Strategy used to attribute infrastructure costs to product entities."""
    TAG_EXACT = "TAG_EXACT"
    TAG_PREFIX = "TAG_PREFIX"
    USAGE_PROPORTIONAL = "USAGE_PROPORTIONAL"
    FIXED_PERCENTAGE = "FIXED_PERCENTAGE"


class AllocationTargetType(str, enum.Enum):
    """Destination entity for allocated infrastructure expenditure."""
    PRODUCT_FEATURE = "PRODUCT_FEATURE"
    COST_CENTER = "COST_CENTER"


class ImportBatchStatus(str, enum.Enum):
    """Execution status of a billing data import batch."""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

