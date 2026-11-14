from __future__ import annotations

from dataclasses import replace

import pytest

from app.config import settings
from app.momen.client import MomenError
from app.routers import momen as momen_router


ACCOUNT = {"id": 1000000000000001, "email": "qa@example.com", "username": "qa"}
WORKSPACE = {
    "id": 6,
    "name": "QA Workspace",
    "slug": "qa-workspace",
    "status": "active",
    "owner_id": ACCOUNT["id"],
}
JOB = {
    "id": 42,
    "title": "Eiffel check",
    "input_type": "TEXT",
    "status": "QUEUED",
    "current_stage": "RECEIVED",
    "error_message": None,
    "created_at": "2026-11-13T10:00:00Z",
    "updated_at": "2026-11-13T10:00:00Z",
    "started_at": None,
    "completed_at": None,
    "workspace_id": WORKSPACE["id"],
    "created_by_id": ACCOUNT["id"],
    "metadata": None,
}


def _csrf(client) -> dict[str, str]:
    value = client.cookies.get("proofloop_csrf")
    return {"X-CSRF-Token": value} if value else {}


@pytest.fixture()
def momen(client, guest, monkeypatch):
    monkeypatch.setattr(
        momen_router,
        "settings",
        replace(settings, momen_admin_token="test-admin-token"),
    )
    monkeypatch.setattr(
        momen_router.momen_client,
        "authenticate",
        lambda email, password: {"account": ACCOUNT, "token": "momen-user-jwt"},
    )
    monkeypatch.setattr(
        momen_router.momen_client, "list_workspaces", lambda account_id: [WORKSPACE]
    )
    response = client.post(
        "/api/v1/momen/auth/login",
        json={"email": "qa@example.com", "password": "secret"},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _body(**overrides):
    body = {
        "workspace_id": WORKSPACE["id"],
        "input_type": "TEXT",
        "title": "Eiffel check",
        "original_text": "The Eiffel Tower is 330 metres tall.",
    }
    body.update(overrides)
    return body


def test_login_returns_account_and_workspaces_without_token(momen, client):
    assert momen["connected"] is True
    assert momen["account"]["email"] == "qa@example.com"
    assert momen["workspaces"][0]["id"] == WORKSPACE["id"]
    assert momen["persistence_available"] is False
    assert "momen-user-jwt" not in str(momen)
    cookies = "\n".join(client.get("/api/v1/momen/session").headers.get_list("set-cookie"))
    assert "proofloop_momen" not in cookies
    assert client.get("/api/v1/auth/me").status_code == 200


def test_session_cookie_is_httponly(client, guest, monkeypatch):
    monkeypatch.setattr(
        momen_router.momen_client,
        "authenticate",
        lambda email, password: {"account": ACCOUNT, "token": "momen-user-jwt"},
    )
    monkeypatch.setattr(
        momen_router.momen_client, "list_workspaces", lambda account_id: [WORKSPACE]
    )
    response = client.post(
        "/api/v1/momen/auth/login",
        json={"email": "qa@example.com", "password": "secret"},
    )
    set_cookie = "\n".join(response.headers.get_list("set-cookie"))
    assert "proofloop_momen=" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "SameSite=strict" in set_cookie
    assert "momen-user-jwt" not in response.text


def test_invalid_credentials_are_rejected(client, guest, monkeypatch):
    def fail(email, password):
        raise MomenError("invalid_credentials", "Email or password is incorrect.", 401)

    monkeypatch.setattr(momen_router.momen_client, "authenticate", fail)
    response = client.post(
        "/api/v1/momen/auth/login",
        json={"email": "qa@example.com", "password": "wrong"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"


def test_expired_or_tampered_session_is_rejected(momen, client):
    client.cookies.set(
        "proofloop_momen", "tampered.token", path="/api/v1/momen"
    )
    session = client.get("/api/v1/momen/session")
    assert session.status_code == 200
    assert session.json()["connected"] is False
    response = client.get("/api/v1/momen/verifications")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "momen_session_expired"


def test_missing_momen_session_is_rejected(client, guest):
    response = client.get("/api/v1/momen/verifications")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "momen_not_connected"


def test_anonymous_job_creation_is_rejected(client):
    response = client.post(
        "/api/v1/momen/verifications",
        json=_body(),
        headers={"X-CSRF-Token": "missing"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_authenticated"


def test_csrf_is_required_for_job_creation(momen, client, monkeypatch):
    called = []
    monkeypatch.setattr(
        momen_router.momen_client,
        "create_verification_job",
        lambda *args, **kwargs: called.append(True),
    )
    response = client.post("/api/v1/momen/verifications", json=_body())
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "csrf_failed"
    assert called == []


def test_create_job_passes_exact_text_and_user_jwt(momen, client, monkeypatch):
    captured = {}

    def fake_create(token, **kwargs):
        captured["token"] = token
        captured.update(kwargs)
        return {
            "verification_job_id": 42,
            "status": "QUEUED",
            "created_at": "2026-11-13T10:00:00Z",
        }

    monkeypatch.setattr(
        momen_router.momen_client, "create_verification_job", fake_create
    )
    padded = "  The Eiffel Tower is 330 metres tall.  "
    response = client.post(
        "/api/v1/momen/verifications",
        json=_body(original_text=padded),
        headers=_csrf(client),
    )
    assert response.status_code == 201, response.text
    assert response.json()["verification_job_id"] == 42
    assert response.json()["persistence_available"] is False
    assert "momen-user-jwt" not in response.text
    assert captured["token"] == "momen-user-jwt"
    assert captured["original_text"] == padded
    assert captured["title"] == "Eiffel check"
    assert captured["workspace_id"] == WORKSPACE["id"]
    assert captured["input_type"] == "TEXT"


def test_cross_workspace_creation_is_rejected(momen, client, monkeypatch):
    def fail(*args, **kwargs):
        raise MomenError(
            "workspace_forbidden",
            "That workspace does not exist or is not owned by your Momen account.",
            403,
        )

    monkeypatch.setattr(momen_router.momen_client, "create_verification_job", fail)
    response = client.post(
        "/api/v1/momen/verifications",
        json=_body(workspace_id=999999999),
        headers=_csrf(client),
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "workspace_forbidden"


def test_whitespace_only_text_is_rejected_by_actionflow(momen, client, monkeypatch):
    def fail(*args, **kwargs):
        raise MomenError(
            "invalid_input",
            "original_text must contain non-whitespace content when input_type is TEXT.",
            422,
        )

    monkeypatch.setattr(momen_router.momen_client, "create_verification_job", fail)
    response = client.post(
        "/api/v1/momen/verifications",
        json=_body(original_text="   "),
        headers=_csrf(client),
    )
    assert response.status_code == 422
    assert "non-whitespace" in response.json()["error"]["message"]


@pytest.mark.parametrize(
    "payload",
    [
        {"input_type": "URL", "original_text": None, "original_url": "not-a-url"},
        {
            "input_type": "PDF",
            "original_text": None,
            "uploaded_file_url": "not-a-url",
        },
    ],
)
def test_url_and_pdf_validation_errors_are_surfaced(
    momen, client, monkeypatch, payload
):
    def fail(*args, **kwargs):
        raise MomenError(
            "invalid_input",
            "input_type must be TEXT, URL, PDF, or IMAGE, and its matching content field must be non-empty.",
            422,
        )

    monkeypatch.setattr(momen_router.momen_client, "create_verification_job", fail)
    response = client.post(
        "/api/v1/momen/verifications",
        json=_body(**payload),
        headers=_csrf(client),
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_input"


def test_graphql_error_maps_to_bad_gateway(momen, client, monkeypatch):
    def fail(*args, **kwargs):
        raise MomenError("momen_graphql_error", "Momen rejected the request.", 502)

    monkeypatch.setattr(momen_router.momen_client, "create_verification_job", fail)
    response = client.post(
        "/api/v1/momen/verifications", json=_body(), headers=_csrf(client)
    )
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "momen_graphql_error"


def test_timeout_maps_to_gateway_timeout(momen, client, monkeypatch):
    def fail(*args, **kwargs):
        raise MomenError("momen_timeout", "Momen did not respond in time.", 504)

    monkeypatch.setattr(momen_router.momen_client, "create_verification_job", fail)
    response = client.post(
        "/api/v1/momen/verifications", json=_body(), headers=_csrf(client)
    )
    assert response.status_code == 504
    assert response.json()["error"]["code"] == "momen_timeout"


def test_authorized_job_list_uses_session_account(momen, client, monkeypatch):
    captured = {}

    def fake_list(account_id, limit=20, offset=0):
        captured.update({"account_id": account_id, "limit": limit, "offset": offset})
        return {"items": [JOB], "total": 1}

    monkeypatch.setattr(momen_router.momen_client, "list_jobs", fake_list)
    response = client.get("/api/v1/momen/verifications?limit=5&offset=0")
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["id"] == 42
    assert captured == {"account_id": ACCOUNT["id"], "limit": 5, "offset": 0}


def test_cross_workspace_read_returns_not_found(momen, client, monkeypatch):
    captured = {}

    def fake_get(account_id, job_id):
        captured.update({"account_id": account_id, "job_id": job_id})
        return None

    monkeypatch.setattr(momen_router.momen_client, "get_job", fake_get)
    response = client.get("/api/v1/momen/verifications/999")
    assert response.status_code == 404
    assert captured == {"account_id": ACCOUNT["id"], "job_id": 999}


def test_job_detail_and_report_reads(momen, client, monkeypatch):
    job = {
        **JOB,
        "claims": [],
        "sources": [],
        "contradictions": [],
        "proof_reports": [
            {
                "id": 1,
                "version": 1,
                "overall_status": "verified",
                "summary": "Ready.",
                "report_content": {},
                "limitations": [],
                "generated_at": "2026-11-13T10:05:00Z",
                "is_current": True,
            }
        ],
        "audit_logs": [],
    }
    monkeypatch.setattr(
        momen_router.momen_client, "get_job", lambda account_id, job_id: job
    )
    detail = client.get("/api/v1/momen/verifications/42")
    assert detail.status_code == 200
    assert detail.json()["job"]["id"] == 42
    assert detail.json()["persistence_available"] is False

    report = client.get("/api/v1/momen/verifications/42/report")
    assert report.status_code == 200
    assert report.json()["report"]["version"] == 1


def test_missing_report_returns_clear_error(momen, client, monkeypatch):
    job = {
        **JOB,
        "claims": [],
        "sources": [],
        "contradictions": [],
        "proof_reports": [],
        "audit_logs": [],
    }
    monkeypatch.setattr(
        momen_router.momen_client, "get_job", lambda account_id, job_id: job
    )
    response = client.get("/api/v1/momen/verifications/42/report")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "report_not_available"


def test_missing_read_access_is_reported(momen, client, monkeypatch):
    def unavailable(account_id, limit=20, offset=0):
        raise MomenError(
            "momen_read_unavailable",
            "Momen read access is not configured on the server (MOMEN_ADMIN_TOKEN).",
            503,
        )

    monkeypatch.setattr(momen_router.momen_client, "list_jobs", unavailable)
    response = client.get("/api/v1/momen/verifications")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "momen_read_unavailable"
