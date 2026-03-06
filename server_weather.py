"""
MCP Server 1 — Météo actuelle via wttr.in (gratuit, sans clé API)
"""
import json
import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

app = Server("weather-server")


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="get_current_weather",
            description="Retourne la météo actuelle pour une ville donnée (température, conditions, vent).",
            inputSchema={
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "Nom de la ville, ex: Paris, Tokyo, New York",
                    }
                },
                "required": ["city"],
            },
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name != "get_current_weather":
        raise ValueError(f"Unknown tool: {name}")

    city = arguments["city"]
    url = f"https://wttr.in/{city}?format=j1"

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()

    current = data["current_condition"][0]
    result = {
        "city": city,
        "temp_c": current["temp_C"],
        "feels_like_c": current["FeelsLikeC"],
        "description": current["weatherDesc"][0]["value"],
        "humidity_pct": current["humidity"],
        "wind_kmh": current["windspeedKmph"],
    }

    return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]


# Fix: stdio_server est un async context manager, pas une coroutine
async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
