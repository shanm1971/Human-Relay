import pytest
from sqlalchemy import select, text
from apps.api.database import transaction
from apps.api.models import Agent, CreditTransaction, Organization
from .conftest import headers

def test_authority_and_hashed_credentials(client,setup):
    agent,worker=setup
    with transaction(client.app.state.engine) as s:
        stored=s.get(Agent,agent["id"])
        assert stored.api_key_hash != agent["api_key"]
        assert stored.max_task_price == 1000
    assert client.get("/api/v1/me",headers=headers(agent["api_key"])).json()["role"]=="agent"
    assert client.post(f'/api/v1/agents/{agent["id"]}/revoke',headers=headers("other")).status_code==409
    assert client.post(f'/api/v1/agents/{agent["id"]}/revoke',headers=headers("principal")).status_code==200
    assert client.get("/api/v1/me",headers=headers(agent["api_key"])).status_code==401

def test_credit_idempotency(client,setup):
    for _ in range(2):
        assert client.post("/api/v1/organization/credits",headers=headers("principal"),json={"amount":500}).status_code==200
    assert client.post("/api/v1/organization/credits",headers=headers("principal"),json={"amount":501}).status_code==409
    with transaction(client.app.state.engine) as s:
        assert s.scalar(select(Organization)).credit_balance==50000
        assert len(list(s.scalars(select(CreditTransaction))))==1

def test_invitation_and_role_boundaries(client):
    assert client.get("/api/v1/me").status_code==401
    assert client.get("/api/v1/me",headers=headers("unknown")).status_code==401
    assert client.post("/api/v1/organizations",headers=headers("worker"),json={"name":"No"}).status_code==403
    assert client.post("/api/v1/admin/invitations",headers=headers("principal"),json={"user_id":"x","role":"worker","country":"US"}).status_code==403
    assert client.post("/api/v1/admin/invitations",headers=headers("admin"),json={"user_id":"x","role":"worker","country":"CA"}).status_code==422

def test_append_only_audit(client,setup):
    with pytest.raises(Exception,match="append-only"):
        with transaction(client.app.state.engine) as s: s.execute(text("DELETE FROM audit_events"))
