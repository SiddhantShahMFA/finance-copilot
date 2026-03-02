from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


class FinancialSnapshotIn(BaseModel):
    month: date
    income_total: Decimal = Field(ge=0)
    expense_total: Decimal = Field(ge=0)
    assets_total: Decimal = Field(ge=0)
    liabilities_total: Decimal = Field(ge=0)
    emi_total: Decimal = Field(ge=0)
    liquid_assets: Decimal = Field(ge=0)
    essential_expense: Decimal = Field(ge=0)
    credit_limit_total: Decimal = Field(ge=0)
    credit_outstanding_total: Decimal = Field(ge=0)

    @field_validator("month", mode="before")
    @classmethod
    def normalize_month(cls, value):
        if isinstance(value, str) and len(value) == 7:
            return date.fromisoformat(f"{value}-01")
        if isinstance(value, date):
            return value.replace(day=1)
        raise ValueError("month must be YYYY-MM or a valid date")


class FinancialSnapshotOut(BaseModel):
    user_id: str
    month: date
    income_total: Decimal
    expense_total: Decimal
    assets_total: Decimal
    liabilities_total: Decimal
    emi_total: Decimal
    liquid_assets: Decimal
    essential_expense: Decimal
    credit_limit_total: Decimal
    credit_outstanding_total: Decimal

    model_config = {"from_attributes": True}
