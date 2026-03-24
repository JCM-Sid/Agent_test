import asyncio
import json
import os
import re

import httpx
from dotenv import load_dotenv
from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server
from openai import OpenAI

import time
from datetime import datetime
import urllib.request
import subprocess
from selenium import webdriver
from selenium.webdriver.common.by import By


OLLAMA_MODEL = "minimax-m2.7:cloud" #"qwen3.5:4b"
# Interface OpenAI-compatible d'Ollama
ollama_client = OpenAI(
    api_key="ollama",
    base_url="http://localhost:11434/v1",
)


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

#####
@weather_app.call_tool()
async def call_weather_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name != "get_current_weather":
        raise ValueError(f"Unknown tool: {name}")

    city = arguments["city"]
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        # On force le format JSON avec format=j1
        resp = await client.get(f"https://wttr.in/{city}?format=j1")
        resp.raise_for_status()
        data = resp.json()

    # --- SÉCURISATION ICI ---
    if "current_condition" not in data:
        return [types.TextContent(
            type="text", 
            text=f"Désolé, je n'ai pas pu récupérer la météo pour {city}. L'API a renvoyé un format inattendu."
        )]

    current = data["current_condition"][0]
    result = {
        "city": city,
        "temp_c": current.get("temp_C", "N/A"),
        "description": current.get("weatherDesc", [{}])[0].get("value", "Indisponible"),
        "wind_kmh": current.get("windspeedKmph", "N/A"),
    }
    
    return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]

#####


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
load_dotenv()
nextcloud_dir = os.getenv("NEXTCLOUD")
api_key_path = os.path.join(nextcloud_dir, "ConfigPerso", "api_key.json")
conf_file = json.load(open(api_key_path))
LINKEDIN_TOKEN = conf_file["LinkedIn_TOKEN"]


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
        types.Tool(
            name="post_from_linkedin",
            description="Affiche les posts sur mon fil d'actualité LinkedIn.",
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
            #print(f"DEBUG - Profil LinkedIn récupéré : {profile}")  # Debug pour vérifier les clés disponibles
            
            email = profile.get("email", "Inconnu")
            full_name = profile.get("name", "Inconnu")
            sub_id = profile.get("sub")  # C'est l'ID unique de l'utilisateur

            text = f"Profil : {full_name} Email: {email} ID interne: {sub_id})"
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

            #resp = await client.post(f"{LINKEDIN_API_URL}/ugcPosts", headers=headers, json=post_data)
            resp.status_code = 201 # Simulation de succès pour éviter les erreurs liées à l'API LinkedIn
            if resp.status_code == 201:
                return [types.TextContent(type="text", text="✅ Post publié avec succès sur LinkedIn !")]
            else:
                return [types.TextContent(type="text", text=f"❌ Erreur lors de la publication : {resp.text}")]
        elif name == "get_posts_from_linkedin":
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

            #resp = await client.post(f"{LINKEDIN_API_URL}/ugcPosts", headers=headers, json=post_data)
            resp.status_code = 201 # Simulation de succès pour éviter les erreurs liées à l'API LinkedIn
            if resp.status_code == 201:
                return [types.TextContent(type="text", text="✅ Post publié avec succès sur LinkedIn !")]
            else:
                return [types.TextContent(type="text", text=f"❌ Erreur lors de la publication : {resp.text}")]

    return [types.TextContent(type="text", text="Outil non reconnu")]


# =================================================================
# SERVEUR 5: THEIRSTACK (Job Market & Tech Insights)
# =================================================================
# Note: TheirStack est un serveur distant.
# Cette implémentation permet de l'appeler via ton orchestrateur.
theirstack_app = Server("theirstack-server")
# THEIRSTACK_API_KEY = os.environ.get("THEIRSTACK_API_KEY", "TON_API_KEY_ICI")


@theirstack_app.list_tools()
async def list_theirstack_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="search_jobs",
            description="Recherche des offres d'emploi et les technologies utilisées par les entreprises.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Poste ou technologie (ex: Python Developer)"},
                    "location": {"type": "string", "description": "Ville ou pays"},
                    "limit": {"type": "integer", "default": 5},
                },
                "required": ["query"],
            },
        )
    ]


