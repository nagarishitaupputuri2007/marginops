"""Unit tests for Normalized Cost Persistence Service, Import Batches, and DB Integrity."""
import uuid
from datetime import date
from decimal import Decimal
import pytest
from sqlalchemy import create_engine, event, select, func
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models import (
    Base,
    Organization,
    CloudAccount,
    ProductFeature,
    ImportBatch,
    CostRecord,
    CloudProvider,
    ImportBatchStatus,
)
from app.services.billing_ingestion import BillingIngestionService
from app.services.cost_persistence import CostPersistenceService, DuplicateImportError


@pytest.fixture
def db_session():
    """Provides an isolated in-memory SQLite database enforcing foreign keys."""
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, _):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


@pytest.fixture
def org_alpha(db_session: Session):
    """Creates a primary tenant organization."""
    org = Organization(
        id=uuid.uuid4(),
        name="Alpha Corp",
        slug="alpha-corp",
        currency="USD",
        is_active=True,
    )
    db_session.add(org)
    db_session.commit()
    return org


@pytest.fixture
def org_beta(db_session: Session):
    """Creates a secondary tenant organization for tenant isolation tests."""
    org = Organization(
        id=uuid.uuid4(),
        name="Beta Labs",
        slug="beta-labs",
        currency="USD",
        is_active=True,
    )
    db_session.add(org)
    db_session.commit()
    return org


@pytest.fixture
def ingestion_service():
    return BillingIngestionService()


@pytest.fixture
def persistence_service():
    return CostPersistenceService()


SAMPLE_CSV = """billing_date,cloud_provider,account_id,service_id,service_name,resource_id,usage_type,usage_quantity,unit_of_measurement,currency,cost,billing_amount,workload_id,product_feature_id,resource_tags
2026-08-01,AWS,aws-123456789012,AmazonEC2,Amazon Elastic Compute Cloud,i-01,BoxUsage:m6i.xlarge,24.0000,Hours,USD,4.6080,4.6080,workload-api,feat-ci,"{""env"": ""prod"", ""team"": ""platform""}"
2026-08-01,AWS,aws-123456789012,AmazonRDS,Amazon Relational Database Service,db-01,InstanceUsage:db.r6g,24.0000,Hours,USD,12.4800,12.4800,workload-db,feat-ci,"{""env"": ""prod""}"
2026-08-01,AWS,aws-123456789012,AWSBilling,AWS Billing,credit-startup,Credit:PromotionalDiscount,1.0000,Adjustment,USD,-2500.0000,-2500.0000,workload-fin,feat-ci,"{""type"": ""grant""}"
2026-08-01,Azure,sub-azure-ai,AzureOpenAI,Azure OpenAI Service,dep-gpt4o,TokenUsage:Inference,1200.0000,kTokens,USD,6.0000,6.0000,workload-ai,feat-copilot,"{""model"": ""gpt-4o""}"
"""


# ==============================================================================
# 1. Record Persistence and Financial Precision Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_persist_records_and_batch_header(
    db_session: Session,
    org_alpha: Organization,
    ingestion_service: BillingIngestionService,
    persistence_service: CostPersistenceService,
):
    """Verifies that an IngestionReport persists the batch header and all cost records."""
    report = ingestion_service.ingest_string(SAMPLE_CSV)
    assert report.valid_rows == 4

    batch = await persistence_service.persist_ingestion_report(
        session=db_session,
        organization_id=org_alpha.id,
        report=report,
        source_filename="sample_test_billing.csv",
        file_hash="test-hash-001",
    )
    db_session.commit()

    # Verify batch header
    assert batch.id is not None
    assert batch.organization_id == org_alpha.id
    assert batch.source_filename == "sample_test_billing.csv"
    assert batch.status == ImportBatchStatus.COMPLETED
    assert batch.total_rows == 4
    assert batch.valid_rows == 4
    assert batch.invalid_rows == 0
    assert batch.total_positive_charges == Decimal("23.0880")  # 4.6080 + 12.4800 + 6.0000
    assert batch.total_credits == Decimal("-2500.0000")
    assert batch.net_billing_amount == Decimal("-2476.9120")

    # Verify cost records in DB
    records = db_session.scalars(
        select(CostRecord).where(CostRecord.import_batch_id == batch.id).order_by(CostRecord.created_at)
    ).all()
    assert len(records) == 4

    ec2_rec = next(r for r in records if r.service_id == "AmazonEC2")
    assert ec2_rec.organization_id == org_alpha.id
    assert ec2_rec.cloud_provider == CloudProvider.AWS
    assert ec2_rec.billing_date == date(2026, 8, 1)
    assert ec2_rec.usage_quantity == Decimal("24.0000")
    assert ec2_rec.cost == Decimal("4.6080")
    assert ec2_rec.billing_amount == Decimal("4.6080")
    assert ec2_rec.is_credit is False
    assert ec2_rec.resource_tags == {"env": "prod", "team": "platform"}


