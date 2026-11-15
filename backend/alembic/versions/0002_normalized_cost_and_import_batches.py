"""Create normalized cost records and import batches tables

Revision ID: 0002_normalized_cost_and_import_batches
Revises: 0001_initial_core_domain_tables
Create Date: 2026-11-15 18:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0002_normalized_cost_and_import_batches"
down_revision: Union[str, None] = "0001_initial_core_domain_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 0. Add composite unique constraint to cloud_accounts for composite FK tenant isolation
    op.create_unique_constraint(
        "uq_cloud_accounts_org_id",
        "cloud_accounts",
        ["organization_id", "id"],
    )

    # 1. import_batches
    op.create_table(
        "import_batches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_filename", sa.String(length=255), nullable=False),
        sa.Column("file_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="PENDING", nullable=False),
        sa.Column("total_rows", sa.Integer(), server_default="0", nullable=False),
        sa.Column("valid_rows", sa.Integer(), server_default="0", nullable=False),
        sa.Column("invalid_rows", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_positive_charges", sa.Numeric(precision=18, scale=4), server_default="0.0000", nullable=False),
        sa.Column("total_credits", sa.Numeric(precision=18, scale=4), server_default="0.0000", nullable=False),
        sa.Column("net_billing_amount", sa.Numeric(precision=18, scale=4), server_default="0.0000", nullable=False),
        sa.Column("currency", sa.String(length=3), server_default="USD", nullable=False),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("organization_id", "id", name="uq_import_batches_org_id"),
        sa.UniqueConstraint("organization_id", "file_hash", name="uq_import_batch_org_file_hash"),
    )
    op.create_index("ix_import_batches_org_status", "import_batches", ["organization_id", "status"])
    op.create_index("ix_import_batches_org_created_at", "import_batches", ["organization_id", "created_at"])

    # 2. cost_records
    op.create_table(
        "cost_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("import_batch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cloud_account_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("billing_date", sa.Date(), nullable=False),
        sa.Column("cloud_provider", sa.String(length=50), nullable=False),
        sa.Column("service_id", sa.String(length=100), nullable=False),
        sa.Column("service_name", sa.String(length=255), nullable=False),
        sa.Column("resource_id", sa.String(length=500), nullable=False),
        sa.Column("usage_type", sa.String(length=255), nullable=False),
        sa.Column("usage_quantity", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("unit_of_measurement", sa.String(length=50), nullable=False),
        sa.Column("currency", sa.String(length=3), server_default="USD", nullable=False),
        sa.Column("cost", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("billing_amount", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("is_credit", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("workload_id", sa.String(length=100), nullable=True),
        sa.Column("product_feature_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("resource_tags", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["organization_id", "import_batch_id"],
            ["import_batches.organization_id", "import_batches.id"],
            ondelete="CASCADE",
            name="fk_cost_record_batch_same_org",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "cloud_account_id"],
            ["cloud_accounts.organization_id", "cloud_accounts.id"],
            ondelete="SET NULL",
            name="fk_cost_record_cloud_account_same_org",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "product_feature_id"],
            ["product_features.organization_id", "product_features.id"],
            ondelete="SET NULL",
            name="fk_cost_record_feature_same_org",
        ),
        sa.UniqueConstraint("organization_id", "id", name="uq_cost_records_org_id"),
    )
    op.create_index("ix_cost_records_org_billing_date", "cost_records", ["organization_id", "billing_date"])
    op.create_index("ix_cost_records_org_provider_service", "cost_records", ["organization_id", "cloud_provider", "service_id"])
    op.create_index("ix_cost_records_org_workload", "cost_records", ["organization_id", "workload_id"])
    op.create_index("ix_cost_records_org_feature", "cost_records", ["organization_id", "product_feature_id"])
    op.create_index("ix_cost_records_org_batch", "cost_records", ["organization_id", "import_batch_id"])


def downgrade() -> None:
    op.drop_table("cost_records")
    op.drop_table("import_batches")
    op.drop_constraint("uq_cloud_accounts_org_id", "cloud_accounts", type_="unique")
