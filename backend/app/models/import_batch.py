"""ImportBatch model tracking cloud billing ingestion batches and lifecycle."""
import uuid
from decimal import Decimal
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import (
    String,
    Integer,
    Numeric,
    Text,
    Enum as SQLEnum,
    ForeignKey,
    UniqueConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, UUIDPrimaryKeyMixin, TimestampMixin
from app.models.enums import ImportBatchStatus

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.cost_record import CostRecord


class ImportBatch(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Tracks a discrete billing file ingestion batch and financial audit totals."""
    __tablename__ = "import_batches"
    __table_args__ = (
        UniqueConstraint("organization_id", "id", name="uq_import_batches_org_id"),
        UniqueConstraint("organization_id", "file_hash", name="uq_import_batch_org_file_hash"),
        Index("ix_import_batches_org_status", "organization_id", "status"),
        Index("ix_import_batches_org_created_at", "organization_id", "created_at"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[ImportBatchStatus] = mapped_column(
        SQLEnum(ImportBatchStatus, native_enum=False, length=20),
        default=ImportBatchStatus.PENDING,
        nullable=False,
    )
    total_rows: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    valid_rows: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    invalid_rows: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_positive_charges: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        default=Decimal("0.0000"),
        nullable=False,
    )
    total_credits: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        default=Decimal("0.0000"),
        nullable=False,
    )
    net_billing_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        default=Decimal("0.0000"),
        nullable=False,
    )
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    error_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization", back_populates="import_batches")
    cost_records: Mapped[List["CostRecord"]] = relationship(
        "CostRecord",
        back_populates="import_batch",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<ImportBatch(id={self.id}, filename='{self.source_filename}', status='{self.status.value}', net={self.net_billing_amount})>"