# ==============================================================================
# 2. Negative Credits and Refunds Preservation
# ==============================================================================

@pytest.mark.asyncio
async def test_negative_credits_and_refunds_persisted(
    db_session: Session,
    org_alpha: Organization,
    ingestion_service: BillingIngestionService,
    persistence_service: CostPersistenceService,
):
    """Verifies that negative credits/refunds retain negative amounts in the database."""
    report = ingestion_service.ingest_string(SAMPLE_CSV)
    batch = await persistence_service.persist_ingestion_report(
        session=db_session,
        organization_id=org_alpha.id,
        report=report,
        source_filename="credits_test.csv",
        file_hash="credits-hash-001",
    )
    db_session.commit()

    credit_record = db_session.scalar(
        select(CostRecord).where(
            CostRecord.import_batch_id == batch.id,
            CostRecord.is_credit == True,
        )
    )
    assert credit_record is not None
    assert credit_record.resource_id == "credit-startup"
    assert credit_record.cost == Decimal("-2500.0000")
    assert credit_record.billing_amount == Decimal("-2500.0000")
    assert credit_record.usage_type == "Credit:PromotionalDiscount"


# ==============================================================================
# 3. Duplicate Import Prevention (Idempotency) Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_duplicate_import_prevention(
    db_session: Session,
    org_alpha: Organization,
    ingestion_service: BillingIngestionService,
    persistence_service: CostPersistenceService,
):
    """Attempting to import the same file hash for the same organization raises DuplicateImportError."""
    report = ingestion_service.ingest_string(SAMPLE_CSV)
    file_hash = "unique-file-hash-12345"

    # First import succeeds
    batch_1 = await persistence_service.persist_ingestion_report(
        session=db_session,
        organization_id=org_alpha.id,
        report=report,
        source_filename="billing_august.csv",
        file_hash=file_hash,
    )
    db_session.commit()
    assert batch_1.status == ImportBatchStatus.COMPLETED

    # Second import with identical organization and hash raises DuplicateImportError
    with pytest.raises(DuplicateImportError) as exc_info:
        await persistence_service.persist_ingestion_report(
            session=db_session,
            organization_id=org_alpha.id,
            report=report,
            source_filename="billing_august.csv",
            file_hash=file_hash,
        )
    assert "Duplicate import detected" in str(exc_info.value)
    assert exc_info.value.existing_batch_id == batch_1.id

    # Setting allow_duplicate=True returns existing batch without creating new records
    existing_batch = await persistence_service.persist_ingestion_report(
        session=db_session,
        organization_id=org_alpha.id,
        report=report,
        source_filename="billing_august.csv",
        file_hash=file_hash,
        allow_duplicate=True,
    )
    assert existing_batch.id == batch_1.id

    # Verify no duplicate records were added
    count = db_session.scalar(
        select(func.count(CostRecord.id)).where(CostRecord.import_batch_id == batch_1.id)
    )
    assert count == 4


@pytest.mark.asyncio
async def test_same_file_hash_different_organizations_allowed(
    db_session: Session,
    org_alpha: Organization,
    org_beta: Organization,
    ingestion_service: BillingIngestionService,
    persistence_service: CostPersistenceService,
):
    """The same file hash CAN be imported by two different organizations (scoped by tenant)."""
    report = ingestion_service.ingest_string(SAMPLE_CSV)
    shared_hash = "shared-cross-tenant-hash"

    batch_a = await persistence_service.persist_ingestion_report(
        session=db_session,
        organization_id=org_alpha.id,
        report=report,
        source_filename="common_billing.csv",
        file_hash=shared_hash,
    )
    batch_b = await persistence_service.persist_ingestion_report(
        session=db_session,
        organization_id=org_beta.id,
        report=report,
        source_filename="common_billing.csv",
        file_hash=shared_hash,
    )
    db_session.commit()

    assert batch_a.id != batch_b.id
    assert batch_a.organization_id == org_alpha.id
    assert batch_b.organization_id == org_beta.id


