import asyncio
import json
import os
import re
import sys

import httpx
from dotenv import load_dotenv

from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server
from fastapi import FastAPI
from mcp.server.fastmcp import FastMCP

from openai import OpenAI

import time
from datetime import datetime
import urllib.request
import subprocess
from selenium import webdriver
from selenium.webdriver.common.by import By


from fastapi import FastAPI
import uvicorn


OLLAMA_MODEL = "minimax-m2.7:cloud" #"qwen3.5:4b"
# Interface OpenAI-compatible d'Ollama
ollama_client = OpenAI(
    api_key="ollama",
    base_url="http://localhost:11434/v1",
)

import json
import httpx
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from mcp.server import Server
from mcp.server.sse import SseServerTransport
import mcp.types as types

# 1. Création du serveur MCP
mcp_server = Server("mcp-orchestrator")

#@doctolib_app.call_tool()
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
    time.sleep(3)
    # Extraction infos
    h2s = browser.find_elements(By.TAG_NAME, "h2")
    #h2s = [h for h in h2s if h.text.startswith("Dr")]
    h2s = [h for h in h2s if h.text.strip().startswith("Dr") or h.text.strip().startswith("M.") or h.text.strip().startswith("Mme")]

    list_results = ""

    for h2 in h2s:
        browser.execute_script("arguments[0].scrollIntoView();", h2)
        time.sleep(2)
        
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
                continue

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
            print(f"{nom} | {dispo}")
        except Exception as e:
            print(f"Erreur: {e}")

    browser.close()
    return [types.TextContent(type="text", text=list_results)]


app = FastAPI()

@app.get("/api/doctolib")
async def search_doctolib(spec: str, location: str = "", limit: int = 10):
    result = await call_doctolib_tool("doctolib_search", 
                {"spec": spec, "location": location, "limit": limit})
    return {"result": result[0].text}

# 2. Déclaration de ton outil (Format Standard)
@mcp_server.list_tools()
async def list_tools():
    return [
        types.Tool(
            name="get_current_weather",
            description="Météo actuelle pour une ville.",
            inputSchema={
                "type": "object",
                "properties": {"city": {"type": "string"}},
                "required": ["city"],
            },
        )
    ]

@mcp_server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "get_current_weather":
        city = arguments.get("city", "Paris")
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"https://wttr.in/{city}?format=j1")
            return [types.TextContent(type="text", text=resp.text)]
    raise ValueError(f"Outil non trouvé : {name}")

# 3. Configuration du Transport SSE
# On définit l'URL où les messages seront postés
sse = SseServerTransport("/messages")

async def handle_sse(request):
    async with sse.connect_sse(request.scope, request.receive, request._send) as (read_stream, write_stream):
        await mcp_server.run(
            read_stream,
            write_stream,
            mcp_server.create_initialization_options()
        )

async def handle_messages(request):
    await sse.handle_post_message(request.scope, request.receive, request._send)

# 4. Création de l'application Web

#app = Starlette(
#    routes=[
#        Route("/sse", endpoint=handle_sse),
#        Route("/messages", endpoint=handle_messages, methods=["POST"]),
#        Mount("/api", app=fastapi_app),
#    ]
#)

app.add_route("/sse", handle_sse)
app.add_route("/messages", handle_messages, methods=["POST"])

if __name__ == "__main__":
    import uvicorn
    # On passe du port 6000 (dangereux) au port 8080 (standard et sûr)
    print("Démarrage manuel du serveur MCP sur le port 8123...")
    uvicorn.run(app, host="0.0.0.0", port=8123)