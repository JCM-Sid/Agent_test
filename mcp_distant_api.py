# mcp__distant_api.py
import httpx
import uvicorn
from fastapi import FastAPI, Request
from mcp import types
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from tools.doctolib import call_doctolib_tool  # Importation de ta logique
from fastapi.responses import Response # Ajoutez cet import en haut
from starlette.applications import Starlette
from starlette.routing import Route


# 2️⃣ objets globaux
app = Starlette()
mcp_server = Server("remote-bridge")
#sse_transport = SseServerTransport("/messages")
sse_transport = SseServerTransport("/sse/messages")

# 3️⃣ outils MCP (AVANT les handlers ou après, mais après init serveur)

@mcp_server.list_tools()
async def list_tools():
    return [
        types.Tool(
            name="doctolib_search",
            description="Recherche de praticiens disponibles sur Doctolib.",
            inputSchema={
                "type": "object",
                "properties": {
                    "spec": {"type": "string"},
                    "location": {"type": "string"},
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

@mcp_server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "get_current_weather":
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"https://wttr.in/{arguments.get('city', 'Paris')}?format=j1")
            return [types.TextContent(type="text", text=resp.text)]
    if name == "doctolib_search":
        return await call_doctolib_tool(name, arguments)
    raise ValueError(f"Outil non trouvé : {name}")




# 4️⃣ handlers ASGI

async def handle_sse(scope, receive, send):
    if scope["type"] != "http":
        return

    async with sse_transport.connect_sse(scope, receive, send) as (r, w):
        await mcp_server.run(r, w, mcp_server.create_initialization_options())


async def handle_messages(scope, receive, send):
    if scope["type"] != "http":
        return

    await sse_transport.handle_post_message(scope, receive, send)

# 5️⃣ routes (TOUJOURS à la fin)

app.router.routes.append(
    Route("/sse", endpoint=handle_sse, methods=["GET"])
)

app.router.routes.append(
    Route("/sse/messages", endpoint=handle_messages, methods=["POST"])
)


# =================================================================
# MAIN
# =================================================================
if __name__ == "__main__":
    print("Démarrage serveur MCP+API sur le port 8123...")
    uvicorn.run(app, host="0.0.0.0", port=8123)
