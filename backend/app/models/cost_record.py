"""CostRecord model representing normalized multi-cloud infrastructure line items."""
import uuid
from datetime import date
from decimal import Decimal
from typing import Any, Dict, Optional, TYPE_CHECKING
from sqlalchemy import (
    String,
    Numeric,
    Date,
    Boolean,
    JSON,
    Enum as SQLEnum,
    ForeignKey,
    ForeignKeyConstraint,
    UniqueConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, UUIDPrimaryKeyMixin, TimestampMixin
from app.models.enums import CloudProvider

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.import_batch import ImportBatch
    from app.models.cloud_account import CloudAccount
    from app.models.product_feature import ProductFeature


class CostRecord(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Normalized, organization-scoped cloud infrastructure billing record."""
    __tablename__ = "cost_records"
    __table_args__ = (
        UniqueConstraint("organization_id", "id", name="uq_cost_records_org_id"),
        ForeignKeyConstraint(
            ["organization_id", "import_batch_id"],
            ["import_batches.organization_id", "import_batches.id"],
            ondelete="CASCADE",
            name="fk_cost_record_batch_same_org",
        ),
        ForeignKeyConstraint(
            ["organization_id", "cloud_account_id"],
            ["cloud_accounts.organization_id", "cloud_accounts.id"],
            ondelete="SET NULL",
            name="fk_cost_record_cloud_account_same_org",
        ),
        ForeignKeyConstraint(
            ["organization_id", "product_feature_id"],
            ["product_features.organization_id", "product_features.id"],
            ondelete="SET NULL",
            name="fk_cost_record_feature_same_org",
        ),
        Index("ix_cost_records_org_billing_date", "organization_id", "billing_date"),
        Index("ix_cost_records_org_provider_service", "organization_id", "cloud_provider", "service_id"),
        Index("ix_cost_records_org_workload", "organization_id", "workload_id"),
        Index("ix_cost_records_org_feature", "organization_id", "product_feature_id"),
        Index("ix_cost_records_org_batch", "organization_id", "import_batch_id"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    import_batch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    cloud_account_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )
    product_feature_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )
    billing_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    cloud_provider: Mapped[CloudProvider] = mapped_column(
        SQLEnum(CloudProvider, native_enum=False, length=50),
        nullable=False,
        index=True,
    )
    service_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    service_name: Mapped[str] = mapped_column(String(255), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    usage_type: Mapped[str] = mapped_column(String(255), nullable=False)
    usage_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    unit_of_measurement: Mapped[str] = mapped_column(String(50), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    cost: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    billing_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    is_credit: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    workload_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    resource_tags: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization",
        foreign_keys=[organization_id],
        overlaps="cost_records",
    )
    import_batch: Mapped["ImportBatch"] = relationship(
        "ImportBatch",
        back_populates="cost_records",
        foreign_keys=[import_batch_id],
    )
    cloud_account: Mapped[Optional["CloudAccount"]] = relationship(
        "CloudAccount",
        foreign_keys=[cloud_account_id],
    )
    product_feature: Mapped[Optional["ProductFeature"]] = relationship(
        "ProductFeature",
        foreign_keys=[product_feature_id],
        overlaps="cost_records",
    )

    def __repr__(self) -> str:
        return f"<CostRecord(id={self.id}, date={self.billing_date}, service='{self.service_id}', amount={self.billing_amount})>"


# Convenient alias requested by prompt
NormalizedCostRecord = CostRecord
