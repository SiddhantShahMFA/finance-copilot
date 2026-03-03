"""stage5 family mode

Revision ID: 20260302_000003
Revises: 20260302_000002
Create Date: 2026-03-02 00:00:03
"""

from alembic import op
import sqlalchemy as sa


revision = "20260302_000003"
down_revision = "20260302_000002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "households",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("owner_user_id", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_households_owner_user_id", "households", ["owner_user_id"], unique=False)

    op.create_table(
        "household_members",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("household_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("household_id", "user_id", name="uq_household_member"),
    )
    op.create_index("ix_household_members_household_id", "household_members", ["household_id"], unique=False)
    op.create_index("ix_household_members_user_id", "household_members", ["user_id"], unique=False)

    op.create_table(
        "household_goals",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("household_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("target_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("current_savings", sa.Numeric(14, 2), nullable=False),
        sa.Column("remaining_months", sa.Integer(), nullable=False),
        sa.Column("monthly_contribution", sa.Numeric(14, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_household_goals_household_id", "household_goals", ["household_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_household_goals_household_id", table_name="household_goals")
    op.drop_table("household_goals")

    op.drop_index("ix_household_members_user_id", table_name="household_members")
    op.drop_index("ix_household_members_household_id", table_name="household_members")
    op.drop_table("household_members")

    op.drop_index("ix_households_owner_user_id", table_name="households")
    op.drop_table("households")
