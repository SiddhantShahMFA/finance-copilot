from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class FinancialSnapshot(Base):
    __tablename__ = "financial_snapshots"
    __table_args__ = (UniqueConstraint("user_id", "month", name="uq_financial_snapshots_user_month"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    month: Mapped[date] = mapped_column(Date, nullable=False)

    income_total: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    expense_total: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    assets_total: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    liabilities_total: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    emi_total: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    liquid_assets: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    essential_expense: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    credit_limit_total: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    credit_outstanding_total: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
