from datetime import datetime

from pydantic import BaseModel


class EntitlementOut(BaseModel):
    user_id: str
    plan: str
    status: str
    source: str
    expiry_date: datetime | None

    model_config = {"from_attributes": True}


class EntitlementPatchRequest(BaseModel):
    plan: str
    status: str
    expiry_date: datetime | None = None
