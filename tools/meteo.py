import httpx
from fastapi import FastAPI
from mcp.server import Server
from mcp.server.sse import SseServerTransport

# =================================================================
# CONFIG
# =================================================================
mcp_server = Server("mcp-orchestrator")
sse = SseServerTransport("/messages")
app = FastAPI()


@app.get("/api/weather")
async def get_weather(city: str):
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"https://wttr.in/{city}?format=j1")
        # return [types.TextContent(type="text", text=resp.text)]
        return resp.json()
