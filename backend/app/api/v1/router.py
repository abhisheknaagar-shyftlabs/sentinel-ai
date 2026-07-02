from fastapi import APIRouter

from app.api.v1.endpoints import auth, docker, github, health, incidents

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(github.router)
api_router.include_router(docker.router)
api_router.include_router(incidents.router)
