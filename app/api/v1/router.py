from fastapi import APIRouter

from app.api.v1.endpoints.admin_subscriptions import router as admin_router
from app.api.v1.endpoints.copilot import router as copilot_router
from app.api.v1.endpoints.entitlements import router as entitlement_router
from app.api.v1.endpoints.financial_snapshots import router as snapshots_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.premium import router as premium_router

api_router = APIRouter(prefix="/v1")
api_router.include_router(health_router)
api_router.include_router(snapshots_router)
api_router.include_router(entitlement_router)
api_router.include_router(admin_router)
api_router.include_router(premium_router)
api_router.include_router(copilot_router)
