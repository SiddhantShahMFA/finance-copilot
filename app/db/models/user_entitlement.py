import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PlanEnum(str, enum.Enum):
    free = "free"
    premium = "premium"


class EntitlementStatusEnum(str, enum.Enum):
    active = "active"
    inactive = "inactive"
    expired = "expired"


class EntitlementSourceEnum(str, enum.Enum):
    manual = "manual"


class UserEntitlement(Base):
    __tablename__ = "user_entitlements"

    user_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    plan: Mapped[PlanEnum] = mapped_column(Enum(PlanEnum), nullable=False, default=PlanEnum.free)
    status: Mapped[EntitlementStatusEnum] = mapped_column(
        Enum(EntitlementStatusEnum), nullable=False, default=EntitlementStatusEnum.active
    )
    source: Mapped[EntitlementSourceEnum] = mapped_column(
        Enum(EntitlementSourceEnum), nullable=False, default=EntitlementSourceEnum.manual
    )
    expiry_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
