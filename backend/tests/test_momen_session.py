from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

from app.momen import session


def _jwt(exp: int | None = None) -> str:
    payload = {"sub": "hashid"}
    if exp is not None:
        payload["exp"] = exp
    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
    return f"header.{body}.signature"


def test_session_roundtrip_keeps_numeric_account_id():
    token, ttl = session.create_session(
        "usr_local", {"id": 1000000000000001, "email": "qa@example.com"}, _jwt()
    )
    payload = session.decode_session(token)
    assert payload is not None
    assert payload["uid"] == "usr_local"
    assert payload["sub"] == 1000000000000001
    assert payload["jwt"].startswith("header.")
    assert ttl > 0


def test_session_honours_jwt_expiry():
    exp = int(time.time()) + 120
    token, ttl = session.create_session("usr_local", {"id": 7}, _jwt(exp))
    assert 60 <= ttl <= 120
    assert session.decode_session(token)["exp"] <= exp


def test_tampered_session_is_rejected():
    token, _ = session.create_session("usr_local", {"id": 7}, _jwt())
    body, signature = token.split(".")
    assert session.decode_session(f"{body}.{signature[:-4]}AAAA") is None
    other = base64.urlsafe_b64encode(b"{}").rstrip(b"=").decode()
    assert session.decode_session(f"{other}.{signature}") is None


def test_expired_session_is_rejected():
    body = base64.urlsafe_b64encode(
        json.dumps(
            {"uid": "usr_local", "sub": 7, "jwt": _jwt(), "exp": int(time.time()) - 1}
        ).encode()
    ).rstrip(b"=").decode()
    signature = hmac.new(session._key(), body.encode("ascii"), hashlib.sha256).digest()
    signed = base64.urlsafe_b64encode(signature).rstrip(b"=").decode()
    assert session.decode_session(f"{body}.{signed}") is None
