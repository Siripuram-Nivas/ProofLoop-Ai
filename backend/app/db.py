from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .config import settings


_lock = threading.RLock()
_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE,
    password_hash TEXT,
    is_guest INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS uploads (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    filename TEXT NOT NULL,
    kind TEXT NOT NULL,
    extracted_text TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS verifications (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    title TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    data TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_verifications_user_created
    ON verifications(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_verifications_user_status
    ON verifications(user_id, status);
CREATE INDEX IF NOT EXISTS idx_uploads_user_created
    ON uploads(user_id, created_at DESC);
"""


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:20]}"


def _connect() -> sqlite3.Connection:
    path = Path(settings.db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    with _lock, _connect() as conn:
        conn.executescript(_SCHEMA)


def _user_row(row: sqlite3.Row | None) -> Optional[dict[str, Any]]:
    if row is None:
        return None
    return {
        "id": row["id"],
        "email": row["email"],
        "is_guest": bool(row["is_guest"]),
        "created_at": row["created_at"],
    }


def create_user(password_hash: Optional[str], is_guest: bool, email: Optional[str] = None) -> dict:
    user = {
        "id": new_id("usr"),
        "email": email.lower().strip() if email else None,
        "password_hash": password_hash,
        "is_guest": 1 if is_guest else 0,
        "created_at": utcnow(),
    }
    with _lock, _connect() as conn:
        conn.execute(
            "INSERT INTO users (id, email, password_hash, is_guest, created_at) VALUES (?,?,?,?,?)",
            (user["id"], user["email"], user["password_hash"], user["is_guest"], user["created_at"]),
        )
    return _user_row_dict(user)


def _user_row_dict(user: dict) -> dict:
    return {
        "id": user["id"],
        "email": user["email"],
        "is_guest": bool(user["is_guest"]),
        "created_at": user["created_at"],
    }


def get_user(user_id: str) -> Optional[dict]:
    with _lock, _connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return _user_row(row)


def get_user_with_secret(email: str) -> Optional[dict]:
    with _lock, _connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email.lower().strip(),)).fetchone()
    if row is None:
        return None
    user = _user_row(row)
    user["password_hash"] = row["password_hash"]
    return user


def create_upload(user_id: str, filename: str, kind: str, text: str) -> dict:
    upload = {
        "id": new_id("upl"),
        "user_id": user_id,
        "filename": filename,
        "kind": kind,
        "extracted_text": text,
        "created_at": utcnow(),
    }
    with _lock, _connect() as conn:
        conn.execute(
            "INSERT INTO uploads (id, user_id, filename, kind, extracted_text, created_at) VALUES (?,?,?,?,?,?)",
            (upload["id"], user_id, filename, kind, text, upload["created_at"]),
        )
    return {k: upload[k] for k in ("id", "filename", "kind", "created_at")}


def get_upload(upload_id: str, user_id: str) -> Optional[dict]:
    with _lock, _connect() as conn:
        row = conn.execute(
            "SELECT * FROM uploads WHERE id = ? AND user_id = ?", (upload_id, user_id)
        ).fetchone()
    return dict(row) if row else None


def save_verification(job: dict) -> None:
    with _lock, _connect() as conn:
        conn.execute(
            """INSERT INTO verifications (id, user_id, title, status, created_at, updated_at, data)
               VALUES (?,?,?,?,?,?,?)""",
            (
                job["id"],
                job["user_id"],
                job["title"],
                job["status"],
                job["created_at"],
                job["updated_at"],
                json.dumps(job, ensure_ascii=False, separators=(",", ":")),
            ),
        )


def update_verification(job: dict) -> None:
    job["updated_at"] = utcnow()
    with _lock, _connect() as conn:
        conn.execute(
            "UPDATE verifications SET title = ?, status = ?, updated_at = ?, data = ? WHERE id = ?",
            (
                job["title"],
                job["status"],
                job["updated_at"],
                json.dumps(job, ensure_ascii=False, separators=(",", ":")),
                job["id"],
            ),
        )


def get_verification(job_id: str, user_id: str) -> Optional[dict]:
    with _lock, _connect() as conn:
        row = conn.execute(
            "SELECT data FROM verifications WHERE id = ? AND user_id = ?", (job_id, user_id)
        ).fetchone()
    return json.loads(row["data"]) if row else None


def list_verifications(
    user_id: str, limit: int = 20, offset: int = 0, status: Optional[str] = None
) -> tuple[list[dict], int]:
    clauses = ["user_id = ?"]
    params: list[Any] = [user_id]
    if status:
        clauses.append("status = ?")
        params.append(status)
    where = " AND ".join(clauses)
    with _lock, _connect() as conn:
        total = conn.execute(f"SELECT COUNT(*) AS n FROM verifications WHERE {where}", params).fetchone()["n"]
        rows = conn.execute(
            f"""SELECT data FROM verifications WHERE {where}
                ORDER BY created_at DESC LIMIT ? OFFSET ?""",
            [*params, limit, offset],
        ).fetchall()
    items = []
    for row in rows:
        job = json.loads(row["data"])
        claims = job.get("claims", [])
        items.append(
            {
                "id": job["id"],
                "title": job["title"],
                "status": job["status"],
                "input_kind": job.get("input_kind"),
                "created_at": job["created_at"],
                "updated_at": job["updated_at"],
                "claim_count": len(claims),
                "verdicts": _verdict_counts(claims),
                "source_count": len(job.get("sources", [])),
                "conflict_count": len(job.get("contradictions", [])),
                "error": job.get("error"),
            }
        )
    return items, total


def _verdict_counts(claims: list[dict]) -> dict[str, int]:
    counts = {
        "supported": 0,
        "contradicted": 0,
        "mixed": 0,
        "insufficient": 0,
        "outdated": 0,
        "unverified": 0,
        "inconclusive": 0,
    }
    for claim in claims:
        verdict = claim.get("verdict")
        if verdict in counts:
            counts[verdict] += 1
    return counts


def stats(user_id: str) -> dict:
    with _lock, _connect() as conn:
        rows = conn.execute(
            "SELECT data FROM verifications WHERE user_id = ? AND status = 'completed'", (user_id,)
        ).fetchall()
    totals = {
        "runs": len(rows),
        "claims": 0,
        "supported": 0,
        "contradicted": 0,
        "mixed": 0,
        "insufficient": 0,
        "outdated": 0,
        "unverified": 0,
        "inconclusive": 0,
        "sources": 0,
        "conflicts": 0,
    }
    for row in rows:
        job = json.loads(row["data"])
        claims = job.get("claims", [])
        totals["claims"] += len(claims)
        totals["sources"] += len(job.get("sources", []))
        totals["conflicts"] += len(job.get("contradictions", []))
        for key, value in _verdict_counts(claims).items():
            totals[key] += value
    totals["unverified_all"] = totals["unverified"] + totals["inconclusive"]
    return totals
