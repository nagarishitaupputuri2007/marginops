"""Persistence service normalizing and saving validated billing records to PostgreSQL."""
import hashlib
import json
import uuid
from decimal import Decimal
from typing import Any, Dict, List, Optional, Union
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.models.enums import CloudProvider, ImportBatchStatus
from app.models.cost_record import CostRecord
from app.models.import_batch import ImportBatch
from app.services.billing_ingestion.models import IngestionReport, ParsedBillingRecord


class DuplicateImportError(Exception):
    """Raised when an import batch with the same file hash has already been processed for the organization."""

    def __init__(self, message: str, existing_batch_id: Optional[uuid.UUID] = None):
        super().__init__(message)
        self.existing_batch_id = existing_batch_id


class CostPersistenceService:
    """Service responsible for transactional persistence of normalized cost records and import batches."""

    @staticmethod
    def compute_file_hash(content: Union[str, bytes]) -> str:
        """Computes SHA-256 hash for raw billing file content or stream."""
        if isinstance(content, str):
            content = content.encode("utf-8")
        return hashlib.sha256(content).hexdigest()

    async def persist_ingestion_report(
        self,
        session: Union[AsyncSession, Session],
        organization_id: uuid.UUID,
        report: IngestionReport,
        source_filename: str,
        file_hash: Optional[str] = None,
        allow_duplicate: bool = False,
        cloud_account_map: Optional[Dict[str, uuid.UUID]] = None,
        product_feature_map: Optional[Dict[str, uuid.UUID]] = None,
    ) -> ImportBatch:
        """Persists validated billing records and import batch metadata transactionally.

        Supports both AsyncSession (production PostgreSQL asyncpg) and Session (sync test harness).

        Args:
            session: SQLAlchemy AsyncSession or Session.
            organization_id: Organization (tenant) UUID.
            report: IngestionReport containing validated records and totals.
            source_filename: Source file name or origin identifier.
            file_hash: SHA-256 idempotency hash (computed if omitted).
            allow_duplicate: If True, returns existing batch instead of raising DuplicateImportError.
            cloud_account_map: Optional mapping of account_identifier -> cloud_account_id UUID.
            product_feature_map: Optional mapping of feature_slug_or_id -> product_feature_id UUID.

        Returns:
            Saved ImportBatch instance.
        """
        if isinstance(session, AsyncSession):
            if session.in_transaction():
                return await self._execute_async(
                    session=session,
                    organization_id=organization_id,
                    report=report,
                    source_filename=source_filename,
                    file_hash=file_hash,
                    allow_duplicate=allow_duplicate,
                    cloud_account_map=cloud_account_map,
                    product_feature_map=product_feature_map,
                )
            else:
                async with session.begin():
                    return await self._execute_async(
                        session=session,
                        organization_id=organization_id,
                        report=report,
                        source_filename=source_filename,
                        file_hash=file_hash,
                        allow_duplicate=allow_duplicate,
                        cloud_account_map=cloud_account_map,
                        product_feature_map=product_feature_map,
                    )
        else:
            if session.in_transaction():
                return self._execute_sync(
                    session=session,
                    organization_id=organization_id,
                    report=report,
                    source_filename=source_filename,
                    file_hash=file_hash,
                    allow_duplicate=allow_duplicate,
                    cloud_account_map=cloud_account_map,
                    product_feature_map=product_feature_map,
                )
            else:
                with session.begin():
                    return self._execute_sync(
                        session=session,
                        organization_id=organization_id,
                        report=report,
                        source_filename=source_filename,
                        file_hash=file_hash,
                        allow_duplicate=allow_duplicate,
                        cloud_account_map=cloud_account_map,
                        product_feature_map=product_feature_map,
                    )

    def persist_ingestion_report_sync(
        self,
        session: Session,
        organization_id: uuid.UUID,
        report: IngestionReport,
        source_filename: str,
        file_hash: Optional[str] = None,
        allow_duplicate: bool = False,
        cloud_account_map: Optional[Dict[str, uuid.UUID]] = None,
        product_feature_map: Optional[Dict[str, uuid.UUID]] = None,
    ) -> ImportBatch:
        """Synchronous persistence method for standard SQLAlchemy Session."""
        if session.in_transaction():
            return self._execute_sync(
                session=session,
                organization_id=organization_id,
                report=report,
                source_filename=source_filename,
                file_hash=file_hash,
                allow_duplicate=allow_duplicate,
                cloud_account_map=cloud_account_map,
                product_feature_map=product_feature_map,
            )
        else:
            with session.begin():
                return self._execute_sync(
                    session=session,
                    organization_id=organization_id,
                    report=report,
                    source_filename=source_filename,
                    file_hash=file_hash,
                    allow_duplicate=allow_duplicate,
                    cloud_account_map=cloud_account_map,
                    product_feature_map=product_feature_map,
                )

    def _resolve_file_hash(
        self,
        organization_id: uuid.UUID,
        source_filename: str,
        report: IngestionReport,
        file_hash: Optional[str],
    ) -> str:
        if not file_hash:
            hash_payload = f"{organization_id}:{source_filename}:{report.total_rows}:{report.net_billing_amount}"
            return hashlib.sha256(hash_payload.encode("utf-8")).hexdigest()
        return file_hash

    def _build_batch_entity(
        self,
        organization_id: uuid.UUID,
        source_filename: str,
        file_hash: str,
        report: IngestionReport,
    ) -> ImportBatch:
        error_summary_json = None
        if report.errors:
            error_summary_json = json.dumps([e.model_dump() for e in report.errors[:50]])

        return ImportBatch(
            organization_id=organization_id,
            source_filename=source_filename,
            file_hash=file_hash,
            status=ImportBatchStatus.PROCESSING,
            total_rows=report.total_rows,
            valid_rows=report.valid_rows,
            invalid_rows=report.invalid_rows,
            total_positive_charges=report.total_positive_charges,
            total_credits=report.total_credits,
            net_billing_amount=report.net_billing_amount,
            currency=report.currency,
            error_summary=error_summary_json,
        )

    def _build_cost_records(
        self,
        organization_id: uuid.UUID,
        batch_id: uuid.UUID,
        report: IngestionReport,
        cloud_account_map: Optional[Dict[str, uuid.UUID]],
        product_feature_map: Optional[Dict[str, uuid.UUID]] = None,
    ) -> List[CostRecord]:
        cost_records: List[CostRecord] = []
        for record in report.records:
            cloud_account_id = None
            if cloud_account_map and record.account_id in cloud_account_map:
                cloud_account_id = cloud_account_map[record.account_id]

            # Resolve product_feature_id to UUID
            product_feature_id: Optional[uuid.UUID] = None
            raw_feature = record.product_feature_id
            if product_feature_map and raw_feature in product_feature_map:
                product_feature_id = product_feature_map[raw_feature]
            elif isinstance(raw_feature, uuid.UUID):
                product_feature_id = raw_feature
            elif isinstance(raw_feature, str) and raw_feature:
                try:
                    product_feature_id = uuid.UUID(raw_feature)
                except (ValueError, TypeError, AttributeError):
                    product_feature_id = None

            provider_key = record.cloud_provider.upper()
            provider_enum = (
                CloudProvider[provider_key]
                if provider_key in CloudProvider.__members__
                else CloudProvider.AWS
            )

            cost_record = CostRecord(
                organization_id=organization_id,
                import_batch_id=batch_id,
                cloud_account_id=cloud_account_id,
                product_feature_id=product_feature_id,
                billing_date=record.billing_date,
                cloud_provider=provider_enum,
                service_id=record.service_id,
                service_name=record.service_name,
                resource_id=record.resource_id,
                usage_type=record.usage_type,
                usage_quantity=record.usage_quantity,
                unit_of_measurement=record.unit_of_measurement,
                currency=record.currency,
                cost=record.cost,
                billing_amount=record.billing_amount,
                is_credit=record.is_credit,
                workload_id=record.workload_id,
                resource_tags=record.resource_tags,
            )
            cost_records.append(cost_record)
        return cost_records

    async def _execute_async(
        self,
        session: AsyncSession,
        organization_id: uuid.UUID,
        report: IngestionReport,
        source_filename: str,
        file_hash: Optional[str],
        allow_duplicate: bool,
        cloud_account_map: Optional[Dict[str, uuid.UUID]],
        product_feature_map: Optional[Dict[str, uuid.UUID]] = None,
    ) -> ImportBatch:
        resolved_hash = self._resolve_file_hash(organization_id, source_filename, report, file_hash)

        stmt = select(ImportBatch).where(
            ImportBatch.organization_id == organization_id,
            ImportBatch.file_hash == resolved_hash,
        )
        result = await session.execute(stmt)
        existing_batch = result.scalar_one_or_none()

        if existing_batch is not None:
            if not allow_duplicate:
                raise DuplicateImportError(
                    f"Duplicate import detected: File '{source_filename}' (hash: {resolved_hash[:12]}...) has already been imported for organization {organization_id}.",
                    existing_batch_id=existing_batch.id,
                )
            return existing_batch

        batch = self._build_batch_entity(organization_id, source_filename, resolved_hash, report)
        session.add(batch)
        await session.flush()

        cost_records = self._build_cost_records(
            organization_id, batch.id, report, cloud_account_map, product_feature_map
        )
        session.add_all(cost_records)

        batch.status = ImportBatchStatus.COMPLETED
        await session.flush()
        return batch

    def _execute_sync(
        self,
        session: Session,
        organization_id: uuid.UUID,
        report: IngestionReport,
        source_filename: str,
        file_hash: Optional[str],
        allow_duplicate: bool,
        cloud_account_map: Optional[Dict[str, uuid.UUID]],
        product_feature_map: Optional[Dict[str, uuid.UUID]] = None,
    ) -> ImportBatch:
        resolved_hash = self._resolve_file_hash(organization_id, source_filename, report, file_hash)

        stmt = select(ImportBatch).where(
            ImportBatch.organization_id == organization_id,
            ImportBatch.file_hash == resolved_hash,
        )
        result = session.execute(stmt)
        existing_batch = result.scalar_one_or_none()

        if existing_batch is not None:
            if not allow_duplicate:
                raise DuplicateImportError(
                    f"Duplicate import detected: File '{source_filename}' (hash: {resolved_hash[:12]}...) has already been imported for organization {organization_id}.",
                    existing_batch_id=existing_batch.id,
                )
            return existing_batch

        batch = self._build_batch_entity(organization_id, source_filename, resolved_hash, report)
        session.add(batch)
        session.flush()

        cost_records = self._build_cost_records(
            organization_id, batch.id, report, cloud_account_map, product_feature_map
        )
        session.add_all(cost_records)

        batch.status = ImportBatchStatus.COMPLETED
        session.flush()
        return batch
