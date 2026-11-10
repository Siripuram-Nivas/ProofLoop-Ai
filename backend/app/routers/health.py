from __future__ import annotations

from fastapi import APIRouter

from ..config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    return {
        "status": "ok",
        "service": "proofloop-api",
        "version": "1.0.0",
        "storage": "sqlite",
        "research": settings.research_provider,
        "extraction": "gemini" if settings.gemini_api_key else "deterministic",
        "image_ocr": False,
        "environment": settings.env,
    }
