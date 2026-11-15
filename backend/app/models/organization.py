"""Organization model representing the primary tenant boundary."""
from typing import List, TYPE_CHECKING
from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, UUIDPrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.cloud_account import CloudAccount
    from app.models.cost_center import CostCenter
    from app.models.budget import Budget
    from app.models.product_feature import ProductFeature
    from app.models.unit_metric import UnitMetric
    from app.models.allocation_rule import AllocationRule
    from app.models.import_batch import ImportBatch


class Organization(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Primary tenant boundary encapsulating all infrastructure and financial entities."""
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships to tenant-scoped entities
    cloud_accounts: Mapped[List["CloudAccount"]] = relationship(
        "CloudAccount",
        back_populates="organization",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    cost_centers: Mapped[List["CostCenter"]] = relationship(
        "CostCenter",
        back_populates="organization",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    budgets: Mapped[List["Budget"]] = relationship(
        "Budget",
        back_populates="organization",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    product_features: Mapped[List["ProductFeature"]] = relationship(
        "ProductFeature",
        back_populates="organization",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    unit_metrics: Mapped[List["UnitMetric"]] = relationship(
        "UnitMetric",
        back_populates="organization",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    allocation_rules: Mapped[List["AllocationRule"]] = relationship(
        "AllocationRule",
        back_populates="organization",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    import_batches: Mapped[List["ImportBatch"]] = relationship(
        "ImportBatch",
        back_populates="organization",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<Organization(id={self.id}, name='{self.name}', slug='{self.slug}')>"
