from pydantic import BaseModel, Field


class HouseholdCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class HouseholdMemberAddRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=128)
    role: str = Field(default="member", min_length=1, max_length=32)


class HouseholdGoalCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    target_amount: float = Field(ge=0)
    current_savings: float = Field(ge=0)
    remaining_months: int = Field(gt=0)
    monthly_contribution: float = Field(ge=0)


class HouseholdResponse(BaseModel):
    id: int
    name: str
    owner_user_id: str
    member_count: int


class HouseholdGoalResponse(BaseModel):
    id: int
    household_id: int
    name: str
    target_amount: float
    current_savings: float
    remaining_months: int
    monthly_contribution: float


class FamilyContributionItem(BaseModel):
    user_id: str
    net_worth: float
    monthly_surplus: float
    health_score: float


class FamilyOverviewResponse(BaseModel):
    household_id: int
    shared_net_worth: float
    combined_goal_target: float
    combined_goal_current_savings: float
    combined_required_monthly_saving: float
    family_health_score: float
    contribution_breakdown: list[FamilyContributionItem]
