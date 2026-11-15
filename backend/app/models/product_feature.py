"""ProductFeature model for granular unit economics and feature-level cost attribution."""
import uuid
from decimal import Decimal
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import (
    String,
    Text,
    Numeric,
    Boolean,
    ForeignKey,
    ForeignKeyConstraint,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, UUIDPrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.cost_center import CostCenter
    from app.models.unit_metric import UnitMetric
    from app.models.allocation_rule import AllocationRule


class ProductFeature(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Customer-facing or internal product feature whose unit economics are tracked."""
    __tablename__ = "product_features"
    __table_args__ = (
        UniqueConstraint("organization_id", "slug", name="uq_product_feature_org_slug"),
        # Composite unique constraint allowing composite foreign keys for tenant isolation
        UniqueConstraint("organization_id", "id", name="uq_product_features_org_id"),
        # Enforce that associated cost center belongs strictly to the SAME organization
        ForeignKeyConstraint(
            ["organization_id", "cost_center_id"],
            ["cost_centers.organization_id", "cost_centers.id"],
            ondelete="SET NULL",
            name="fk_product_feature_cost_center_same_org",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    cost_center_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tier: Mapped[str] = mapped_column(String(50), default="core", nullable=False)
    target_gross_margin_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("75.00"),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="product_features",
        foreign_keys=[organization_id],
    )
    cost_center: Mapped[Optional["CostCenter"]] = relationship(
        "CostCenter",
        back_populates="product_features",
        foreign_keys=[cost_center_id],
        overlaps="product_features,cost_center,organization",
    )
    unit_metrics: Mapped[List["UnitMetric"]] = relationship(
        "UnitMetric",
        back_populates="product_feature",
        cascade="all, delete-orphan",
        passive_deletes=True,
        foreign_keys="[UnitMetric.product_feature_id]",
        overlaps="unit_metrics,product_feature,organization",
    )
    allocation_rules: Mapped[List["AllocationRule"]] = relationship(
        "AllocationRule",
        back_populates="product_feature",
        foreign_keys="[AllocationRule.product_feature_id]",
        overlaps="allocation_rules,product_feature,organization",
    )

    def __repr__(self) -> str:
        return f"<ProductFeature(id={self.id}, name='{self.name}', slug='{self.slug}')>"