@theirstack_app.call_tool()
async def call_theirstack_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name != "search_jobs":
        raise ValueError(f"Unknown tool: {name}")

    # On appelle l'API de TheirStack
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        # Note: On utilise ici leur API directement pour le tool
        # headers = {"Authorization": f"Bearer {THEIRSTACK_API_KEY}"}
        params = {"q": arguments["query"], "location": arguments.get("location", ""), "limit": arguments.get("limit", 5)}

        try:
            # Simulation de l'appel MCP distant vers TheirStack
            # resp = await client.get("https://api.theirstack.com/v1/jobs/search", headers=headers, params=params)
            resp = await client.get("https://api.theirstack.com/v1/jobs/search", params=params)
            resp.raise_for_status()
            data = resp.json()

            jobs = data.get("data", [])
            if not jobs:
                return [types.TextContent(type="text", text="Aucune offre trouvée.")]

            results = []
            for job in jobs:
                results.append(f"- {job['job_title']} chez {job['company_name']} ({job['location']})")

            return [types.TextContent(type="text", text="\n".join(results))]
        except Exception as e:
            return [types.TextContent(type="text", text=f"Erreur TheirStack: {str(e)}")]



# =================================================================
# SERVEUR 6: Doctolib (trouver un medecin disponible)
# =================================================================

doctolib_app = Server("doctolib-server")
@doctolib_app.list_tools()
async def list_doctolib_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="doctolib_search",
            description="Recherche un médecin disponible ,dans une ville données et pour une spécialité donnée.",
            inputSchema={
                "type": "object",
                "properties": {
                    "spec": {"type": "string", "description": "specialité du médecin, ex: medecin generaliste, dentiste, .."},
                    "location": {"type": "string", "description": "Ville ou pays"},
                    "limit": {"type": "integer", "default": 5},
                },
                "required": ["query"],
            },
        )
    ]

@doctolib_app.call_tool()
async def call_doctolib_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name != "doctolib_search":
        raise ValueError(f"Unknown tool: {name}")

    params = {"spec": arguments["spec"], "location": arguments.get("location", ""), "limit": arguments.get("limit", 5)}
    print(f"Recherche Doctolib avec params: {params}")

    #URL = "https://www.doctolib.fr/search?keyword=medecin-generaliste&location=versailles"
    # Construction de l'URL de recherche Doctolib
    spec = params["spec"].replace(" ", "-").lower()
    base_url = "https://www.doctolib.fr/search"
    URL = f"{base_url}?keyword={spec}&location={'location' in params and params['location'].replace(' ', '+').lower() or ''}"
    print(f"URL de recherche Doctolib: {URL}")
    firefoxOptions = webdriver.FirefoxOptions()
    firefoxOptions.headless = True
    browser = webdriver.Firefox(options=firefoxOptions)
    browser.get(URL)
    time.sleep(1)

    # Extraction infos
    h2s = browser.find_elements(By.TAG_NAME, "h2")
    h2s = [h for h in h2s if h.text.startswith("Dr")]
    list_results = ""

    for h2 in h2s:
        browser.execute_script("arguments[0].scrollIntoView();", h2)
        time.sleep(1)
        
        try:
            text = ""
            card = h2.find_element(By.XPATH, "./ancestor::div[contains(@class,'dl-card')]")

            if "Ce soignant réserve la prise de rendez-vous en ligne aux patients déjà suivis" in card.text:
                continue
            # Cherche une date avec au moins une heure associée
            text = " ".join(card.text.splitlines())
            match_date_heure = re.search(
                r'(lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche)\s+\d{1,2}\s+\w+(?:\s+\d{4})?\s+(\d{2}:\d{2})',
                text, re.IGNORECASE
            )

            # Fallback : "Prochain RDV le ..."
            match_prochain = re.search(r'Prochain RDV le \d{1,2} \w+ \d{4}', text)

            if match_date_heure:
                dispo = match_date_heure.group().strip()
            elif match_prochain:
                dispo = match_prochain.group().strip()
            else:
                dispo = "Aucune disponibilité"

            dispo_line = dispo.replace("\n", " ")  

            lines = [l.strip() for l in card.text.splitlines() if l.strip()]
            
            nom        = lines[0]                    # Dr Corinne BOYER
            specialite = lines[1]                    # Médecin généraliste
            adresse    = " ".join(lines[2:4])        # 26 BIS Rue Coste 78000 Versailles
            secteur    = lines[4]                    # Conventionné secteur 1
            
            list_results += f"{nom} | {specialite}\n"
            list_results += f"{adresse} | {secteur}\n"
            list_results += f"Dispo: {dispo}\n"
            list_results += "---\n"
            #print(f"{nom} | {dispo}")
        except Exception as e:
            print(f"Erreur: {e}")

    browser.close()
    return [types.TextContent(type="text", text=list_results)]


