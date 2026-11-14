from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Optional

from fastapi import Cookie, Depends, HTTPException, Header, Response

from .. import security
from ..config import settings


COOKIE_NAME = "proofloop_momen"
CSRF_COOKIE = "proofloop_csrf"
COOKIE_PATH = "/api/v1/momen"
DEFAULT_TTL_SECONDS = 60 * 60 * 8


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def _key() -> bytes:
    return hashlib.sha256(f"momen-session:{settings.secret}".encode("utf-8")).digest()


def _jwt_expiry(token: str) -> Optional[int]:
    try:
        payload = json.loads(_unb64(token.split(".")[1]))
        return int(payload["exp"])
    except (ValueError, TypeError, KeyError, IndexError, UnicodeDecodeError):
        return None


def create_session(
    local_user_id: str, account: dict, token: str
) -> tuple[str, int]:
    expires = _jwt_expiry(token)
    now = int(time.time())
    ttl = DEFAULT_TTL_SECONDS if expires is None else max(60, min(expires - now, 86400))
    payload = {
        "uid": local_user_id,
        "sub": account.get("id"),
        "email": account.get("email"),
        "username": account.get("username"),
        "jwt": token,
        "iat": now,
        "exp": now + ttl,
    }
    body = _b64(
        json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    )
    signature = hmac.new(_key(), body.encode("ascii"), hashlib.sha256).digest()
    return f"{body}.{_b64(signature)}", ttl


def decode_session(value: str) -> Optional[dict]:
    try:
        body, signature = value.split(".")
        expected = hmac.new(_key(), body.encode("ascii"), hashlib.sha256).digest()
        if not hmac.compare_digest(expected, _unb64(signature)):
            return None
        payload = json.loads(_unb64(body))
        if not isinstance(payload, dict) or int(payload.get("exp", 0)) < int(time.time()):
            return None
        if not payload.get("uid") or not payload.get("sub") or not payload.get("jwt"):
            return None
        return payload
    except (ValueError, TypeError, json.JSONDecodeError, UnicodeDecodeError):
        return None


def new_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def set_session_cookies(
    response: Response, session_token: str, csrf_token: str, ttl: int
) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=session_token,
        max_age=ttl,
        httponly=True,
        samesite="strict",
        secure=settings.is_production,
        path=COOKIE_PATH,
    )
    response.set_cookie(
        key=CSRF_COOKIE,
        value=csrf_token,
        max_age=ttl,
        httponly=False,
        samesite="strict",
        secure=settings.is_production,
        path="/",
    )


def clear_session_cookies(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME, path=COOKIE_PATH)
    response.delete_cookie(CSRF_COOKIE, path="/")


def current_session(
    value: Optional[str] = Cookie(default=None, alias=COOKIE_NAME),
    user: dict = Depends(security.current_user),
) -> dict:
    if not value:
        raise HTTPException(
            status_code=401,
            detail={
                "code": "momen_not_connected",
                "message": "Connect a Momen account to use the Momen backend.",
            },
        )
    payload = decode_session(value)
    if not payload:
        raise HTTPException(
            status_code=401,
            detail={
                "code": "momen_session_expired",
                "message": "Your Momen session expired. Reconnect your Momen account.",
            },
        )
    if payload.get("uid") != user["id"]:
        raise HTTPException(
            status_code=401,
            detail={
                "code": "momen_session_mismatch",
                "message": "This Momen session belongs to a different local user.",
            },
        )
    return payload


def require_csrf(
    csrf_cookie: Optional[str] = Cookie(default=None, alias=CSRF_COOKIE),
    csrf_header: Optional[str] = Header(default=None, alias="X-CSRF-Token"),
) -> None:
    if (
        not csrf_cookie
        or not csrf_header
        or not hmac.compare_digest(csrf_cookie, csrf_header)
    ):
        raise HTTPException(
            status_code=403,
            detail={
                "code": "csrf_failed",
                "message": "Missing or invalid CSRF token. Reload and try again.",
            },
        )
