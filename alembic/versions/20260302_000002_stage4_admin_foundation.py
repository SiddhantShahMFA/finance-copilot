"""stage4 admin foundation

Revision ID: 20260302_000002
Revises: 20260302_000001
Create Date: 2026-03-02 00:00:02
"""

from alembic import op
import sqlalchemy as sa


revision = "20260302_000002"
down_revision = "20260302_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_prompt_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("question", sa.String(length=1024), nullable=False),
        sa.Column("intent_id", sa.String(length=128), nullable=True),
        sa.Column("tier", sa.String(length=32), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_ai_prompt_logs_user_id", "ai_prompt_logs", ["user_id"], unique=False)

    op.create_table(
        "account_links",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("account_type", sa.String(length=32), nullable=False),
        sa.Column("provider", sa.String(length=128), nullable=False),
        sa.Column("external_account_id", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_account_links_user_id", "account_links", ["user_id"], unique=False)
    op.create_index("ix_account_links_account_type", "account_links", ["account_type"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_account_links_account_type", table_name="account_links")
    op.drop_index("ix_account_links_user_id", table_name="account_links")
    op.drop_table("account_links")

    op.drop_index("ix_ai_prompt_logs_user_id", table_name="ai_prompt_logs")
    op.drop_table("ai_prompt_logs")
