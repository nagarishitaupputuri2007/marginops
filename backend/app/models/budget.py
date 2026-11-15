"""Budget model for cost tracking, ceiling limits, and alerts."""
import uuid
from datetime import date
from decimal import Decimal
from typing import Optional, TYPE_CHECKING
from sqlalchemy import (
    String,
    Numeric,
    Date,
    Enum as SQLEnum,
    ForeignKey,
    ForeignKeyConstraint,
    CheckConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, UUIDPrimaryKeyMixin, TimestampMixin
from app.models.enums import BudgetPeriod, BudgetStatus

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.cost_center import CostCenter


class Budget(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Spending limits and alert thresholds for an organization or cost center."""
    __tablename__ = "budgets"
    __table_args__ = (
        CheckConstraint("amount >= 0", name="chk_budget_amount_positive"),
        CheckConstraint(
            "alert_threshold_percent >= 0 AND alert_threshold_percent <= 100",
            name="chk_budget_alert_threshold_range",
        ),
        # Enforce that associated cost center belongs strictly to the SAME organization
        ForeignKeyConstraint(
            ["organization_id", "cost_center_id"],
            ["cost_centers.organization_id", "cost_centers.id"],
            ondelete="SET NULL",
            name="fk_budget_cost_center_same_org",
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
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    period: Mapped[BudgetPeriod] = mapped_column(
        SQLEnum(BudgetPeriod, native_enum=False, length=20),
        nullable=False,
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    alert_threshold_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("80.00"),
        nullable=False,
    )
    status: Mapped[BudgetStatus] = mapped_column(
        SQLEnum(BudgetStatus, native_enum=False, length=20),
        default=BudgetStatus.ACTIVE,
        nullable=False,
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="budgets",
        foreign_keys=[organization_id],
    )
    cost_center: Mapped[Optional["CostCenter"]] = relationship(
        "CostCenter",
        back_populates="budgets",
        foreign_keys=[cost_center_id],
        overlaps="budgets,cost_center,organization",
    )

    def __repr__(self) -> str:
        return f"<Budget(id={self.id}, name='{self.name}', amount={self.amount}, period='{self.period.value}')>"
