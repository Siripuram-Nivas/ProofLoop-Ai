from __future__ import annotations

import re
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

from .services.ingest import IngestError, validate_url

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")


class Credentials(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def valid_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not EMAIL_RE.match(value):
            raise ValueError("Enter a valid email address.")
        return value


class EngineSelection(BaseModel):
    claim_extraction: Optional[Literal["deterministic", "openai", "gemini"]] = None
    research: Optional[Literal["wikipedia", "google_search"]] = None
    analysis: Optional[Literal["", "openai", "gemini"]] = None
    review: Optional[Literal["", "openai", "gemini"]] = None
    second_review: Optional[Literal["", "openai", "gemini"]] = None


class VerificationCreate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=160)
    text: Optional[str] = None
    url: Optional[str] = Field(default=None, max_length=2000)
    upload_id: Optional[str] = None
    engines: Optional[EngineSelection] = None

    @field_validator("text")
    @classmethod
    def valid_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        if len(value) < 20:
            raise ValueError("Provide at least 20 characters so claims can be extracted.")
        if len(value) > 200_000:
            raise ValueError("Text is limited to 200,000 characters.")
        return value

    @field_validator("url")
    @classmethod
    def valid_url(cls, value: Optional[str]) -> Optional[str]:
        if value is None or not value.strip():
            return None
        try:
            return validate_url(value)
        except IngestError as exc:
            raise ValueError(str(exc)) from exc

    def model_post_init(self, __context) -> None:
        provided = [bool(self.text), bool(self.url), bool(self.upload_id)]
        if sum(provided) != 1:
            raise ValueError("Provide exactly one input: text, url, or upload_id.")


class ClaimCreate(BaseModel):
    text: str = Field(min_length=3, max_length=2000)

    @field_validator("text")
    @classmethod
    def clean(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 3:
            raise ValueError("Claim text is too short.")
        return value


class ClaimPatch(ClaimCreate):
    pass
