from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import select
from apps.api.models import *
from apps.api.database import transaction
from .conftest import headers
from .test_protocol import offer,active,payload

def test_capacity_race(client,setup):
    with transaction(client.app.state.engine) as s:s.get(Worker,setup[1]["id"]).maximum_active_tasks=1
    a=offer(client,setup,key="a",objective="Verify monthly pricing").json()
    b=offer(client,setup,key="b",objective="Verify annual pricing").json()
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda o:client.post(f'/api/v1/worker/offers/{o["id"]}/accept',headers=headers("worker")),[a,b]))
    assert sorted(r.status_code for r in results)==[200,409]

def test_credit_reservation_race(client,setup):
    with transaction(client.app.state.engine) as s:s.scalar(select(Organization)).credit_balance=400
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda key:offer(client,setup,key=key,objective=f"Verify pricing {key}"),["a","b"]))
    assert sorted(r.status_code for r in results)==[200,409]
    with transaction(client.app.state.engine) as s:assert s.scalar(select(Organization)).reserved==400

def test_review_timeout_holds_money(client,setup):
    t=active(client,setup);tid=t["id"]
    client.post(f"/api/v1/tasks/{tid}/result",headers=headers("worker"),json={"monthly_price":39,"annual_price":360})
    with transaction(client.app.state.engine) as s:s.get(Offer,t["task_offer_id"]).deadline_at=now()-1
    assert client.get(f"/api/v1/tasks/{tid}",headers=headers(setup[0]["api_key"])).json()["status"]=="admin_review"
    with transaction(client.app.state.engine) as s:assert s.scalar(select(Organization)).reserved==400
    assert client.post(f"/api/v1/admin/tasks/{tid}/resolve",headers=headers("admin"),json={"outcome":"completed","reason":"Verified valid result."}).status_code==200

def test_message_limits_and_terminal_session(client,setup):
    t=active(client,setup);path=f'/api/v1/tasks/{t["id"]}/messages';h=headers(setup[0]["api_key"])
    for _ in range(10):assert client.post(path,headers=h,json={"content":"Please confirm the public price."}).status_code==200
    assert client.post(path,headers=h,json={"content":"Another message."}).status_code==429

def test_cancel_decline_idempotent(client,setup):
    o=offer(client,setup).json()
    for _ in range(2):assert client.post(f'/api/v1/task-offers/{o["id"]}/cancel',headers=headers(setup[0]["api_key"])).status_code==200
    assert client.post(f'/api/v1/worker/offers/{o["id"]}/accept',headers=headers("worker")).status_code==409
    with transaction(client.app.state.engine) as s:
        assert s.scalar(select(Organization)).reserved==0
        assert len(list(s.scalars(select(CreditTransaction).where(CreditTransaction.type=="release"))))==1

def test_other_agent_cannot_read_contract(client,setup):
    second=client.post("/api/v1/agents",headers=headers("principal"),json={"display_name":"Other agent","allowed_capabilities":["web_research"]}).json()
    t=active(client,setup)
    for suffix in ("","/messages","/result"):
        assert client.get(f'/api/v1/tasks/{t["id"]}{suffix}',headers=headers(second["api_key"])).status_code==404

def test_failed_validation_leaves_no_money_effects(client,setup):
    assert offer(client,setup,response_schema={"type":"object","properties":{"x":{"type":"string","pattern":"(a+)+$"}}}).status_code==422
    with transaction(client.app.state.engine) as s:
        assert s.scalar(select(Organization)).reserved==0
        assert len(list(s.scalars(select(Offer))))==0
