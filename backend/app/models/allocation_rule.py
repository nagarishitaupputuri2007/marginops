"""AllocationRule model for tag-based and usage-based infrastructure cost attribution."""
import uuid
from decimal import Decimal
from typing import Optional, TYPE_CHECKING
from sqlalchemy import (
    String,
    Integer,
    Numeric,
    Boolean,
    Enum as SQLEnum,
    ForeignKey,
    ForeignKeyConstraint,
    CheckConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, UUIDPrimaryKeyMixin, TimestampMixin
from app.models.enums import AllocationRuleType, AllocationTargetType

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.cost_center import CostCenter
    from app.models.product_feature import ProductFeature


class AllocationRule(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Declarative rule attributing cloud line items and shared services to features or cost centers."""
    __tablename__ = "allocation_rules"
    __table_args__ = (
        CheckConstraint(
            "(target_type = 'PRODUCT_FEATURE' AND product_feature_id IS NOT NULL) OR "
            "(target_type = 'COST_CENTER' AND cost_center_id IS NOT NULL)",
            name="chk_allocation_rule_target_validity",
        ),
        CheckConstraint(
            "allocation_percentage IS NULL OR (allocation_percentage >= 0 AND allocation_percentage <= 100)",
            name="chk_allocation_rule_percentage_range",
        ),
        # Enforce that product feature target belongs strictly to the SAME organization
        ForeignKeyConstraint(
            ["organization_id", "product_feature_id"],
            ["product_features.organization_id", "product_features.id"],
            ondelete="CASCADE",
            name="fk_allocation_rule_product_feature_same_org",
        ),
        # Enforce that cost center target belongs strictly to the SAME organization
        ForeignKeyConstraint(
            ["organization_id", "cost_center_id"],
            ["cost_centers.organization_id", "cost_centers.id"],
            ondelete="CASCADE",
            name="fk_allocation_rule_cost_center_same_org",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    rule_type: Mapped[AllocationRuleType] = mapped_column(
        SQLEnum(AllocationRuleType, native_enum=False, length=50),
        nullable=False,
    )
    target_type: Mapped[AllocationTargetType] = mapped_column(
        SQLEnum(AllocationTargetType, native_enum=False, length=50),
        nullable=False,
    )

    # Destination targets
    product_feature_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )
    cost_center_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )

    # Matching criteria
    tag_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    tag_value: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    allocation_percentage: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
    )
    priority: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="allocation_rules",
        foreign_keys=[organization_id],
    )
    product_feature: Mapped[Optional["ProductFeature"]] = relationship(
        "ProductFeature",
        back_populates="allocation_rules",
        foreign_keys=[product_feature_id],
        overlaps="allocation_rules,product_feature,organization",
    )
    cost_center: Mapped[Optional["CostCenter"]] = relationship(
        "CostCenter",
        back_populates="allocation_rules",
        foreign_keys=[cost_center_id],
        overlaps="allocation_rules,cost_center,organization",
    )

    def __repr__(self) -> str:
        return f"<AllocationRule(id={self.id}, name='{self.name}', type='{self.rule_type.value}')>"
