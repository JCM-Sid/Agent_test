import httpx
from fastapi import FastAPI
from mcp.server import Server
from mcp.server.sse import SseServerTransport
import mcp.types as types

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


async def list_weather_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="get_current_weather",
            description="Météo actuelle pour une ville (température, vent).",
            inputSchema={
                "type": "object",
                "properties": {"city": {"type": "string", "description": "Ex: Paris, Tokyo"}},
                "required": ["city"],
            },
        )
    ]
