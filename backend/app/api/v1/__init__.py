"""API v1 master router mounting all domain resource endpoints."""

from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.chat import router as chat_router
from app.api.v1.companies import router as companies_router
from app.api.v1.evals import router as evals_router
from app.api.v1.mcp_servers import router as mcp_router
from app.api.v1.memory import router as memory_router
from app.api.v1.reports import router as reports_router
from app.api.v1.runs import router as runs_router
from app.api.v1.schedules import router as schedules_router
from app.api.v1.signals import router as signals_router

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(auth_router)
api_v1_router.include_router(chat_router)
api_v1_router.include_router(companies_router)
api_v1_router.include_router(signals_router)
api_v1_router.include_router(reports_router)
api_v1_router.include_router(schedules_router)
api_v1_router.include_router(mcp_router)
api_v1_router.include_router(memory_router)
api_v1_router.include_router(runs_router)
api_v1_router.include_router(evals_router)
