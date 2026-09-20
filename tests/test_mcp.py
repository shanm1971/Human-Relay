import asyncio
import json
from apps.mcp import server as module
from .conftest import headers

def test_mcp_tool_lifecycle(client,setup,monkeypatch):
    agent,worker=setup
    def api_call(method,path,body=None,key=None):
        r=client.request(method,"/api/v1"+path,json=body,headers=headers(agent["api_key"],key or "mcp"))
        if r.is_error:raise ValueError(r.text)
        return r.json()
    monkeypatch.setattr(module,"call",api_call)
    async def scenario():
        tools=await module.server.list_tools()
        assert len(tools)==10
        async def invoke(name,arguments):
            r=await module.server.call_tool(name,arguments)
            assert not r.is_error,r
            return json.loads(r.content[0].text)
        found=await invoke("search_humans",{"capability":"web_research"})
        assert found["matches"][0]["worker_id"]==worker["public_worker_id"]
        o=await invoke("hire_human",{"worker_id":worker["public_worker_id"],"capability":"web_research","objective":"Verify public pricing","instructions":"Inspect the public page and report the price.","context":{},"response_schema":{"type":"object","properties":{"price":{"type":"number"}},"required":["price"]},"price":4,"deadline_minutes":10,"idempotency_key":"mcp-lifecycle"})
        t=client.post(f'/api/v1/worker/offers/{o["id"]}/accept',headers=headers("worker")).json()
        await invoke("message_human",{"task_id":t["id"],"message":"Please confirm monthly pricing."})
        assert client.post(f'/api/v1/worker/tasks/{t["id"]}/result',headers=headers("worker"),json={"price":39}).status_code==200
        r=await invoke("get_human_result",{"task_id":t["id"]});assert r["schema_valid"]
        finished=await invoke("accept_human_result",{"task_id":t["id"]});assert finished["status"]=="completed"
    asyncio.run(scenario())
