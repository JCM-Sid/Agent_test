import asyncio
import json

import httpx
from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server

# --- CONFIGURATION COMMUNE ---
TIMEOUT = 15.0
HEADERS = {"User-Agent": "Mozilla/5.0 (MCP Agent)"}

# =================================================================
# SERVEUR 1: WEATHER (wttr.in)
# =================================================================
weather_app = Server("weather-server")


@weather_app.list_tools()
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


@weather_app.call_tool()
async def call_weather_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name != "get_current_weather":
        raise ValueError(f"Unknown tool: {name}")

    city = arguments["city"]
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(f"https://wttr.in/{city}?format=j1")
        resp.raise_for_status()
        data = resp.json()

    current = data["current_condition"][0]
    result = {
        "city": city,
        "temp_c": current["temp_C"],
        "description": current["weatherDesc"][0]["value"],
        "wind_kmh": current["windspeedKmph"],
    }
    return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]


# =================================================================
# SERVEUR 2: FORECAST (Open-Meteo)
# =================================================================
forecast_app = Server("forecast-server")


async def geocode(city: str) -> tuple[float, float]:
    url = "https://geocoding-api.open-meteo.com/v1/search"
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(url, params={"name": city, "count": 1, "language": "fr"})
        resp.raise_for_status()
        data = resp.json()

    if not data.get("results"):
        raise ValueError(f"Ville introuvable: {city}")
    r = data["results"][0]
    return r["latitude"], r["longitude"]


@forecast_app.list_tools()
async def list_forecast_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="get_forecast",
            description="Prévisions sur 3 jours pour une ville.",
            inputSchema={
                "type": "object",
                "properties": {"city": {"type": "string"}},
                "required": ["city"],
            },
        )
    ]


@forecast_app.call_tool()
async def call_forecast_tool(name: str, arguments: dict) -> list[types.TextContent]:
    city = arguments["city"]
    lat, lon = await geocode(city)

    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
        "timezone": "auto",
        "forecast_days": 3,
    }
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get("https://api.open-meteo.com/v1/forecast", params=params)
        resp.raise_for_status()
        data = resp.json()

    daily = data["daily"]
    forecast = [{"date": daily["time"][i], "max": daily["temperature_2m_max"][i], "min": daily["temperature_2m_min"][i]} for i in range(3)]
    return [types.TextContent(type="text", text=json.dumps({"city": city, "forecast": forecast}, ensure_ascii=False))]


# =================================================================
# SERVEUR 3: SEARXNG (Web Search)
# =================================================================
searx_app = Server("searx-server")
SEARX_URL = "https://ddcm-local.myftp.org/searx/search"


@searx_app.list_tools()
async def list_searx_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="web_search",
            description="Recherche web pour identifier des lieux ou des faits.",
            inputSchema={
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        )
    ]


@searx_app.call_tool()
async def call_searx_tool(name: str, arguments: dict) -> list[types.TextContent]:
    params = {"q": arguments["query"], "format": "json", "language": "fr-FR"}
    async with httpx.AsyncClient(headers=HEADERS, timeout=TIMEOUT) as client:
        resp = await client.get(SEARX_URL, params=params)
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])[:3]
        text = "\n".join([f"- {r['title']}: {r['content']}" for r in results])
    return [types.TextContent(type="text", text=text or "Aucun résultat trouvé.")]


# =================================================================
# LOGIQUE DE LANCEMENT (Sélecteur via argument)
# =================================================================
async def run_server(server_type: str):
    apps = {"weather": weather_app, "forecast": forecast_app, "searx": searx_app}

    if server_type not in apps:
        print("Usage: python mcp_tools.py [weather|forecast|searx]")
        return

    app = apps[server_type]
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    import sys

    target = sys.argv[1] if len(sys.argv) > 1 else "weather"
    asyncio.run(run_server(target))
