"""Health and Readiness probes."""
from __future__ import annotations
from fastapi import APIRouter
from services.hermes_adapter.adapter import HermesDeepSeekAdapter
from .settings import settings

router = APIRouter(tags=["Health"])

@router.get("/health")
@router.get("/healthz")
@router.get("/v1/health")
def liveness():
    adapter = HermesDeepSeekAdapter(
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
        default_model=settings.deepseek_model_id,
    )
    health = adapter.health()
    return {
        "status": "HEALTHY",
        "service": settings.app_title,
        "version": settings.app_version,
        "hermes": health,
    }

@router.get("/readyz")
def readiness():
    return {
        "status": "READY",
        "model_configured": bool(settings.deepseek_api_key),
    }
