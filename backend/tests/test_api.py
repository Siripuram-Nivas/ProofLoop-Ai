from __future__ import annotations

from fastapi.testclient import TestClient

from app import main as main_module


DEMO_TEXT = (
    "The Eiffel Tower is 330 metres tall. It was completed in 1889. "
    "The tower is located in Paris, France."
)


def _candidate() -> dict:
    return {
        "page_id": 923,
        "title": "Eiffel Tower",
        "url": "https://en.wikipedia.org/?curid=923",
        "excerpt": "The Eiffel Tower is 330 metres tall and was completed in 1889 in Paris.",
        "updated_at": "2026-10-01T00:00:00Z",
        "retrieved_at": "2026-11-10T00:00:00Z",
        "stale": False,
    }


def _stub_research(monkeypatch):
    monkeypatch.setattr("app.services.pipeline.fetch_sources", lambda claim: [_candidate()])


def test_health_is_public(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_guest_session(client):
    response = client.post("/api/v1/auth/guest")
    assert response.status_code == 200
    assert response.json()["user"]["is_guest"] is True
    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200


def test_unauthenticated_write_is_rejected(client):
    response = client.post("/api/v1/verifications", json={"text": DEMO_TEXT})
    assert response.status_code == 401


def test_register_login_flow(client):
    registration = client.post(
        "/api/v1/auth/register",
        json={"email": "judge@example.com", "password": "strong-password-1"},
    )
    assert registration.status_code in (201, 409)
    client.post("/api/v1/auth/logout")
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "judge@example.com", "password": "strong-password-1"},
    )
    assert login.status_code == 200
    assert login.json()["user"]["is_guest"] is False
    bad = client.post(
        "/api/v1/auth/login",
        json={"email": "judge@example.com", "password": "wrong-password"},
    )
    assert bad.status_code == 401


def test_empty_input_rejected(client, guest):
    response = client.post("/api/v1/verifications", json={"text": "too short"})
    assert response.status_code == 422


def test_invalid_url_rejected(client, guest):
    response = client.post("/api/v1/verifications", json={"url": "http://127.0.0.1/x"})
    assert response.status_code == 422
    message = response.json()["error"]["message"]
    assert "reserved network" in message
    assert "Value error" not in message


def test_text_upload_becomes_document_job(client, guest, monkeypatch):
    _stub_research(monkeypatch)
    upload = client.post(
        "/api/v1/uploads",
        files={"file": ("notes.txt", b"The Eiffel Tower is 330 metres tall and was completed in 1889.", "text/plain")},
    )
    assert upload.status_code == 200
    assert upload.json()["kind"] == "text"

    created = client.post("/api/v1/verifications", json={"upload_id": upload.json()["id"]})
    assert created.status_code == 202
    job = client.get(f"/api/v1/verifications/{created.json()['id']}").json()
    assert job["input_kind"] == "document"
    assert "Eiffel Tower" in job["input_text"]


def test_image_upload_is_rejected_without_ocr(client, guest):
    upload = client.post(
        "/api/v1/uploads", files={"file": ("shot.png", b"\x89PNG\r\n\x1a\n", "image/png")}
    )
    assert upload.status_code == 422
    assert upload.json()["error"]["code"] == "ocr_unavailable"
    assert "not enabled" in upload.json()["error"]["message"]


def test_full_pipeline_with_stubbed_research(client, guest, monkeypatch):
    _stub_research(monkeypatch)
    response = client.post("/api/v1/verifications", json={"text": DEMO_TEXT})
    assert response.status_code == 202
    job_id = response.json()["id"]

    job = client.get(f"/api/v1/verifications/{job_id}").json()
    assert job["status"] == "completed", job.get("error")
    assert len(job["claims"]) == 3
    assert len(job["sources"]) == 1
    assert job["report"]["summary"]["sources"] == 1
    assert job["stages"][-1]["status"] == "done"
    assert all(stage["status"] in {"done", "partial"} for stage in job["stages"])

    claim = job["claims"][0]
    assert claim["verdict"] in {"supported", "insufficient", "unverified", "contradicted", "mixed"}

    graph = client.get(f"/api/v1/verifications/{job_id}/graph").json()
    node_ids = {node["id"] for node in graph["nodes"]}
    assert graph["nodes"]
    assert all(edge["source"] in node_ids and edge["target"] in node_ids for edge in graph["edges"])

    report = client.get(f"/api/v1/verifications/{job_id}/report").json()
    assert report["limitations"]
    assert report["disclaimer"]
    assert len(report["claims"]) == 3

    contradictions = client.get(f"/api/v1/verifications/{job_id}/contradictions")
    assert contradictions.status_code == 200

    stats = client.get("/api/v1/stats").json()
    assert stats["totals"]["runs"] == 1
    assert stats["totals"]["claims"] == 3


def test_claim_edit_and_delete(client, guest, monkeypatch):
    _stub_research(monkeypatch)
    job_id = client.post("/api/v1/verifications", json={"text": DEMO_TEXT}).json()["id"]
    job = client.get(f"/api/v1/verifications/{job_id}").json()
    claim_id = job["claims"][0]["id"]

    edited = client.patch(
        f"/api/v1/verifications/{job_id}/claims/{claim_id}",
        json={"text": "The Eiffel Tower is 300 metres tall."},
    )
    assert edited.status_code == 200
    assert edited.json()["verdict"] == "unverified"

    added = client.post(
        f"/api/v1/verifications/{job_id}/claims",
        json={"text": "Paris is the capital of France."},
    )
    assert added.status_code == 201
    assert added.json()["verdict"] == "unverified"

    deleted = client.delete(f"/api/v1/verifications/{job_id}/claims/{claim_id}")
    assert deleted.status_code == 200
    assert deleted.json()["claims"] == 3


def test_ownership_isolation(tmp_path, monkeypatch, client, guest):
    monkeypatch.setattr("app.services.pipeline.fetch_sources", lambda claim: [_candidate()])
    job_id = client.post("/api/v1/verifications", json={"text": DEMO_TEXT}).json()["id"]

    with TestClient(main_module.app) as other:
        other.post("/api/v1/auth/guest")
        assert other.get(f"/api/v1/verifications/{job_id}").status_code == 404
        assert other.get(f"/api/v1/verifications/{job_id}/report").status_code == 404


def test_research_failure_is_visible(client, guest, monkeypatch):
    def boom(claim):
        from app.services.research import ResearchError

        raise ResearchError("offline")

    monkeypatch.setattr("app.services.pipeline.fetch_sources", boom)
    job_id = client.post("/api/v1/verifications", json={"text": DEMO_TEXT}).json()["id"]
    job = client.get(f"/api/v1/verifications/{job_id}").json()
    assert job["status"] == "completed"
    assert all(claim["verdict"] == "inconclusive" for claim in job["claims"])
    assert any(stage["status"] == "failed" for stage in job["stages"])
    assert "no usable evidence" in " ".join(job["report"]["limitations"]).lower()
