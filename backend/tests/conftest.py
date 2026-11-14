from __future__ import annotations

import os

# Tests must never reach a real provider: pin the master gate off before app.config
# reads backend/.env. A local .env with live calls enabled must not spend credits here.
os.environ["PROOFLOOP_AI_LIVE_CALLS_ENABLED"] = "false"

from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from app import db
from app.config import settings
from app import main as main_module


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "settings", replace(settings, db_path=tmp_path / "test.db"))
    main_module._buckets.clear()
    with TestClient(main_module.app) as test_client:
        yield test_client


@pytest.fixture()
def guest(client):
    response = client.post("/api/v1/auth/guest")
    assert response.status_code == 200
    return response.json()["user"]
