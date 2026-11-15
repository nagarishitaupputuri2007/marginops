"""Unit tests for Pydantic v2 Telemetry Event Schemas and MongoDB Index Configuration."""
import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

from pydantic import ValidationError
from pymongo import ASCENDING, DESCENDING
from pymongo.operations import IndexModel

from app.schemas.telemetry import (
    TelemetryEvent,
    TelemetryEventType,
    TelemetryStatus,
    TokenUsage,
)
from app.core.mongo import (
    TELEMETRY_COLLECTION,
    get_telemetry_index_models,
    init_telemetry_indexes,
)


# ==============================================================================
# 1. TokenUsage Schema Tests
# ==============================================================================

def test_token_usage_auto_computes_total():
    """Omitting total_tokens auto-computes prompt_tokens + completion_tokens."""
    usage = TokenUsage(prompt_tokens=150, completion_tokens=75)
    assert usage.prompt_tokens == 150
    assert usage.completion_tokens == 75
    assert usage.total_tokens == 225


def test_token_usage_allows_higher_total_tokens():
    """Allows total_tokens >= prompt + completion (e.g. reasoning/cached tokens)."""
    usage = TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=170)
    assert usage.total_tokens == 170


def test_token_usage_rejects_total_less_than_sum():
    """Rejects total_tokens that is strictly less than prompt + completion."""
    with pytest.raises(ValidationError) as exc_info:
        TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=120)
    assert "total_tokens (120) cannot be less than prompt_tokens (100) + completion_tokens (50) = 150" in str(exc_info.value)


@pytest.mark.parametrize("field,value", [
    ("prompt_tokens", -1),
    ("completion_tokens", -10),
    ("total_tokens", -5),
])
def test_token_usage_rejects_negative_values(field, value):
    """Rejects negative values for any token count field."""
    with pytest.raises(ValidationError) as exc_info:
        TokenUsage(**{field: value})
    assert "Input should be greater than or equal to 0" in str(exc_info.value)


# ==============================================================================
# 2. TelemetryEvent Schema Valid Case Tests
# ==============================================================================

def test_minimal_valid_telemetry_event():
    """Minimal valid event requires only organization_id and event_type."""
    org_id = uuid4()
    event = TelemetryEvent(
        organization_id=org_id,
        event_type=TelemetryEventType.LLM_INFERENCE,
    )
    assert event.organization_id == org_id
    assert event.event_type == TelemetryEventType.LLM_INFERENCE
    assert event.status == TelemetryStatus.SUCCESS
    assert event.timestamp.tzinfo is not None
    assert event.attributes == {}
    assert event.tokens is None
    assert event.latency_ms is None
    assert UUID(event.event_id)  # Auto-generated valid UUID string


def test_full_valid_telemetry_event():
    """Valid event with all fields specified."""
    org_id = uuid4()
    feature_id = uuid4()
    now_utc = datetime.now(timezone.utc)
    event = TelemetryEvent(
        organization_id=org_id,
        product_feature_id=feature_id,
        event_type="api_request",
        timestamp=now_utc,
        trace_id="tr-abc-12345",
        workload_id="worker-pod-88",
        provider="openai",
        ai_model="gpt-4o",
        tokens=TokenUsage(prompt_tokens=200, completion_tokens=100),
        latency_ms=342.5,
        cost_estimate=Decimal("0.004500"),
        status=TelemetryStatus.SUCCESS,
        attributes={"user_id": "usr_99", "tier": "enterprise"},
    )
    assert event.organization_id == org_id
    assert event.product_feature_id == feature_id
    assert event.event_type == TelemetryEventType.API_REQUEST
    assert event.timestamp == now_utc
    assert event.trace_id == "tr-abc-12345"
    assert event.workload_id == "worker-pod-88"
    assert event.provider == "openai"
    assert event.ai_model == "gpt-4o"
    assert event.tokens.total_tokens == 300
    assert event.latency_ms == 342.5
    assert event.cost_estimate == Decimal("0.004500")
    assert event.attributes["user_id"] == "usr_99"


def test_aliases_tenant_id_and_feature_id():
    """Supports tenant_id and feature_id as aliases."""
    org_id = uuid4()
    feature_id = uuid4()
    payload = {
        "tenant_id": str(org_id),
        "feature_id": str(feature_id),
        "event_type": "llm_inference",
        "token_usage": {"prompt_tokens": 50, "completion_tokens": 25},
    }
    event = TelemetryEvent.model_validate(payload)
    assert event.organization_id == org_id
    assert event.product_feature_id == feature_id
    assert event.tokens.total_tokens == 75