# ==============================================================================
# 4. Transaction Rollback on Failure Test
# ==============================================================================

@pytest.mark.asyncio
async def test_transaction_rollback_on_failure(
    db_session: Session,
    org_alpha: Organization,
    ingestion_service: BillingIngestionService,
    persistence_service: CostPersistenceService,
):
    """If an unhandled failure occurs during persistence, all changes roll back atomically."""
    report = ingestion_service.ingest_string(SAMPLE_CSV)

    # Intentionally corrupt the first record's cloud_provider to trigger an error
    report.records[0].cloud_provider = None  # Will fail NOT NULL constraint or validation

    with pytest.raises(Exception):
        await persistence_service.persist_ingestion_report(
            session=db_session,
            organization_id=org_alpha.id,
            report=report,
            source_filename="failing_batch.csv",
            file_hash="fail-hash-001",
        )
    db_session.rollback()

    # Verify database has zero batches and zero records for this file
    batch_count = db_session.scalar(
        select(func.count(ImportBatch.id)).where(ImportBatch.file_hash == "fail-hash-001")
    )
    assert batch_count == 0


# ==============================================================================
# 5. Organization Boundary & Foreign Key Integrity
# ==============================================================================

@pytest.mark.asyncio
async def test_cross_org_batch_reference_rejected(
    db_session: Session,
    org_alpha: Organization,
    org_beta: Organization,
    ingestion_service: BillingIngestionService,
    persistence_service: CostPersistenceService,
):
    """Enforces that a CostRecord cannot reference an ImportBatch belonging to another organization."""
    report = ingestion_service.ingest_string(SAMPLE_CSV)

    # Create batch belonging to Org Alpha
    batch_alpha = await persistence_service.persist_ingestion_report(
        session=db_session,
        organization_id=org_alpha.id,
        report=report,
        source_filename="alpha_batch.csv",
        file_hash="alpha-hash-001",
    )
    db_session.commit()

    # Attempt to insert a CostRecord under Org Beta referencing Org Alpha's batch
    cross_org_record = CostRecord(
        id=uuid.uuid4(),
        organization_id=org_beta.id,  # Belongs to Beta
        import_batch_id=batch_alpha.id,  # References Alpha's batch
        billing_date=date(2026, 8, 1),
        cloud_provider=CloudProvider.AWS,
        service_id="AmazonEC2",
        service_name="Amazon Elastic Compute Cloud",
        resource_id="i-cross-tenant-hack",
        usage_type="BoxUsage",
        usage_quantity=Decimal("1.0000"),
        unit_of_measurement="Hours",
        currency="USD",
        cost=Decimal("10.0000"),
        billing_amount=Decimal("10.0000"),
        is_credit=False,
    )
    db_session.add(cross_org_record)

    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


# ==============================================================================
# 6. ProductFeature Alignment and Constraint Tests
# ==============================================================================

def test_valid_feature_reference(db_session: Session, org_alpha: Organization):
    """CostRecord successfully references a ProductFeature in the same organization."""
    feature = ProductFeature(
        id=uuid.uuid4(),
        organization_id=org_alpha.id,
        name="Cost Intelligence",
        slug="cost-intelligence",
    )
    batch = ImportBatch(
        id=uuid.uuid4(),
        organization_id=org_alpha.id,
        source_filename="test.csv",
        file_hash="hash-valid-feat",
    )
    db_session.add_all([feature, batch])
    db_session.flush()

    record = CostRecord(
        id=uuid.uuid4(),
        organization_id=org_alpha.id,
        import_batch_id=batch.id,
        product_feature_id=feature.id,
        billing_date=date(2026, 8, 1),
        cloud_provider=CloudProvider.AWS,
        service_id="AmazonEC2",
        service_name="EC2",
        resource_id="i-test-01",
        usage_type="BoxUsage",
        usage_quantity=Decimal("1.0"),
        unit_of_measurement="Hours",
        currency="USD",
        cost=Decimal("1.0000"),
        billing_amount=Decimal("1.0000"),
        is_credit=False,
    )
    db_session.add(record)
    db_session.flush()

    assert record.product_feature_id == feature.id
    assert record.product_feature is not None
    assert record.product_feature.slug == "cost-intelligence"


