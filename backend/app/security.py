from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
import uuid
from typing import Optional

from fastapi import Cookie, HTTPException, Response

from . import db
from .config import settings


TOKEN_TTL_SECONDS = 60 * 60 * 24 * 30
COOKIE_NAME = "proofloop_session"
_SCRYPT_N = 2**14


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=_SCRYPT_N, r=8, p=1, dklen=32)
    return f"scrypt${_SCRYPT_N}$8$1${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, stored: Optional[str]) -> bool:
    if not stored:
        return False
    try:
        scheme, n, r, p, salt, digest = stored.split("$")
        if scheme != "scrypt":
            return False
        candidate = hashlib.scrypt(
            password.encode("utf-8"),
            salt=_unb64(salt),
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(_unb64(digest)),
        )
        return hmac.compare_digest(candidate, _unb64(digest))
    except (ValueError, TypeError):
        return False


def create_token(user_id: str, is_guest: bool) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": user_id,
        "guest": is_guest,
        "iat": int(time.time()),
        "exp": int(time.time()) + TOKEN_TTL_SECONDS,
        "jti": uuid.uuid4().hex,
    }
    signing_input = f"{_b64(json.dumps(header, separators=(',', ':')).encode())}." \
                    f"{_b64(json.dumps(payload, separators=(',', ':')).encode())}"
    signature = hmac.new(settings.secret.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256).digest()
    return f"{signing_input}.{_b64(signature)}"


def decode_token(token: str) -> Optional[dict]:
    try:
        header_b64, payload_b64, signature_b64 = token.split(".")
        signing_input = f"{header_b64}.{payload_b64}"
        expected = hmac.new(
            settings.secret.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256
        ).digest()
        if not hmac.compare_digest(expected, _unb64(signature_b64)):
            return None
        payload = json.loads(_unb64(payload_b64))
        if not isinstance(payload, dict) or int(payload.get("exp", 0)) < int(time.time()):
            return None
        return payload
    except (ValueError, TypeError, json.JSONDecodeError, UnicodeDecodeError):
        return None


def set_session_cookie(response: Response, user: dict) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=create_token(user["id"], bool(user["is_guest"])),
        max_age=TOKEN_TTL_SECONDS,
        httponly=True,
        samesite="lax",
        secure=settings.is_production,
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME, path="/")


def current_user(session: Optional[str] = Cookie(default=None, alias=COOKIE_NAME)) -> dict:
    if not session:
        raise HTTPException(
            status_code=401,
            detail={"code": "not_authenticated", "message": "Start a guest session or sign in."},
        )
    payload = decode_token(session)
    if not payload:
        raise HTTPException(
            status_code=401,
            detail={"code": "invalid_session", "message": "Your session expired. Reload to continue."},
        )
    user = db.get_user(str(payload.get("sub", "")))
    if not user:
        raise HTTPException(
            status_code=401,
            detail={"code": "unknown_user", "message": "Session user no longer exists."},
        )
    return user
