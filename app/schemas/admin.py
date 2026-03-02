from datetime import datetime

from pydantic import BaseModel


class AdminOverviewResponse(BaseModel):
    total_registered_users: int
    monthly_active_users: int
    total_premium_users: int
    conversion_rate: float


class SubscriptionItem(BaseModel):
    user_id: str
    user_name: str | None
    contact: str | None
    plan: str
    status: str
    start_date: datetime | None
    expiry_date: datetime | None
    payment_status: str


class SubscriptionsResponse(BaseModel):
    items: list[SubscriptionItem]


class AIUsageResponse(BaseModel):
    total_prompts_used: int
    avg_prompts_per_user: float
    top_asked_questions: list[str]
    failed_prompts: int


class DataHealthResponse(BaseModel):
    linked_bank_accounts_count: int
    linked_mf_count: int
    linked_stock_accounts_count: int
    avg_assets_per_user: float


class AdminActionResponse(BaseModel):
    success: bool
    action: str
    user_id: str
    message: str
