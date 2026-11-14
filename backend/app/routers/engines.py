from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .. import security
from ..engines import registry
from ..engines.errors import EngineError

router = APIRouter(prefix="/engines", tags=["engines"])

EngineId = Literal["openai", "gemini", "google_search"]


class EngineTestRequest(BaseModel):
    confirm: bool = False


@router.get("")
def list_engines(_: dict = Depends(security.current_user)):
    return {"engines": registry.availability(), "config": registry.config_summary()}


@router.post("/{engine_id}/test")
def test_engine(
    engine_id: EngineId,
    payload: EngineTestRequest,
    _: dict = Depends(security.current_user),
):
    if not payload.confirm:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "confirmation_required",
                "message": "Set confirm=true to spend a live provider request.",
            },
        )
    try:
        return registry.test_engine(engine_id)
    except EngineError as exc:
        raise HTTPException(
            status_code=exc.status, detail={"code": exc.code, "message": exc.message}
        ) from exc
