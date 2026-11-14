from __future__ import annotations

from typing import Literal, Optional

from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field

from .. import security
from ..config import settings
from ..momen import client as momen_client
from ..momen import session as momen_session
from ..momen.client import MomenError

router = APIRouter(prefix="/momen", tags=["momen"])


class MomenCredentials(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=1, max_length=200)


class MomenVerificationCreate(BaseModel):
    workspace_id: int = Field(gt=0)
    input_type: Literal["TEXT", "URL", "PDF", "IMAGE"]
    title: str = Field(min_length=1, max_length=300)
    original_text: Optional[str] = None
    original_url: Optional[str] = Field(default=None, max_length=4000)
    uploaded_file_url: Optional[str] = Field(default=None, max_length=4000)


def _raise(exc: MomenError) -> None:
    raise HTTPException(
        status_code=exc.status,
        detail={"code": exc.code, "message": exc.message},
    )


def _session_body(
    payload: dict,
    workspaces: list[dict],
    read_access: bool,
) -> dict:
    return {
        "connected": True,
        "account": {
            "id": payload.get("sub"),
            "email": payload.get("email"),
            "username": payload.get("username"),
        },
        "workspaces": workspaces,
        "read_access": read_access,
        "persistence_available": False,
    }


def _load_workspaces(account_id: int) -> tuple[list[dict], bool]:
    if not settings.momen_admin_token:
        return [], False
    try:
        return momen_client.list_workspaces(account_id), True
    except MomenError:
        return [], False


@router.post("/auth/login")
def login(
    payload: MomenCredentials,
    response: Response,
    user: dict = Depends(security.current_user),
):
    try:
        result = momen_client.authenticate(payload.email, payload.password)
    except MomenError as exc:
        _raise(exc)

    account = result["account"]
    workspaces, read_access = _load_workspaces(int(account["id"]))
    session_token, ttl = momen_session.create_session(
        user["id"], account, result["token"]
    )
    momen_session.set_session_cookies(
        response, session_token, momen_session.new_csrf_token(), ttl
    )
    return _session_body(
        {
            "sub": account["id"],
            "email": account.get("email"),
            "username": account.get("username"),
        },
        workspaces,
        read_access,
    )


@router.post("/auth/logout")
def logout(response: Response):
    momen_session.clear_session_cookies(response)
    return {"ok": True}


@router.get("/session")
def get_session(
    proofloop_momen: Optional[str] = Cookie(
        default=None, alias=momen_session.COOKIE_NAME
    ),
    user: dict = Depends(security.current_user),
):
    payload = (
        momen_session.decode_session(proofloop_momen) if proofloop_momen else None
    )
    if not payload or payload.get("uid") != user["id"]:
        return {
            "connected": False,
            "workspaces": [],
            "read_access": bool(settings.momen_admin_token),
            "persistence_available": False,
        }
    workspaces, read_access = _load_workspaces(int(payload["sub"]))
    return _session_body(payload, workspaces, read_access)


@router.get("/workspaces")
def list_workspaces(session: dict = Depends(momen_session.current_session)):
    try:
        items = momen_client.list_workspaces(int(session["sub"]))
    except MomenError as exc:
        _raise(exc)
    return {"items": items}


@router.post("/verifications", status_code=status.HTTP_201_CREATED)
def create_verification(
    payload: MomenVerificationCreate,
    session: dict = Depends(momen_session.current_session),
    _: None = Depends(momen_session.require_csrf),
):
    try:
        created = momen_client.create_verification_job(
            session["jwt"],
            title=payload.title,
            workspace_id=payload.workspace_id,
            input_type=payload.input_type,
            original_text=payload.original_text,
            original_url=payload.original_url,
            uploaded_file_url=payload.uploaded_file_url,
        )
    except MomenError as exc:
        _raise(exc)
    return {**created, "persistence_available": False}


@router.get("/verifications")
def list_verifications(
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    session: dict = Depends(momen_session.current_session),
):
    try:
        result = momen_client.list_jobs(int(session["sub"]), limit=limit, offset=offset)
    except MomenError as exc:
        _raise(exc)
    return {**result, "limit": limit, "offset": offset, "persistence_available": False}


@router.get("/verifications/{job_id}")
def get_verification(
    job_id: int,
    session: dict = Depends(momen_session.current_session),
):
    try:
        job = momen_client.get_job(int(session["sub"]), job_id)
    except MomenError as exc:
        _raise(exc)
    if not job:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "not_found",
                "message": "Verification not found in your Momen workspace.",
            },
        )
    return {"job": job, "persistence_available": False}


@router.get("/verifications/{job_id}/report")
def get_report(
    job_id: int,
    session: dict = Depends(momen_session.current_session),
):
    try:
        job = momen_client.get_job(int(session["sub"]), job_id)
    except MomenError as exc:
        _raise(exc)
    if not job:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "not_found",
                "message": "Verification not found in your Momen workspace.",
            },
        )
    reports = job.get("proof_reports") or []
    report = next((item for item in reports if item.get("is_current")), None)
    if report is None and reports:
        report = sorted(reports, key=lambda item: item.get("version") or 0)[-1]
    if report is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "report_not_available",
                "message": "No proof report is persisted for this Momen job yet.",
            },
        )
    return {"report": report, "persistence_available": False}
