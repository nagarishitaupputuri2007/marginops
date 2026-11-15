"""UnitMetric model defining business unit cost drivers (per-request, per-user, per-token)."""
import uuid
from decimal import Decimal
from typing import Optional, TYPE_CHECKING
from sqlalchemy import (
    String,
    Numeric,
    Enum as SQLEnum,
    ForeignKey,
    ForeignKeyConstraint,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, UUIDPrimaryKeyMixin, TimestampMixin
from app.models.enums import UnitMetricType

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.product_feature import ProductFeature


class UnitMetric(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Unit economic metric definition mapping infrastructure spend to product activity."""
    __tablename__ = "unit_metrics"
    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_unit_metric_org_name"),
        # Enforce that associated product feature belongs strictly to the SAME organization
        ForeignKeyConstraint(
            ["organization_id", "product_feature_id"],
            ["product_features.organization_id", "product_features.id"],
            ondelete="CASCADE",
            name="fk_unit_metric_product_feature_same_org",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_feature_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    metric_type: Mapped[UnitMetricType] = mapped_column(
        SQLEnum(UnitMetricType, native_enum=False, length=50),
        nullable=False,
        index=True,
    )
    unit_name: Mapped[str] = mapped_column(String(50), nullable=False)
    target_cost_per_unit: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(18, 6),
        nullable=True,
    )
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="unit_metrics",
        foreign_keys=[organization_id],
    )
    product_feature: Mapped[Optional["ProductFeature"]] = relationship(
        "ProductFeature",
        back_populates="unit_metrics",
        foreign_keys=[product_feature_id],
        overlaps="unit_metrics,product_feature,organization",
    )

    def __repr__(self) -> str:
        return f"<UnitMetric(id={self.id}, name='{self.name}', type='{self.metric_type.value}')>"
