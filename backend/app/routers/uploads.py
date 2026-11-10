from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from .. import db, security
from ..services import ingest

router = APIRouter(prefix="/uploads", tags=["uploads"])

IMAGE_MESSAGE = (
    "Screenshot OCR is not enabled in this deployment. Upload a PDF or paste the text from the "
    "image instead — ProofLoop will not invent text it cannot read."
)


@router.post("")
async def upload(file: UploadFile = File(...), user: dict = Depends(security.current_user)):
    filename = ingest.clean_filename(file.filename or "document")
    kind = ingest.detect_kind(filename, file.content_type or "")
    if kind is None:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "unsupported_file",
                "message": "Unsupported file type. Use PDF, TXT/MD, or an image.",
            },
        )
    if kind == "image":
        raise HTTPException(status_code=422, detail={"code": "ocr_unavailable", "message": IMAGE_MESSAGE})

    data = await file.read(ingest.MAX_BYTES + 1)
    if len(data) > ingest.MAX_BYTES:
        raise HTTPException(
            status_code=413,
            detail={"code": "file_too_large", "message": "Files are limited to 10 MB."},
        )
    if not data:
        raise HTTPException(
            status_code=422, detail={"code": "empty_file", "message": "The file is empty."}
        )

    if kind == "pdf":
        try:
            text = ingest.extract_pdf(data)
        except ingest.IngestError as exc:
            raise HTTPException(
                status_code=422, detail={"code": "pdf_unreadable", "message": str(exc)}
            ) from exc
    else:
        text = data.decode("utf-8", errors="replace").strip()[: ingest.MAX_TEXT_CHARS]
        if len(text) < 20:
            raise HTTPException(
                status_code=422,
                detail={"code": "text_too_short", "message": "The file contains too little text."},
            )

    upload_row = db.create_upload(user["id"], filename, kind, text)
    return {
        "id": upload_row["id"],
        "filename": filename,
        "kind": kind,
        "chars": len(text),
        "preview": text[:600],
    }