def test_flat_tokens_consolidation():
    """Flat prompt_tokens and completion_tokens are consolidated into tokens."""
    org_id = uuid4()
    payload = {
        "organization_id": org_id,
        "event_type": "llm_inference",
        "prompt_tokens": 120,
        "completion_tokens": 60,
    }
    event = TelemetryEvent.model_validate(payload)
    assert event.tokens is not None
    assert event.tokens.prompt_tokens == 120
    assert event.tokens.completion_tokens == 60
    assert event.tokens.total_tokens == 180


def test_utc_timezone_conversion_from_offset():
    """Non-UTC timezone-aware timestamp is normalized to UTC."""
    org_id = uuid4()
    # IST (+05:30): 17:30 IST is 12:00 UTC
    ist_tz = timezone(timedelta(hours=5, minutes=30))
    ist_dt = datetime(2026, 11, 15, 17, 30, 0, tzinfo=ist_tz)

    event = TelemetryEvent(
        organization_id=org_id,
        event_type="pipeline_run",
        timestamp=ist_dt,
    )
    assert event.timestamp.tzinfo == timezone.utc
    assert event.timestamp.hour == 12
    assert event.timestamp.minute == 0


def test_mongo_serialization_and_deserialization():
    """Verify to_mongo_doc produces BSON-ready dictionary and from_mongo reconstructs model."""
    org_id = uuid4()
    feature_id = uuid4()
    event = TelemetryEvent(
        organization_id=org_id,
        product_feature_id=feature_id,
        event_type=TelemetryEventType.LLM_INFERENCE,
        provider="anthropic",
        ai_model="claude-3-5-sonnet",
        tokens=TokenUsage(prompt_tokens=500, completion_tokens=200),
        latency_ms=890.2,
        cost_estimate=Decimal("0.015000"),
        attributes={"tags": ["billing", "ai"]},
    )
    doc = event.to_mongo_doc()
    assert doc["_id"] == event.event_id
    assert doc["organization_id"] == str(org_id)
    assert doc["product_feature_id"] == str(feature_id)
    assert doc["event_type"] == "llm_inference"
    assert doc["tokens"]["total_tokens"] == 700
    assert doc["cost_estimate"] == "0.015000"

    # Reconstruct from raw MongoDB document
    reconstructed = TelemetryEvent.from_mongo(doc)
    assert reconstructed.event_id == event.event_id
    assert reconstructed.organization_id == org_id
    assert reconstructed.product_feature_id == feature_id
    assert reconstructed.event_type == TelemetryEventType.LLM_INFERENCE
    assert reconstructed.tokens.total_tokens == 700


# ==============================================================================
# 3. TelemetryEvent Schema Invalid Case Tests (Validation Rejection)
# ==============================================================================

def test_rejects_missing_organization_id():
    """Rejects payload without organization_id or tenant_id."""
    with pytest.raises(ValidationError) as exc_info:
        TelemetryEvent.model_validate({"event_type": "llm_inference"})
    assert "organization_id" in str(exc_info.value)


def test_rejects_invalid_uuid_organization_id():
    """Rejects malformed organization_id string."""
    with pytest.raises(ValidationError) as exc_info:
        TelemetryEvent(
            organization_id="not-a-valid-uuid",
            event_type="llm_inference",
        )
    assert "Input should be a valid UUID" in str(exc_info.value)


def test_rejects_empty_event_type():
    """Rejects empty or blank event_type string."""
    org_id = uuid4()
    with pytest.raises(ValidationError) as exc_info:
        TelemetryEvent(organization_id=org_id, event_type="   ")
    assert "event_type cannot be empty" in str(exc_info.value)


def test_rejects_naive_timestamp_datetime():
    """Rejects timezone-naive datetime instances."""
    org_id = uuid4()
    naive_dt = datetime(2026, 11, 15, 12, 0, 0)  # tzinfo=None
    with pytest.raises(ValidationError) as exc_info:
        TelemetryEvent(organization_id=org_id, event_type="llm_inference", timestamp=naive_dt)
    assert "Timestamp must be timezone-aware" in str(exc_info.value)


def test_rejects_naive_timestamp_string():
    """Rejects ISO 8601 string without timezone offset."""
    org_id = uuid4()
    with pytest.raises(ValidationError) as exc_info:
        TelemetryEvent.model_validate({
            "organization_id": str(org_id),
            "event_type": "llm_inference",
            "timestamp": "2026-11-15T12:00:00",  # No Z or +00:00
        })
    assert "Timestamp must be timezone-aware" in str(exc_info.value)


