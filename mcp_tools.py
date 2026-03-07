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
# SERVEUR 4: LINKEDIN (Profil & Post)
# =================================================================
linkedin_app = Server("linkedin-server")
LINKEDIN_API_URL = "https://api.linkedin.com/v2"  # https://www.linkedin.com/developers/tools/oauth/redirect
LINKEDIN_TOKEN = "AQX_ayhDb_P4H9PJA5kKqZPX4T8rDfNPM4UX1WGTxZXUptfwI6WsIi_UMkVcAoBE2ueNmZDz4JgMFrGViyXquwHRLSIW41o7aVTFLuxpTxyI_R97waDJBlqG3Sfrzpkqa2DM-s-QFxjYQYUyq_PiKKDetQgCcy8EgihQL-xIDGaIHFDF1wfDv2aacadL7vCZ_RbJh1pzYy2Z_hay0fGUh_THiRxKO8OuoZiFRdWdLCLoG7myT7nJNfsyVd6zTtnLtDZ_oIB0FQUgQscRYSyWDIk93-kpupYrFG76lPk2mp4css8UsMdKz7F9ayMDm4Fqr7zPW7T3u86ZWrNAXi8kACIJQ-Lndw"


@linkedin_app.list_tools()
async def list_linkedin_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="get_my_profile",
            description="Récupère les informations de base de mon profil LinkedIn (Nom, ID).",
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="post_to_linkedin",
            description="Publie un message texte sur mon fil d'actualité LinkedIn.",
            inputSchema={
                "type": "object",
                "properties": {"text": {"type": "string", "description": "Le contenu du post à publier"}},
                "required": ["text"],
            },
        ),
    ]


@linkedin_app.call_tool()
async def call_linkedin_tool(name: str, arguments: dict) -> list[types.TextContent]:
    headers = {
        "Authorization": f"Bearer {LINKEDIN_TOKEN}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        if name == "get_my_profile":
            # CHANGEMENT : Utilisation de l'endpoint OpenID Connect userinfo
            # Cet endpoint fonctionne avec le scope 'profile' ou 'openid'
            resp = await client.get("https://api.linkedin.com/v2/userinfo", headers=headers)

            if resp.status_code == 403:
                return [types.TextContent(type="text", text="Erreur 403 : Vérifiez que le scope 'profile' est coché dans le Token Generator.")]

            resp.raise_for_status()
            profile = resp.json()

            # CHANGEMENT : Les clés JSON sont différentes en OpenID Connect
            first_name = profile.get("given_name", "Inconnu")
            last_name = profile.get("family_name", "Inconnu")
            sub_id = profile.get("sub")  # C'est l'ID unique de l'utilisateur

            text = f"Profil : {first_name} {last_name} (ID interne: {sub_id})"
            return [types.TextContent(type="text", text=text)]

        elif name == "post_to_linkedin":
            # Pour poster, on a toujours besoin de l'ID sous forme de URN
            # On récupère le 'sub' (ID) via userinfo
            me_resp = await client.get("https://api.linkedin.com/v2/userinfo", headers=headers)
            me_resp.raise_for_status()
            author_id = me_resp.json()["sub"]

            # Le reste de la requête UGC reste identique, mais assure-toi que
            # X-Restli-Protocol-Version est présent UNIQUEMENT pour les requêtes v2 standard
            headers["X-Restli-Protocol-Version"] = "2.0.0"

            post_data = {
                "author": f"urn:li:person:{author_id}",
                "lifecycleState": "PUBLISHED",
                "specificContent": {"com.linkedin.ugc.ShareContent": {"shareCommentary": {"text": arguments["text"]}, "shareMediaCategory": "NONE"}},
                "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
            }

            resp = await client.post(f"{LINKEDIN_API_URL}/ugcPosts", headers=headers, json=post_data)
            if resp.status_code == 201:
                return [types.TextContent(type="text", text="✅ Post publié avec succès sur LinkedIn !")]
            else:
                return [types.TextContent(type="text", text=f"❌ Erreur lors de la publication : {resp.text}")]

    return [types.TextContent(type="text", text="Outil non reconnu")]


# =================================================================
# LOGIQUE DE LANCEMENT (Sélecteur via argument)
# =================================================================
async def run_server(server_type: str):
    apps = {"weather": weather_app, "forecast": forecast_app, "searx": searx_app, "linkedin": linkedin_app}

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