def test_null_feature_reference(db_session: Session, org_alpha: Organization):
    """CostRecord with product_feature_id=None persists cleanly (nullable FK)."""
    batch = ImportBatch(
        id=uuid.uuid4(),
        organization_id=org_alpha.id,
        source_filename="test.csv",
        file_hash="hash-null-feat",
    )
    db_session.add(batch)
    db_session.flush()

    record = CostRecord(
        id=uuid.uuid4(),
        organization_id=org_alpha.id,
        import_batch_id=batch.id,
        product_feature_id=None,
        billing_date=date(2026, 8, 1),
        cloud_provider=CloudProvider.AWS,
        service_id="AmazonEC2",
        service_name="EC2",
        resource_id="i-test-02",
        usage_type="BoxUsage",
        usage_quantity=Decimal("1.0"),
        unit_of_measurement="Hours",
        currency="USD",
        cost=Decimal("2.0000"),
        billing_amount=Decimal("2.0000"),
        is_credit=False,
    )
    db_session.add(record)
    db_session.flush()

    assert record.product_feature_id is None
    assert record.product_feature is None


def test_invalid_feature_reference(db_session: Session, org_alpha: Organization):
    """CostRecord referencing a non-existent feature UUID fails foreign key validation."""
    batch = ImportBatch(
        id=uuid.uuid4(),
        organization_id=org_alpha.id,
        source_filename="test.csv",
        file_hash="hash-invalid-feat",
    )
    db_session.add(batch)
    db_session.flush()

    non_existent_feature_id = uuid.uuid4()
    record = CostRecord(
        id=uuid.uuid4(),
        organization_id=org_alpha.id,
        import_batch_id=batch.id,
        product_feature_id=non_existent_feature_id,
        billing_date=date(2026, 8, 1),
        cloud_provider=CloudProvider.AWS,
        service_id="AmazonEC2",
        service_name="EC2",
        resource_id="i-test-03",
        usage_type="BoxUsage",
        usage_quantity=Decimal("1.0"),
        unit_of_measurement="Hours",
        currency="USD",
        cost=Decimal("3.0000"),
        billing_amount=Decimal("3.0000"),
        is_credit=False,
    )
    db_session.add(record)

    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


def test_cross_organization_feature_reference_rejected(
    db_session: Session,
    org_alpha: Organization,
    org_beta: Organization,
):
    """Enforces that a CostRecord in Org Alpha CANNOT reference a ProductFeature belonging to Org Beta."""
    # Create batch in Org Alpha
    batch_alpha = ImportBatch(
        id=uuid.uuid4(),
        organization_id=org_alpha.id,
        source_filename="alpha.csv",
        file_hash="hash-alpha-cross",
    )
    # Create feature in Org Beta
    feature_beta = ProductFeature(
        id=uuid.uuid4(),
        organization_id=org_beta.id,
        name="Beta Secret Copilot",
        slug="beta-secret-copilot",
    )
    db_session.add_all([batch_alpha, feature_beta])
    db_session.flush()

    # Attempt to link Org Alpha's cost record with Org Beta's feature
    cross_tenant_record = CostRecord(
        id=uuid.uuid4(),
        organization_id=org_alpha.id,  # Org Alpha
        import_batch_id=batch_alpha.id,
        product_feature_id=feature_beta.id,  # Belongs to Org Beta!
        billing_date=date(2026, 8, 1),
        cloud_provider=CloudProvider.AWS,
        service_id="AmazonEC2",
        service_name="EC2",
        resource_id="i-cross-feat-01",
        usage_type="BoxUsage",
        usage_quantity=Decimal("1.0"),
        unit_of_measurement="Hours",
        currency="USD",
        cost=Decimal("4.0000"),
        billing_amount=Decimal("4.0000"),
        is_credit=False,
    )
    db_session.add(cross_tenant_record)

    # Composite foreign key fk_cost_record_feature_same_org MUST reject this
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()

