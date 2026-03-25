# mcp__distant_api.py
import httpx
import uvicorn
from fastapi import FastAPI, Request
from mcp import types
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from tools.doctolib import call_doctolib_tool  # Importation de ta logique
from fastapi.responses import Response # Ajoutez cet import en haut

app = FastAPI()
mcp_server = Server("remote-bridge")
sse_transport = SseServerTransport("messages")


# =================================================================
# MCP SSE (pour n8n)
sse_transport = SseServerTransport("/messages")

# 2. Les fonctions de bridge (SANS décorateurs @app)
async def handle_sse(request: Request):
    # Ici, on utilise _send (avec underscore) car c'est ce que Starlette 
    # expose quand on passe par add_route
    async with sse_transport.connect_sse(
        request.scope, 
        request.receive, 
        request._send
    ) as (read_stream, write_stream):
        await mcp_server.run(
            read_stream, 
            write_stream, 
            mcp_server.create_initialization_options()
        )


async def handle_messages(request: Request):
    await sse_transport.handle_post_message(
        request.scope, 
        request.receive, 
        request._send
    )
    return Response(status_code=202)

# 3. Les routes (C'est cette méthode qui rend _send disponible correctement)
app.add_route("/sse", handle_sse)
app.add_route("/messages", handle_messages, methods=["POST"])

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
