import os
import pytest
from fastapi.testclient import TestClient
from apps.api.main import create_app
from apps.api.database import transaction
from apps.api.models import Identity, Worker

@pytest.fixture
def client(tmp_path):
    app = create_app(f"sqlite:///{tmp_path / 'test.db'}", dev_auth=True, dev_tokens={"principal":"p", "worker":"w", "admin":"a", "other":"p2", "worker2":"w2"})
    with transaction(app.state.engine) as s:
        s.add_all([Identity(id="p",role="principal"),Identity(id="p2",role="principal"),Identity(id="w",role="worker"),Identity(id="w2",role="worker"),Identity(id="a",role="admin")]); s.flush()
        s.add_all([Worker(user_id="w"),Worker(user_id="w2")])
    with TestClient(app) as c: yield c
    app.state.engine.dispose()

def headers(token, key="test"):
    return {"Authorization":f"Bearer {token}", "Idempotency-Key":key}

@pytest.fixture
def setup(client):
    assert client.post("/api/v1/organizations",headers=headers("principal"),json={"name":"Acme"}).status_code==200
    assert client.post("/api/v1/organization/credits",headers=headers("principal"),json={"amount":500}).status_code==200
    agent = client.post("/api/v1/agents",headers=headers("principal"),json={"display_name":"ResearchAgent-7","allowed_capabilities":["web_research"],"max_task_price":10}).json()
    worker = client.put("/api/v1/worker/profile",headers=headers("worker"),json={"capabilities":["web_research"],"availability":"available"}).json()
    return agent,worker
