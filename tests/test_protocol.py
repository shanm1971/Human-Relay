from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import select
from apps.api.database import transaction
from apps.api.models import *
from .conftest import headers

def payload(worker,**updates):
    return {"worker_id":worker["public_worker_id"],"capability":"web_research","objective":"Verify Pro plan pricing","instructions":"Read the public pricing page and report monthly and annual prices.","context":{"url":"https://example.com/pricing"},"response_schema":{"type":"object","properties":{"monthly_price":{"type":"number"},"annual_price":{"type":"number"}},"required":["monthly_price","annual_price"]},"offered_price":4,"deadline_minutes":10,"max_revisions":1,**updates}

def offer(client,setup,key="offer",**updates):
    a,w=setup
    return client.post("/api/v1/task-offers",headers=headers(a["api_key"],key),json=payload(w,**updates))

def active(client,setup):
    o=offer(client,setup);assert o.status_code==200,o.text
    response=client.post(f'/api/v1/worker/offers/{o.json()["id"]}/accept',headers=headers("worker"))
    assert response.status_code==200,response.text
    return response.json()

def test_definition_of_done(client,setup):
    agent,worker=setup;ah=headers(agent["api_key"])
    matches=client.post("/api/v1/humans/search",headers=ah,json={"capability":"web_research","max_price":5,"minimum_quality_score":0.9}).json()["matches"]
    assert matches[0]["worker_id"]==worker["public_worker_id"] and "user_id" not in matches[0]
    t=active(client,setup);tid=t["id"]
    with transaction(client.app.state.engine) as s:assert s.scalar(select(Organization)).reserved==400
    assert client.post(f"/api/v1/tasks/{tid}/messages",headers=ah,json={"content":"Please include monthly and annual pricing."}).status_code==200
    assert client.post(f"/api/v1/worker/tasks/{tid}/messages",headers=headers("worker"),json={"content":"I will check both prices."}).status_code==200
    assert client.post(f"/api/v1/worker/tasks/{tid}/result",headers=headers("worker"),json={"monthly_price":39,"annual_price":360}).status_code==200
    assert client.get(f"/api/v1/tasks/{tid}/result",headers=ah).json()["schema_valid"]
    for _ in range(3):assert client.post(f"/api/v1/tasks/{tid}/accept",headers=ah).json()["status"]=="completed"
    with transaction(client.app.state.engine) as s:
        org=s.scalar(select(Organization));assert (org.credit_balance,org.reserved)==(49600,0)
        earning=s.scalar(select(Earning));assert (earning.gross_amount,earning.platform_fee,earning.net_amount)==(400,80,320)
        assert len(list(s.scalars(select(Earning))))==1
        task=s.get(Task,tid);assert not task.intervention
        assert s.get(Worker,task.worker_id).tasks_completed==1
        events={a.event_type for a in s.scalars(select(Audit))}
        assert {"HUMAN_SEARCHED","TASK_OFFER_CREATED","CREDITS_RESERVED","TASK_OFFER_ACCEPTED","TASK_SESSION_OPENED","AGENT_MESSAGE_SENT","WORKER_MESSAGE_SENT","RESULT_SUBMITTED","RESULT_ACCEPTED","PAYMENT_RELEASED"}<=events
    assert client.post(f"/api/v1/tasks/{tid}/messages",headers=ah,json={"content":"More work?"}).status_code==409

