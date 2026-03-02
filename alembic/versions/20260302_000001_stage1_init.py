"""stage1 init

Revision ID: 20260302_000001
Revises:
Create Date: 2026-03-02 00:00:01
"""

from alembic import op
import sqlalchemy as sa


revision = "20260302_000001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    plan_enum = sa.Enum("free", "premium", name="planenum")
    status_enum = sa.Enum("active", "inactive", "expired", name="entitlementstatusenum")
    source_enum = sa.Enum("manual", name="entitlementsourceenum")

    plan_enum.create(op.get_bind(), checkfirst=True)
    status_enum.create(op.get_bind(), checkfirst=True)
    source_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "user_entitlements",
        sa.Column("user_id", sa.String(length=128), primary_key=True, nullable=False),
        sa.Column("plan", plan_enum, nullable=False),
        sa.Column("status", status_enum, nullable=False),
        sa.Column("source", source_enum, nullable=False),
        sa.Column("expiry_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "financial_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("month", sa.Date(), nullable=False),
        sa.Column("income_total", sa.Numeric(14, 2), nullable=False),
        sa.Column("expense_total", sa.Numeric(14, 2), nullable=False),
        sa.Column("assets_total", sa.Numeric(14, 2), nullable=False),
        sa.Column("liabilities_total", sa.Numeric(14, 2), nullable=False),
        sa.Column("emi_total", sa.Numeric(14, 2), nullable=False),
        sa.Column("liquid_assets", sa.Numeric(14, 2), nullable=False),
        sa.Column("essential_expense", sa.Numeric(14, 2), nullable=False),
        sa.Column("credit_limit_total", sa.Numeric(14, 2), nullable=False),
        sa.Column("credit_outstanding_total", sa.Numeric(14, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "month", name="uq_financial_snapshots_user_month"),
    )
    op.create_index("ix_financial_snapshots_user_id", "financial_snapshots", ["user_id"], unique=False)

    op.create_table(
        "admin_audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("actor_user_id", sa.String(length=128), nullable=False),
        sa.Column("target_user_id", sa.String(length=128), nullable=False),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("admin_audit_logs")
    op.drop_index("ix_financial_snapshots_user_id", table_name="financial_snapshots")
    op.drop_table("financial_snapshots")
    op.drop_table("user_entitlements")

    source_enum = sa.Enum("manual", name="entitlementsourceenum")
    status_enum = sa.Enum("active", "inactive", "expired", name="entitlementstatusenum")
    plan_enum = sa.Enum("free", "premium", name="planenum")

    source_enum.drop(op.get_bind(), checkfirst=True)
    status_enum.drop(op.get_bind(), checkfirst=True)
    plan_enum.drop(op.get_bind(), checkfirst=True)
