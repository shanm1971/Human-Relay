from .conftest import headers
from .test_protocol import offer,active
from apps.api.models import *
from apps.api.database import transaction
from sqlalchemy import select

def test_http_body_limit(client):
    r=client.post("/api/v1/humans/search",headers=headers("principal"),content="a"*65537)
    assert r.status_code==413

def test_enabled_categories_only(client,setup):
    assert offer(client,setup,capability="visual_verification").status_code==403
    r=client.post("/api/v1/humans/search",headers=headers(setup[0]["api_key"]),json={"capability":"medical_diagnosis"})
    assert r.status_code==422

def test_worker_capability_change_prevents_acceptance(client,setup):
    o=offer(client,setup).json()
    client.put("/api/v1/worker/profile",headers=headers("worker"),json={"capabilities":["content_judgment"]})
    assert client.post(f'/api/v1/worker/offers/{o["id"]}/accept',headers=headers("worker")).status_code==409

def test_active_timeout_releases_and_audits(client,setup):
    t=active(client,setup)
    with transaction(client.app.state.engine) as s:s.get(Offer,t["task_offer_id"]).deadline_at=now()-1
    assert client.get(f'/api/v1/tasks/{t["id"]}',headers=headers("worker")).json()["status"]=="expired"
    with transaction(client.app.state.engine) as s:
        assert s.scalar(select(Organization)).reserved==0
        assert s.get(Worker,setup[1]["id"]).tasks_failed==1
        assert any(e.event_type=="TASK_EXPIRED" for e in s.scalars(select(Audit)))
