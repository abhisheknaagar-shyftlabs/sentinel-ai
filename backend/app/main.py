from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.frontend.router import frontend_router
from app.api.v1.router import api_router
from app.config.settings import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.core.responses import success_envelope
from app.database.session import engine
from app.integrations.redis.client import close_redis
from app.middleware.request_context import RequestContextMiddleware
from app.services.health_monitor import get_health_monitor

settings = get_settings()
configure_logging(settings.log_level)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("application_startup", extra={"env": settings.app_env})
    health_monitor = get_health_monitor()
    health_monitor.start()
    yield
    await health_monitor.stop()
    await close_redis()
    await engine.dispose()
    logger.info("application_shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestContextMiddleware)

    register_exception_handlers(app)

    app.include_router(api_router, prefix=settings.api_v1_prefix)
    # Frontend adapter - raw camelCase JSON (no envelope) matching
    # frontend/API_CONTRACT.md exactly. Entirely separate from /api/v1;
    # existing endpoints are untouched.
    app.include_router(frontend_router, prefix="/api")

    @app.get("/health")
    async def root_health():
        return success_envelope({"status": "ok"}, "Service is healthy")

    return app


app = create_app()
