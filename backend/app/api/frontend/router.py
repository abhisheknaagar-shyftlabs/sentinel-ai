from fastapi import APIRouter

from app.api.frontend import auth, dashboard, development, executive, integrations, production, settings

frontend_router = APIRouter()
frontend_router.include_router(auth.router)
frontend_router.include_router(integrations.router)
frontend_router.include_router(settings.router)
frontend_router.include_router(development.router)
frontend_router.include_router(production.router)
frontend_router.include_router(executive.router)
frontend_router.include_router(dashboard.router)
