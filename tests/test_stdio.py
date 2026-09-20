import asyncio
import os
import sys
from pathlib import Path
from mcp import ClientSession
from mcp.client.stdio import stdio_client,StdioServerParameters

def test_official_mcp_stdio_handshake():
    async def scenario():
        params=StdioServerParameters(command=sys.executable,args=["-m","apps.mcp.server"],cwd=str(Path(__file__).resolve().parents[1]),env={**os.environ,"HUMAN_RELAY_AGENT_KEY":""})
        async with stdio_client(params) as (read,write):
            async with ClientSession(read,write,read_timeout_seconds=15) as session:
                await session.initialize()
                tools=await session.list_tools()
                assert len(tools.tools)==10
                response=await session.call_tool("search_humans",{"capability":"web_research"})
                assert response.is_error
    asyncio.run(scenario())