def test_revision_and_schema_validation(client,setup):
    t=active(client,setup);tid=t["id"];ah=headers(setup[0]["api_key"]);wh=headers("worker")
    assert client.post(f"/api/v1/tasks/{tid}/result",headers=wh,json={"monthly_price":"wrong"}).status_code==422
    assert client.post(f"/api/v1/tasks/{tid}/accept",headers=ah).status_code==409
    result={"monthly_price":39,"annual_price":360}
    assert client.post(f"/api/v1/tasks/{tid}/result",headers=wh,json=result).status_code==200
    assert client.post(f"/api/v1/tasks/{tid}/revision",headers=ah,json={"reason":"Please confirm annual billing."}).status_code==200
    assert client.post(f"/api/v1/tasks/{tid}/result",headers=wh,json=result).status_code==200
    assert client.post(f"/api/v1/tasks/{tid}/revision",headers=ah,json={"reason":"One more change."}).status_code==409
    assert client.post(f"/api/v1/tasks/{tid}/fail",headers=ah,json={"reason":"Source could not be confirmed."}).json()["status"]=="admin_review"
    assert client.post(f"/api/v1/tasks/{tid}/accept",headers=ah).status_code==409
    assert client.post(f"/api/v1/admin/tasks/{tid}/resolve",headers=headers("admin"),json={"outcome":"failed","reason":"Source was unavailable."}).status_code==200
    with transaction(client.app.state.engine) as s:assert s.scalar(select(Organization)).reserved==0

def test_cross_actor_access(client,setup):
    t=active(client,setup)
    for token in ("other","worker2","principal"):
        assert client.get(f'/api/v1/tasks/{t["id"]}',headers=headers(token)).status_code==404
    assert client.post(f'/api/v1/tasks/{t["id"]}/accept',headers=headers("worker")).status_code==403

def test_idempotency_and_expiry(client,setup):
    o=offer(client,setup).json()
    assert offer(client,setup).json()["id"]==o["id"]
    assert offer(client,setup,offered_price=5).status_code==409
    with transaction(client.app.state.engine) as s:s.get(Offer,o["id"]).deadline_at=now()-1
    assert client.post(f'/api/v1/worker/offers/{o["id"]}/accept',headers=headers("worker")).status_code==409
    with transaction(client.app.state.engine) as s:assert s.scalar(select(Organization)).reserved==0

def test_policy_and_budget(client,setup):
    assert offer(client,setup,instructions="Please share the account password.").json()["error"]["category"]=="credential_access"
    assert offer(client,setup,response_schema={"type":"object","$ref":"https://evil.invalid"}).status_code==422
    assert offer(client,setup,offered_price=11).status_code==403
    assert offer(client,setup,deadline_minutes=20).status_code==422
    with transaction(client.app.state.engine) as s:s.get(Agent,setup[0]["id"]).hourly_limit=300
    assert offer(client,setup).json()["error"]["code"]=="SPENDING_LIMIT"

def test_concurrent_accept_and_settle(client,setup):
    o=offer(client,setup).json()
    with ThreadPoolExecutor(max_workers=4) as pool:
        responses=list(pool.map(lambda _:client.post(f'/api/v1/worker/offers/{o["id"]}/accept',headers=headers("worker")),range(4)))
    assert all(r.status_code==200 for r in responses)
    assert len({r.json()["id"] for r in responses})==1
    tid=responses[0].json()["id"]
    client.post(f"/api/v1/tasks/{tid}/result",headers=headers("worker"),json={"monthly_price":39,"annual_price":360})
    with ThreadPoolExecutor(max_workers=4) as pool:
        responses=list(pool.map(lambda _:client.post(f"/api/v1/tasks/{tid}/accept",headers=headers(setup[0]["api_key"])),range(4)))
    assert all(r.status_code==200 for r in responses)
    with transaction(client.app.state.engine) as s:
        assert len(list(s.scalars(select(Earning))))==1
        assert s.scalar(select(Organization)).credit_balance==49600

def test_report_freezes_session_and_preserves_reserve(client,setup):
    t=active(client,setup);tid=t["id"]
    assert client.post(f"/api/v1/worker/tasks/{tid}/report",headers=headers("worker"),json={"category":"scope_changed","reason":"The task scope changed."}).status_code==200
    assert client.post(f"/api/v1/tasks/{tid}/messages",headers=headers(setup[0]["api_key"]),json={"content":"Hello"}).status_code==409
    with transaction(client.app.state.engine) as s:assert s.scalar(select(Organization)).reserved==400