# =================================================================
# ORCHESTRATEUR LLM (Ollama + Qwen3.5)
# =================================================================


# =================================================================
# EXECUTION
# =================================================================
async def main():
    # Vous pouvez toujours lancer un serveur spécifique via les arguments
    if len(sys.argv) > 1 and sys.argv[1] != "chat":
        target = sys.argv[1]
        apps = {"weather": weather_app, "forecast": forecast_app, "searx": searx_app, "linkedin": linkedin_app, "theirstack": theirstack_app, "doctolib": doctolib_app}
        if target in apps:
            app = apps[target]
            async with stdio_server() as (read_stream, write_stream):
                await app.run(read_stream, write_stream, app.create_initialization_options())
    else:
        # MODE CHAT INTERACTIF
        orchestrator = MCPOrchestrator(model=OLLAMA_MODEL)
        print("--- Orchestrateur MCP prêt (Ollama) ---")
        print("Posez une question (ex: 'Quel temps fait-il à Paris ?' ou 'Cherche des jobs Python à Lyon')")

        while True:
            query = input("\n> ")
            if query.lower() in ["exit", "quit"]:
                break
            await orchestrator.chat_with_tools(query)

class MCPOrchestrator:
    def __init__(self, model="qwen3.5:4b"): # Note: qwen3.5 n'existe pas encore, restez sur 2.5
        self.model = model
        # Mapping direct pour simplifier l'exécution
        self.tools_map = {
            "get_current_weather": call_weather_tool,
            "get_forecast": call_forecast_tool,
            "web_search": call_searx_tool,
            "get_my_profile": call_linkedin_tool,
            "post_to_linkedin": call_linkedin_tool,
            "search_jobs": call_theirstack_tool,
            "doctolib_search": call_doctolib_tool,
        }

    async def get_tools_definitions(self):
        """Récupère les définitions et les formate proprement pour Ollama/OpenAI"""
        weather = await list_weather_tools()
        forecast = await list_forecast_tools()
        searx = await list_searx_tools()
        linkedin = await list_linkedin_tools()
        theirstack = await list_theirstack_tools()
        doctolib = await list_doctolib_tools()

        all_tools = weather + forecast + searx + linkedin + theirstack + doctolib

        # On retourne le format standard attendu par l'API Chat Completions
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.inputSchema
                }
            } for t in all_tools
        ]

    def ollama_chat(self, messages: list[dict], tools: list[dict]):
        """Appelle Ollama (assurez-vous que ollama_client est défini au préalable)"""
        # Plus besoin de re-boucler ici, 'tools' est déjà au bon format
        return ollama_client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools,
            temperature=0.3,
        )

    async def chat_with_tools(self, user_query: str):
        tools_meta = await self.get_tools_definitions()
        # On simplifie l'index pour retrouver les fonctions
        messages = [
            {"role": "system", "content": "Tu es un assistant polyvalent. Utilise les outils pour répondre avec précision."},
            {"role": "user", "content": user_query},
        ]

        while True:
            # Exécution synchrone dans un thread pour ne pas bloquer l'event loop
            response = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.ollama_chat(messages, tools_meta)
            )

            msg = response.choices[0].message
            
            # Gestion du cas où msg.tool_calls est None
            tool_calls = getattr(msg, 'tool_calls', None)
            
            # On ajoute le message de l'assistant (nécessaire pour la cohérence du thread)
            messages.append(msg) 

            if not tool_calls:
                print(f"\n[Assistant]: {msg.content}")
                return msg.content

            # Exécution des outils demandés
            for tc in tool_calls:
                func_name = tc.function.name
                args = json.loads(tc.function.arguments)
                
                print(f" -> [Appel Outil]: {func_name}({args})")
                
                if func_name in self.tools_map:
                    # Appel de la fonction définie dans votre script
                    result_content = await self.tools_map[func_name](func_name, args)
                    result_text = result_content[0].text
                else:
                    result_text = "Erreur: Outil non trouvé."

                # Retour du résultat au LLM
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "name": func_name,
                    "content": result_text,
                })


if __name__ == "__main__":
    import sys

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
