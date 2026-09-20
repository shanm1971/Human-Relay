from .conftest import headers
from .test_protocol import active

def test_metrics_and_private_dashboards(client,setup):
    assert client.get("/api/v1/admin/dashboard",headers=headers("worker")).status_code==403
    assert client.get("/api/v1/organization/dashboard",headers=headers("worker")).status_code==403
    assert client.get("/api/v1/organization/dashboard",headers=headers("principal")).json()["metrics"]["autonomous_completion_rate"] is None
    t=active(client,setup)
    client.post(f'/api/v1/tasks/{t["id"]}/result',headers=headers("worker"),json={"monthly_price":39,"annual_price":360})
    client.post(f'/api/v1/tasks/{t["id"]}/accept',headers=headers(setup[0]["api_key"]))
    d=client.get("/api/v1/organization/dashboard",headers=headers("principal")).json()
    assert d["metrics"]["autonomous_completion_rate"]==1
    assert d["daily_spending_cents"]==400
    assert "api_key_hash" not in d["agents"][0]
    w=client.get("/api/v1/worker/dashboard",headers=headers("worker")).json()
    assert w["total_earnings_cents"]==320
    assert "organization" not in w

def test_admin_suspend_and_invite(client,setup):
    assert client.post(f'/api/v1/admin/agents/{setup[0]["id"]}/suspend',headers=headers("admin")).status_code==200
    assert client.get("/api/v1/me",headers=headers(setup[0]["api_key"])).status_code==401
    assert client.post("/api/v1/admin/invitations",headers=headers("admin"),json={"user_id":"new-worker","role":"worker","country":"US"}).status_code==200
