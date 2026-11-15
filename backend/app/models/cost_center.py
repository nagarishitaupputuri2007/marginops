"""CostCenter model for organizational cost grouping and hierarchies."""
import uuid
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import String, Text, ForeignKey, ForeignKeyConstraint, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, UUIDPrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.budget import Budget
    from app.models.product_feature import ProductFeature
    from app.models.allocation_rule import AllocationRule


class CostCenter(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Organizational boundary grouping cloud infrastructure expenditure."""
    __tablename__ = "cost_centers"
    __table_args__ = (
        UniqueConstraint("organization_id", "code", name="uq_cost_center_org_code"),
        # Composite unique constraint allowing composite foreign keys for tenant isolation
        UniqueConstraint("organization_id", "id", name="uq_cost_centers_org_id"),
        # Enforce that parent cost center belongs strictly to the SAME organization
        ForeignKeyConstraint(
            ["organization_id", "parent_id"],
            ["cost_centers.organization_id", "cost_centers.id"],
            ondelete="SET NULL",
            name="fk_cost_center_parent_same_org",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    owner_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Optional self-referential parent/child hierarchy
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="cost_centers",
        foreign_keys=[organization_id],
    )
    parent: Mapped[Optional["CostCenter"]] = relationship(
        "CostCenter",
        remote_side=lambda: [CostCenter.id],
        foreign_keys=[parent_id],
        back_populates="children",
        overlaps="cost_centers,organization",
    )
    children: Mapped[List["CostCenter"]] = relationship(
        "CostCenter",
        back_populates="parent",
        foreign_keys=[parent_id],
        overlaps="cost_centers,organization",
    )
    budgets: Mapped[List["Budget"]] = relationship(
        "Budget",
        back_populates="cost_center",
        foreign_keys="[Budget.cost_center_id]",
        overlaps="cost_center,organization,budgets",
    )
    product_features: Mapped[List["ProductFeature"]] = relationship(
        "ProductFeature",
        back_populates="cost_center",
        foreign_keys="[ProductFeature.cost_center_id]",
        overlaps="cost_center,organization,product_features",
    )
    allocation_rules: Mapped[List["AllocationRule"]] = relationship(
        "AllocationRule",
        back_populates="cost_center",
        foreign_keys="[AllocationRule.cost_center_id]",
        overlaps="cost_center,organization,allocation_rules",
    )

    def __repr__(self) -> str:
        return f"<CostCenter(id={self.id}, code='{self.code}', name='{self.name}')>"
