from __future__ import annotations

import json
from dataclasses import replace

import httpx
import pytest

from app.config import settings
from app.momen import client


def _transport(handler) -> httpx.MockTransport:
    return httpx.MockTransport(handler)


def _json_response(payload: dict, status: int = 200) -> httpx.Response:
    return httpx.Response(status, json=payload)


@pytest.fixture()
def configured(monkeypatch):
    monkeypatch.setattr(
        client,
        "settings",
        replace(
            settings,
            momen_graphql_url="https://momen.test/graphql",
            momen_admin_token="admin-token",
        ),
    )
    return client.settings


def test_graphql_rejects_missing_admin_token(monkeypatch):
    monkeypatch.setattr(client, "settings", replace(settings, momen_admin_token=""))
    with pytest.raises(client.MomenError) as exc:
        client.graphql("query { workspace { id } }", admin=True)
    assert exc.value.code == "momen_read_unavailable"
    assert exc.value.status == 503


def test_graphql_sends_bearer_and_returns_data(configured):
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["auth"] = request.headers.get("Authorization")
        captured["body"] = json.loads(request.content)
        return _json_response({"data": {"workspace": [{"id": 6}]}})

    data = client.graphql(
        "query { workspace { id } }",
        {"where": {"owner_id": {"_eq": 7}}},
        admin=True,
        transport=_transport(handler),
    )
    assert data == {"workspace": [{"id": 6}]}
    assert captured["auth"] == "Bearer admin-token"
    assert captured["body"]["variables"] == {"where": {"owner_id": {"_eq": 7}}}


def test_graphql_maps_login_error(configured):
    def handler(request: httpx.Request) -> httpx.Response:
        return _json_response(
            {
                "errors": [
                    {
                        "message": "authenticateWithEmail: Incorrect email or password",
                        "extensions": {"code": "ENTITY_DOES_NOT_EXIST"},
                    }
                ]
            }
        )

    with pytest.raises(client.MomenError) as exc:
        client.graphql("mutation { x }", transport=_transport(handler))
    assert exc.value.code == "invalid_credentials"
    assert exc.value.status == 401


def test_graphql_maps_workspace_ownership_error(configured):
    handler = lambda request: _json_response(
        {"errors": [{"message": "Workspace not found or not owned by the caller."}]}
    )
    with pytest.raises(client.MomenError) as exc:
        client.graphql("mutation { x }", transport=_transport(handler))
    assert exc.value.code == "workspace_forbidden"
    assert exc.value.status == 403


def test_graphql_maps_timeout(configured):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("timed out", request=request)

    with pytest.raises(client.MomenError) as exc:
        client.graphql("query { x }", transport=_transport(handler))
    assert exc.value.code == "momen_timeout"
    assert exc.value.status == 504


def test_graphql_maps_connection_failure(configured):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no route", request=request)

    with pytest.raises(client.MomenError) as exc:
        client.graphql("query { x }", transport=_transport(handler))
    assert exc.value.code == "momen_unavailable"
    assert exc.value.status == 502


def test_graphql_rejects_unreadable_and_missing_data(configured):
    with pytest.raises(client.MomenError) as exc:
        client.graphql(
            "query { x }",
            transport=_transport(lambda request: httpx.Response(200, text="<html>")),
        )
    assert exc.value.code == "momen_invalid_response"

    with pytest.raises(client.MomenError) as exc:
        client.graphql(
            "query { x }",
            transport=_transport(lambda request: _json_response({"data": None})),
        )
    assert exc.value.code == "momen_invalid_response"


def test_authenticate_requires_account_and_token(monkeypatch):
    monkeypatch.setattr(
        client,
        "graphql",
        lambda *args, **kwargs: {
            "authenticateWithEmail": {"account": {"id": 7}, "jwt": None}
        },
    )
    with pytest.raises(client.MomenError) as exc:
        client.authenticate("qa@example.com", "secret")
    assert exc.value.code == "momen_output_missing"


def test_authenticate_never_registers(monkeypatch):
    captured = {}

    def fake_graphql(query, variables=None, **kwargs):
        captured.update(variables or {})
        return {
            "authenticateWithEmail": {
                "account": {"id": 7, "email": "qa@example.com"},
                "jwt": {"token": "user-jwt"},
            }
        }

    monkeypatch.setattr(client, "graphql", fake_graphql)
    result = client.authenticate(" QA@Example.com ", "secret")
    assert result == {
        "account": {"id": 7, "email": "qa@example.com"},
        "token": "user-jwt",
    }
    assert captured["email"] == "qa@example.com"
    assert captured["register"] is False


def test_create_job_parses_jsonb_string_output(monkeypatch):
    monkeypatch.setattr(
        client,
        "graphql",
        lambda *args, **kwargs: {
            client.ACTION_CREATE_VERIFICATION_JOB: json.dumps(
                {"verification_job_id": 42, "status": "QUEUED", "created_at": None}
            )
        },
    )
    result = client.create_verification_job(
        "user-jwt",
        title="Eiffel",
        workspace_id=6,
        input_type="TEXT",
        original_text="  padded text  ",
    )
    assert result["verification_job_id"] == 42


def test_create_job_rejects_missing_output(monkeypatch):
    monkeypatch.setattr(
        client, "graphql", lambda *args, **kwargs: {client.ACTION_CREATE_VERIFICATION_JOB: None}
    )
    with pytest.raises(client.MomenError) as exc:
        client.create_verification_job(
            "user-jwt", title="Eiffel", workspace_id=6, input_type="TEXT"
        )
    assert exc.value.code == "momen_output_missing"


def test_read_filters_scope_to_account(monkeypatch):
    captured = []

    def fake_graphql(query, variables=None, **kwargs):
        captured.append(variables)
        return {
            "verification_job": [],
            "verification_job_aggregate": {"aggregate": {"count": 0}},
            "workspace": [],
        }

    monkeypatch.setattr(client, "graphql", fake_graphql)
    client.list_workspaces(7)
    client.list_jobs(7)
    client.get_job(7, 42)
    assert captured[0]["where"] == {"owner_id": {"_eq": 7}}
    assert captured[1]["where"] == {
        "created_by_id": {"_eq": 7},
        "workspace": {"owner_id": {"_eq": 7}},
    }
    assert captured[2]["where"] == {
        "id": {"_eq": 42},
        "created_by_id": {"_eq": 7},
        "workspace": {"owner_id": {"_eq": 7}},
    }
