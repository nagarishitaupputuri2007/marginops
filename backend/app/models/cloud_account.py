"""CloudAccount model representing linked infrastructure providers."""
import uuid
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Enum as SQLEnum, ForeignKey, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, UUIDPrimaryKeyMixin, TimestampMixin
from app.models.enums import CloudProvider, CloudAccountStatus

if TYPE_CHECKING:
    from app.models.organization import Organization


class CloudAccount(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Linked cloud provider or cluster metadata for cost ingestion."""
    __tablename__ = "cloud_accounts"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "provider",
            "account_identifier",
            name="uq_cloud_account_org_provider_account",
        ),
        UniqueConstraint("organization_id", "id", name="uq_cloud_accounts_org_id"),
        Index("ix_cloud_account_org_provider", "organization_id", "provider"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    provider: Mapped[CloudProvider] = mapped_column(
        SQLEnum(CloudProvider, native_enum=False, length=50),
        nullable=False,
        index=True,
    )
    account_identifier: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[CloudAccountStatus] = mapped_column(
        SQLEnum(CloudAccountStatus, native_enum=False, length=50),
        default=CloudAccountStatus.ACTIVE,
        nullable=False,
    )
    environment: Mapped[str] = mapped_column(String(50), default="production", nullable=False)
    credentials_arn: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization", back_populates="cloud_accounts")

    def __repr__(self) -> str:
        return f"<CloudAccount(id={self.id}, provider='{self.provider.value}', identifier='{self.account_identifier}')>"
