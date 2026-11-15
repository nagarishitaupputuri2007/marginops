"""Pydantic v2 Telemetry Event Schemas for MarginOps."""
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, Optional, Union
from uuid import UUID, uuid4

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class TelemetryEventType(str, Enum):
    """Controlled event classification types for infrastructure and AI telemetry."""
    LLM_INFERENCE = "llm_inference"
    EMBEDDING = "embedding"
    API_REQUEST = "api_request"
    BACKGROUND_JOB = "background_job"
    DATABASE_QUERY = "database_query"
    STORAGE_OPERATION = "storage_operation"
    PIPELINE_RUN = "pipeline_run"
    CUSTOM = "custom"


class TelemetryStatus(str, Enum):
    """Operational status classifications for telemetry events."""
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"
    CANCELLED = "cancelled"


class TokenUsage(BaseModel):
    """Token consumption metrics for AI/LLM workloads."""
    model_config = ConfigDict(extra="forbid")

    prompt_tokens: int = Field(
        default=0,
        ge=0,
        description="Number of input/prompt tokens consumed",
    )
    completion_tokens: int = Field(
        default=0,
        ge=0,
        description="Number of generated/completion tokens produced",
    )
    total_tokens: Optional[int] = Field(
        default=None,
        ge=0,
        description="Total tokens billed or consumed. If omitted, computed as prompt_tokens + completion_tokens.",
    )

    @model_validator(mode="after")
    def calculate_or_validate_total(self) -> "TokenUsage":
        computed = self.prompt_tokens + self.completion_tokens
        if self.total_tokens is None:
            self.total_tokens = computed
        elif self.total_tokens < computed:
            raise ValueError(
                f"total_tokens ({self.total_tokens}) cannot be less than prompt_tokens ({self.prompt_tokens}) + completion_tokens ({self.completion_tokens}) = {computed}"
            )
        return self


class TelemetryEvent(BaseModel):
    """Pydantic v2 schema representing a telemetry and cost event stored in MongoDB."""
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=False,
    )

    # Identifiers
    event_id: str = Field(
        default_factory=lambda: str(uuid4()),
        validation_alias=AliasChoices("event_id", "id", "_id"),
        description="Unique identifier for the telemetry event",
    )
    organization_id: UUID = Field(
        ...,
        validation_alias=AliasChoices("organization_id", "tenant_id"),
        description="Tenant organization boundary UUID",
    )
    product_feature_id: Optional[UUID] = Field(
        default=None,
        validation_alias=AliasChoices("product_feature_id", "feature_id"),
        description="Associated product feature UUID for unit margin attribution",
    )

    # Classification & Context
    event_type: Union[TelemetryEventType, str] = Field(
        ...,
        description="Classification of the telemetry event (e.g., llm_inference, api_request)",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when the event occurred",
    )
    trace_id: Optional[str] = Field(
        default=None,
        max_length=128,
        description="Distributed trace identifier for request correlation",
    )
    workload_id: Optional[str] = Field(
        default=None,
        max_length=128,
        description="Identifier of batch job, service, or container workload",
    )

    # Provider & Model Metadata
    provider: Optional[str] = Field(
        default=None,
        max_length=64,
        description="Cloud or AI provider (e.g., openai, anthropic, aws, gcp, azure)",
    )
    ai_model: Optional[str] = Field(
        default=None,
        max_length=128,
        description="AI/ML model name or checkpoint (e.g., gpt-4o, claude-3-5-sonnet)",
    )

    # Resource Metrics & Cost
    tokens: Optional[TokenUsage] = Field(
        default=None,
        validation_alias=AliasChoices("tokens", "token_usage"),
        description="Token consumption details for AI model inference",
    )
    latency_ms: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Duration/latency of the operation in milliseconds",
    )
    cost_estimate: Optional[Decimal] = Field(
        default=None,
        ge=Decimal("0.0"),
        description="Estimated or calculated cost of the operation in USD",
    )

    # Status & Diagnostics
    status: TelemetryStatus = Field(
        default=TelemetryStatus.SUCCESS,
        description="Operational outcome of the event",
    )
    error_message: Optional[str] = Field(
        default=None,
        max_length=1024,
        description="Sanitized failure description if status is error or timeout",
    )

    # Flexible Attributes & Dimensions
    attributes: Dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary custom dimensions, tags, prompt versions, and user metadata",
    )

    @field_validator("timestamp", mode="after")
    @classmethod
    def enforce_utc_timestamp(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError(
                "Timestamp must be timezone-aware (e.g. UTC ISO 8601 string or datetime with tzinfo=timezone.utc)"
            )
        return v.astimezone(timezone.utc)

    @field_validator("event_type", mode="before")
    @classmethod
    def normalize_event_type(cls, v: Any) -> Any:
        if isinstance(v, str):
            v_clean = v.strip().lower()
            if not v_clean:
                raise ValueError("event_type cannot be empty")
            try:
                return TelemetryEventType(v_clean)
            except ValueError:
                return v_clean
        elif isinstance(v, TelemetryEventType):
            return v
        raise ValueError("event_type must be a string or TelemetryEventType")

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, v: Any) -> Any:
        if isinstance(v, str):
            v_clean = v.strip().lower()
            try:
                return TelemetryStatus(v_clean)
            except ValueError:
                valid = [s.value for s in TelemetryStatus]
                raise ValueError(f"Invalid status '{v}'. Allowed values: {valid}")
        return v

    @model_validator(mode="before")
    @classmethod
    def consolidate_tokens_input(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Consolidate top-level prompt_tokens / completion_tokens if tokens is not provided
            if "tokens" not in data and "token_usage" not in data:
                has_prompt = "prompt_tokens" in data
                has_completion = "completion_tokens" in data
                has_total = "total_tokens" in data
                if has_prompt or has_completion or has_total:
                    data = dict(data)
                    data["tokens"] = {
                        "prompt_tokens": data.pop("prompt_tokens", 0),
                        "completion_tokens": data.pop("completion_tokens", 0),
                        "total_tokens": data.pop("total_tokens", None),
                    }
        return data

    def to_mongo_doc(self) -> Dict[str, Any]:
        """Converts the telemetry event into a BSON-friendly dictionary for MongoDB storage."""
        return {
            "_id": self.event_id,
            "organization_id": str(self.organization_id),
            "product_feature_id": str(self.product_feature_id) if self.product_feature_id else None,
            "event_type": self.event_type.value if isinstance(self.event_type, TelemetryEventType) else self.event_type,
            "timestamp": self.timestamp,
            "trace_id": self.trace_id,
            "workload_id": self.workload_id,
            "provider": self.provider,
            "ai_model": self.ai_model,
            "tokens": self.tokens.model_dump() if self.tokens else None,
            "latency_ms": self.latency_ms,
            "cost_estimate": str(self.cost_estimate) if self.cost_estimate is not None else None,
            "status": self.status.value if isinstance(self.status, TelemetryStatus) else str(self.status),
            "error_message": self.error_message,
            "attributes": self.attributes,
        }

    @classmethod
    def from_mongo(cls, doc: Dict[str, Any]) -> "TelemetryEvent":
        """Reconstructs a TelemetryEvent from a raw MongoDB document."""
        data = dict(doc)
        if "timestamp" in data and isinstance(data["timestamp"], datetime) and data["timestamp"].tzinfo is None:
            data["timestamp"] = data["timestamp"].replace(tzinfo=timezone.utc)
        return cls.model_validate(data)