def test_rejects_negative_latency():
    """Rejects negative latency_ms."""
    org_id = uuid4()
    with pytest.raises(ValidationError) as exc_info:
        TelemetryEvent(
            organization_id=org_id,
            event_type="llm_inference",
            latency_ms=-10.0,
        )
    assert "Input should be greater than or equal to 0" in str(exc_info.value)


def test_rejects_negative_cost_estimate():
    """Rejects negative cost_estimate."""
    org_id = uuid4()
    with pytest.raises(ValidationError) as exc_info:
        TelemetryEvent(
            organization_id=org_id,
            event_type="llm_inference",
            cost_estimate=Decimal("-0.01"),
        )
    assert "Input should be greater than or equal to 0" in str(exc_info.value)


def test_rejects_invalid_status():
    """Rejects unknown status string."""
    org_id = uuid4()
    with pytest.raises(ValidationError) as exc_info:
        TelemetryEvent(
            organization_id=org_id,
            event_type="llm_inference",
            status="unrecognized_status",
        )
    assert "Invalid status 'unrecognized_status'" in str(exc_info.value)


# ==============================================================================
# 4. MongoDB Index Configuration & Async Initialization Tests
# ==============================================================================

def test_telemetry_index_models_specification():
    """Verifies that all 6 required indexes are defined with correct keys and options."""
    index_models = get_telemetry_index_models()
    assert len(index_models) == 6

    index_map = {idx.document["name"]: idx.document for idx in index_models}

    # 1. Primary Tenant + Timestamp Compound Index
    assert "ix_telemetry_org_timestamp" in index_map
    assert index_map["ix_telemetry_org_timestamp"]["key"] == {
        "organization_id": ASCENDING,
        "timestamp": DESCENDING,
    }

    # 2. Tenant + Feature + Timestamp Compound Index
    assert "ix_telemetry_org_feature_timestamp" in index_map
    assert index_map["ix_telemetry_org_feature_timestamp"]["key"] == {
        "organization_id": ASCENDING,
        "product_feature_id": ASCENDING,
        "timestamp": DESCENDING,
    }

    # 3. Tenant + Event Type + Timestamp Compound Index
    assert "ix_telemetry_org_event_timestamp" in index_map
    assert index_map["ix_telemetry_org_event_timestamp"]["key"] == {
        "organization_id": ASCENDING,
        "event_type": ASCENDING,
        "timestamp": DESCENDING,
    }

    # 4. Tenant + Provider + AI Model + Timestamp Compound Index
    assert "ix_telemetry_org_provider_model_timestamp" in index_map
    assert index_map["ix_telemetry_org_provider_model_timestamp"]["key"] == {
        "organization_id": ASCENDING,
        "provider": ASCENDING,
        "ai_model": ASCENDING,
        "timestamp": DESCENDING,
    }

    # 5. Distributed Trace ID Sparse Index
    assert "ix_telemetry_trace_id" in index_map
    assert index_map["ix_telemetry_trace_id"]["key"] == {"trace_id": ASCENDING}
    assert index_map["ix_telemetry_trace_id"].get("sparse") is True

    # 6. Tenant + Workload ID + Timestamp Sparse Compound Index
    assert "ix_telemetry_org_workload_timestamp" in index_map
    assert index_map["ix_telemetry_org_workload_timestamp"]["key"] == {
        "organization_id": ASCENDING,
        "workload_id": ASCENDING,
        "timestamp": DESCENDING,
    }
    assert index_map["ix_telemetry_org_workload_timestamp"].get("sparse") is True


@pytest.mark.asyncio
async def test_init_telemetry_indexes_with_mock_db():
    """Verifies that init_telemetry_indexes creates indexes on the collection asynchronously."""
    mock_collection = MagicMock()
    expected_names = [
        "ix_telemetry_org_timestamp",
        "ix_telemetry_org_feature_timestamp",
        "ix_telemetry_org_event_timestamp",
        "ix_telemetry_org_provider_model_timestamp",
        "ix_telemetry_trace_id",
        "ix_telemetry_org_workload_timestamp",
    ]
    mock_collection.create_indexes = AsyncMock(return_value=expected_names)

    mock_db = MagicMock()
    mock_db.__getitem__.return_value = mock_collection

    created = await init_telemetry_indexes(db=mock_db)

    # Verify collection access
    mock_db.__getitem__.assert_called_once_with(TELEMETRY_COLLECTION)

    # Verify create_indexes was awaited
    mock_collection.create_indexes.assert_awaited_once()

    # Verify the argument was a list of IndexModel objects
    args, _ = mock_collection.create_indexes.call_args
    passed_indexes = args[0]
    assert len(passed_indexes) == 6
    assert all(isinstance(idx, IndexModel) for idx in passed_indexes)
    assert created == expected_names
