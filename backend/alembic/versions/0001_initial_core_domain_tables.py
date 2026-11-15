"""Create initial core domain tables

Revision ID: 0001_initial_core_domain_tables
Revises: 
Create Date: 2026-11-15 17:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001_initial_core_domain_tables"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. organizations
    op.create_table(
        "organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("currency", sa.String(length=3), server_default="USD", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_organizations_name"),
        sa.UniqueConstraint("slug", name="uq_organizations_slug"),
    )
    op.create_index("ix_organizations_name", "organizations", ["name"], unique=True)
    op.create_index("ix_organizations_slug", "organizations", ["slug"], unique=True)

    # 2. cloud_accounts
    op.create_table(
        "cloud_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("account_identifier", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=50), server_default="ACTIVE", nullable=False),
        sa.Column("environment", sa.String(length=50), server_default="production", nullable=False),
        sa.Column("credentials_arn", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "provider",
            "account_identifier",
            name="uq_cloud_account_org_provider_account",
        ),
    )
    op.create_index("ix_cloud_accounts_organization_id", "cloud_accounts", ["organization_id"], unique=False)
    op.create_index("ix_cloud_account_org_provider", "cloud_accounts", ["organization_id", "provider"], unique=False)

    # 3. cost_centers
    op.create_table(
        "cost_centers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("owner_email", sa.String(length=255), nullable=True),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["organization_id", "parent_id"],
            ["cost_centers.organization_id", "cost_centers.id"],
            ondelete="SET NULL",
            name="fk_cost_center_parent_same_org",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "code", name="uq_cost_center_org_code"),
        sa.UniqueConstraint("organization_id", "id", name="uq_cost_centers_org_id"),
    )
    op.create_index("ix_cost_centers_organization_id", "cost_centers", ["organization_id"], unique=False)
    op.create_index("ix_cost_centers_parent_id", "cost_centers", ["parent_id"], unique=False)

    # 4. budgets
    op.create_table(
        "budgets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cost_center_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("amount", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("period", sa.String(length=20), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("alert_threshold_percent", sa.Numeric(precision=5, scale=2), server_default="80.00", nullable=False),
        sa.Column("status", sa.String(length=20), server_default="ACTIVE", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("amount >= 0", name="chk_budget_amount_positive"),
        sa.CheckConstraint(
            "alert_threshold_percent >= 0 AND alert_threshold_percent <= 100",
            name="chk_budget_alert_threshold_range",
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["organization_id", "cost_center_id"],
            ["cost_centers.organization_id", "cost_centers.id"],
            ondelete="SET NULL",
            name="fk_budget_cost_center_same_org",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_budgets_cost_center_id", "budgets", ["cost_center_id"], unique=False)
    op.create_index("ix_budgets_organization_id", "budgets", ["organization_id"], unique=False)

    # 5. product_features
    op.create_table(
        "product_features",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cost_center_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("tier", sa.String(length=50), server_default="core", nullable=False),
        sa.Column(
            "target_gross_margin_percent",
            sa.Numeric(precision=5, scale=2),
            server_default="75.00",
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["organization_id", "cost_center_id"],
            ["cost_centers.organization_id", "cost_centers.id"],
            ondelete="SET NULL",
            name="fk_product_feature_cost_center_same_org",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "slug", name="uq_product_feature_org_slug"),
        sa.UniqueConstraint("organization_id", "id", name="uq_product_features_org_id"),
    )
    op.create_index("ix_product_features_cost_center_id", "product_features", ["cost_center_id"], unique=False)
    op.create_index("ix_product_features_organization_id", "product_features", ["organization_id"], unique=False)

    # 6. unit_metrics
    op.create_table(
        "unit_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_feature_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("metric_type", sa.String(length=50), nullable=False),
        sa.Column("unit_name", sa.String(length=50), nullable=False),
        sa.Column("target_cost_per_unit", sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column("currency", sa.String(length=3), server_default="USD", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["organization_id", "product_feature_id"],
            ["product_features.organization_id", "product_features.id"],
            ondelete="CASCADE",
            name="fk_unit_metric_product_feature_same_org",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "name", name="uq_unit_metric_org_name"),
    )
    op.create_index("ix_unit_metrics_metric_type", "unit_metrics", ["metric_type"], unique=False)
    op.create_index("ix_unit_metrics_organization_id", "unit_metrics", ["organization_id"], unique=False)
    op.create_index("ix_unit_metrics_product_feature_id", "unit_metrics", ["product_feature_id"], unique=False)

    # 7. allocation_rules
    op.create_table(
        "allocation_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("rule_type", sa.String(length=50), nullable=False),
        sa.Column("target_type", sa.String(length=50), nullable=False),
        sa.Column("product_feature_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("cost_center_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tag_key", sa.String(length=255), nullable=True),
        sa.Column("tag_value", sa.String(length=255), nullable=True),
        sa.Column("allocation_percentage", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("priority", sa.Integer(), server_default="100", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "(target_type = 'PRODUCT_FEATURE' AND product_feature_id IS NOT NULL) OR "
            "(target_type = 'COST_CENTER' AND cost_center_id IS NOT NULL)",
            name="chk_allocation_rule_target_validity",
        ),
        sa.CheckConstraint(
            "allocation_percentage IS NULL OR (allocation_percentage >= 0 AND allocation_percentage <= 100)",
            name="chk_allocation_rule_percentage_range",
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["organization_id", "product_feature_id"],
            ["product_features.organization_id", "product_features.id"],
            ondelete="CASCADE",
            name="fk_allocation_rule_product_feature_same_org",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "cost_center_id"],
            ["cost_centers.organization_id", "cost_centers.id"],
            ondelete="CASCADE",
            name="fk_allocation_rule_cost_center_same_org",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_allocation_rules_cost_center_id", "allocation_rules", ["cost_center_id"], unique=False)
    op.create_index("ix_allocation_rules_organization_id", "allocation_rules", ["organization_id"], unique=False)
    op.create_index("ix_allocation_rules_product_feature_id", "allocation_rules", ["product_feature_id"], unique=False)


def downgrade() -> None:
    op.drop_table("allocation_rules")
    op.drop_table("unit_metrics")
    op.drop_table("product_features")
    op.drop_table("budgets")
    op.drop_table("cost_centers")
    op.drop_table("cloud_accounts")
    op.drop_table("organizations")
