from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import db
from .config import BASE_DIR, settings
from .routers import auth, health, stats, uploads, verifications

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("proofloop")

DIST_DIR = BASE_DIR.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    if settings.uses_default_secret:
        logger.warning(
            "PROOFLOOP_SECRET is missing or short. Sessions are signed with the development "
            "secret; set a long random value before deploying."
        )
    logger.info(
        "ProofLoop API ready (env=%s, research=%s, extraction=%s)",
        settings.env,
        settings.research_provider,
        "gemini" if settings.gemini_api_key else "deterministic",
    )
    yield


app = FastAPI(
    title="ProofLoop AI API",
    version="1.0.0",
    description="Evidence intelligence: claims, sources, contradictions, traceable proof reports.",
    lifespan=lifespan,
)


# ---------------------------------------------------------------- rate limiting
_WINDOW_SECONDS = 60
_LIMITS = {"auth": 10, "write": 30, "read": 120}
_buckets: dict[tuple[str, str], deque[float]] = defaultdict(deque)
_bucket_lock = threading.Lock()


def _bucket_for(request: Request) -> str:
    if "/auth/" in request.url.path:
        return "auth"
    if request.method in {"POST", "PATCH", "PUT", "DELETE"}:
        return "write"
    return "read"


@app.middleware("http")
async def rate_limit(request: Request, call_next):
    if not request.url.path.startswith("/api/") or request.method == "OPTIONS":
        return await call_next(request)
    name = _bucket_for(request)
    client = request.client.host if request.client else "unknown"
    now = time.monotonic()
    with _bucket_lock:
        bucket = _buckets[(client, name)]
        while bucket and now - bucket[0] > _WINDOW_SECONDS:
            bucket.popleft()
        if len(bucket) >= _LIMITS[name]:
            retry = max(1, int(_WINDOW_SECONDS - (now - bucket[0])))
            return JSONResponse(
                status_code=429,
                headers={"Retry-After": str(retry)},
                content={
                    "error": {
                        "code": "rate_limited",
                        "message": f"Too many requests. Try again in {retry} seconds.",
                    }
                },
            )
        bucket.append(now)
    return await call_next(request)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if settings.is_production:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline' "
            "https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com data:; "
            "script-src 'self'; connect-src 'self'"
        )
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type"],
)


# ---------------------------------------------------------------- error shape
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    detail = exc.detail
    if isinstance(detail, dict) and "code" in detail:
        body = {"error": detail}
    else:
        body = {"error": {"code": "http_error", "message": str(detail)}}
    return JSONResponse(status_code=exc.status_code, content=body, headers=exc.headers)


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    messages = []
    for error in exc.errors():
        location = ".".join(str(part) for part in error.get("loc", []) if part != "body")
        message = error.get("msg", "Invalid value").removeprefix("Value error, ")
        messages.append(f"{location}: {message}" if location else message)
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "validation_error",
                "message": "; ".join(messages)[:500] or "Invalid request.",
                "details": [
                    {
                        "loc": [str(part) for part in error.get("loc", [])],
                        "msg": str(error.get("msg", "Invalid value")).removeprefix("Value error, "),
                        "type": str(error.get("type", "value_error")),
                    }
                    for error in exc.errors()[:5]
                ],
            }
        },
    )


# ---------------------------------------------------------------- routes
app.include_router(health.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(uploads.router, prefix="/api/v1")
app.include_router(verifications.router, prefix="/api/v1")
app.include_router(stats.router, prefix="/api/v1")


# ---------------------------------------------------------------- SPA serving
if DIST_DIR.exists():
    assets_dir = DIST_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Not found."})
        candidate = (DIST_DIR / full_path).resolve()
        if (
            full_path
            and candidate.is_file()
            and DIST_DIR.resolve() in candidate.parents
        ):
            return FileResponse(candidate)
        return FileResponse(DIST_DIR / "index.html")
