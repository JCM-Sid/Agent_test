"""
MCP Server 2 — Prévisions 3 jours via Open-Meteo + geocoding (gratuit, sans clé API)
"""
import json
import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

app = Server("forecast-server")

async def geocode(city: str) -> tuple[float, float]:
    url = "https://geocoding-api.open-meteo.com/v1/search"
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, params={"name": city, "count": 1, "language": "fr"})
        resp.raise_for_status()
        data = resp.json()

    if not data.get("results"):
        raise ValueError(f"Ville introuvable: {city}")

    r = data["results"][0]
    return r["latitude"], r["longitude"]


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="get_forecast",
            description="Retourne les prévisions météo sur 3 jours (min/max température, précipitations) pour une ville.",
            inputSchema={
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "Nom de la ville, ex: Lyon, Berlin, Montreal",
                    }
                },
                "required": ["city"],
            },
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name != "get_forecast":
        raise ValueError(f"Unknown tool: {name}")

    city = arguments["city"]
    lat, lon = await geocode(city)

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode",
        "timezone": "auto",
        "forecast_days": 3,
    }

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()

    daily = data["daily"]
    forecast = []
    for i in range(3):
        forecast.append({
            "date": daily["time"][i],
            "temp_max_c": daily["temperature_2m_max"][i],
            "temp_min_c": daily["temperature_2m_min"][i],
            "precipitation_mm": daily["precipitation_sum"][i],
            "weathercode": daily["weathercode"][i],
        })

    result = {"city": city, "latitude": lat, "longitude": lon, "forecast": forecast}
    return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]


# Fix: stdio_server est un async context manager, pas une coroutine
async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
