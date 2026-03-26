import re
import time

import httpx
import uvicorn
from fastapi import FastAPI
from mcp import types
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from selenium import webdriver
from selenium.webdriver.common.by import By

from doctolib import call_doctolib_tool  # Importation de ta logique
from rag_notes import call_rag_notes_tool # Importation de ta logique

# =================================================================
# CONFIG
# =================================================================
mcp_server = Server("mcp-orchestrator")
sse = SseServerTransport("/messages")
app = FastAPI()


# =================================================================
# ROUTES FASTAPI
# =================================================================
@app.get("/api/doctolib")
async def search_doctolib(spec: str, location: str = "", limit: int = 10):
    result = await call_doctolib_tool("doctolib_search", {"spec": spec, "location": location, "limit": limit})
    return {"result": result[0].text}


@app.get("/api/weather")
async def get_weather(city: str):
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"https://wttr.in/{city}?format=j1")
        # return [types.TextContent(type="text", text=resp.text)]
        return resp.json()

@app.get("/api/rag_notes")
async def search_notes(query: str, k: int = 3):
    # This is a placeholder for the actual RAG implementation
    result = await call_ragnotes_tool("rag_notes_search", {"query": query, "k": k})
    return {"result": f"Résultats pour la requête: {query}"}


# =================================================================
# MCP SSE (pour n8n)
# =================================================================
@mcp_server.list_tools()
async def list_tools():
    return [
        types.Tool(
            name="doctolib_search",
            description="Recherche de praticiens disponibles sur Doctolib.",
            inputSchema={
                "type": "object",
                "properties": {
                    "spec": {"type": "string", "description": "Spécialité ex: medecin-generaliste"},
                    "location": {"type": "string", "description": "Ville"},
                    "limit": {"type": "integer", "default": 10},
                },
                "required": ["spec"],
            },
        ),
        types.Tool(
            name="get_current_weather",
            description="Météo actuelle pour une ville.",
            inputSchema={
                "type": "object",
                "properties": {"city": {"type": "string"}},
                "required": ["city"],
            },
        ),
        types.Tool(
            name="rag_notes_search",
            description="Recherche d'informations dans mes notes personnelles",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "k": {"type": "string"},
                    "refresh_db": {"type": "boolean"},
                    },
                "required": ["query"],
            },
        ),
    ]


@mcp_server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "get_current_weather":
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"https://wttr.in/{arguments.get('city', 'Paris')}?format=j1")
            return [types.TextContent(type="text", text=resp.text)]
    if name == "doctolib_search":
        return await call_doctolib_tool(name, arguments)
    if name == "rag_notes_search":
        return await call_rag_notes_tool(name, arguments)

    raise ValueError(f"Outil non trouvé : {name}")


async def handle_sse(request):
    async with sse.connect_sse(request.scope, request.receive, request._send) as (read_stream, write_stream):
        await mcp_server.run(read_stream, write_stream, mcp_server.create_initialization_options())


async def handle_messages(request):
    await sse.handle_post_message(request.scope, request.receive, request._send)


app.add_route("/sse", handle_sse)
app.add_route("/messages", handle_messages, methods=["POST"])

# =================================================================
# MAIN
# =================================================================
if __name__ == "__main__":
    print("Démarrage serveur MCP+API sur le port 8123...")
    uvicorn.run(app, host="0.0.0.0", port=8123)
