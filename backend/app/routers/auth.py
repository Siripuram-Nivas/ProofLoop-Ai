from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response

from .. import db, security
from ..schemas import Credentials

router = APIRouter(prefix="/auth", tags=["auth"])


def _public_user(user: dict) -> dict:
    return {"id": user["id"], "email": user["email"], "is_guest": user["is_guest"]}


@router.post("/guest")
def create_guest(
    response: Response,
    proofloop_session: Optional[str] = Cookie(default=None),
):
    if proofloop_session:
        payload = security.decode_token(proofloop_session)
        if payload:
            user = db.get_user(str(payload.get("sub", "")))
            if user:
                return {"user": _public_user(user)}
    user = db.create_user(password_hash=None, is_guest=True)
    security.set_session_cookie(response, user)
    return {"user": _public_user(user)}


@router.post("/register", status_code=201)
def register(payload: Credentials, response: Response):
    if db.get_user_with_secret(payload.email):
        raise HTTPException(
            status_code=409,
            detail={"code": "email_taken", "message": "An account with this email already exists."},
        )
    user = db.create_user(
        password_hash=security.hash_password(payload.password),
        is_guest=False,
        email=payload.email,
    )
    security.set_session_cookie(response, user)
    return {"user": _public_user(user)}


@router.post("/login")
def login(payload: Credentials, response: Response):
    account = db.get_user_with_secret(payload.email)
    valid = bool(account) and security.verify_password(payload.password, account.get("password_hash"))
    if not valid or account is None:
        raise HTTPException(
            status_code=401,
            detail={"code": "invalid_credentials", "message": "Email or password is incorrect."},
        )
    security.set_session_cookie(response, account)
    return {"user": _public_user(account)}


@router.post("/logout")
def logout(response: Response):
    security.clear_session_cookie(response)
    return {"ok": True}


@router.get("/me")
def me(user: dict = Depends(security.current_user)):
    return {"user": _public_user(user)}
