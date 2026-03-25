# mcp__distant_api.py
import httpx
import uvicorn
from fastapi import FastAPI, Request
from mcp import types
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from tools.doctolib import call_doctolib_tool  # Importation de ta logique

app = FastAPI()
mcp_server = Server("remote-bridge")
sse_transport = SseServerTransport("messages")


# =================================================================
# MCP SSE (pour n8n)
@app.get("/sse")
async def handle_sse(request: Request):
    async with sse_transport.connect_sse(request.scope, request.receive, request._send) as (read, write):
        await mcp_server.run(read, write, mcp_server.create_initialization_options())


@app.post("/messages")
async def handle_messages(request: Request):
    await sse_transport.handle_post_message(request.scope, request.receive, request._send)


# =================================================================
# Liste des OUTILS distants


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
    ]


# =================================================================
# Appel des outils


@mcp_server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "get_current_weather":
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"https://wttr.in/{arguments.get('city', 'Paris')}?format=j1")
            return [types.TextContent(type="text", text=resp.text)]
    if name == "doctolib_search":
        return await call_doctolib_tool(name, arguments)
    raise ValueError(f"Outil non trouvé : {name}")


## =================================================================
# ROUTES FASTAPI (pour tests manuels)
# app.add_route("/sse", handle_sse)
# app.add_route("/messages", handle_messages, methods=["POST"])

# =================================================================
# MAIN
# =================================================================
if __name__ == "__main__":
    print("Démarrage serveur MCP+API sur le port 8123...")
    uvicorn.run(app, host="0.0.0.0", port=8123)
