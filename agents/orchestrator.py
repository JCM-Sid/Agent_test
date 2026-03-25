#
# Demo MCP multi-serveur — météo actuelle (wttr.in) + prévisions (open-meteo)
# LLM : Ollama local via interface OpenAI-compatible — 100% gratuit
#
import asyncio
import json
import os
import sys
from contextlib import AsyncExitStack
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.sse import sse_client  # Import important pour le remote
from mcp.client.stdio import stdio_client
from openai import OpenAI
import httpx 

OLLAMA_MODEL = "minimax-m2.7:cloud"  # "qwen3.5:4b"
# Interface OpenAI-compatible d'Ollama
ollama_client = OpenAI(
    api_key="ollama",
    base_url="http://localhost:11434/v1",
)

# Ajout du dossier parent au sys.path pour importer mcp_local_server si besoin
sys.path.append(str(Path(__file__).parent.parent))


class MCPOrchestrator:
    def __init__(self, model):
        self.model = model
        self.exit_stack = AsyncExitStack()
        self.sessions: list[ClientSession] = []

    async def connect_local_server(self, command: str, args: list[str]):
        # Connexion au hub local via Stdio
        params = StdioServerParameters(
            command=command,
            args=args,
            env=os.environ.copy(),  # Il est souvent préférable de copier l'env actuel
        )
        read, write = await self.exit_stack.enter_async_context(stdio_client(params))
        session = await self.exit_stack.enter_async_context(ClientSession(read, write))
        await session.initialize()
        self.sessions.append(session)
        print("✅ Serveur Local connecté")

    async def connect_remote_server(self, url: str):
        print(f"Tentative de connexion SSE sur : {url}")
        try:
            read, write = await self.exit_stack.enter_async_context(sse_client(url))
            session = await self.exit_stack.enter_async_context(ClientSession(read, write))
            await asyncio.wait_for(session.initialize(), timeout=10.0)  # ← timeout
            self.sessions.append(session)
            print(f"✅ Serveur Remote connecté : {url}")
        except asyncio.TimeoutError:
            print("❌ Timeout sur session.initialize()")
            raise
        except Exception as e:
            print(f"❌ Erreur de connexion : {e}")
            raise

    async def get_all_tools(self):
        """Récupère les outils de TOUS les serveurs connectés"""
        all_tools = []
        for session in self.sessions:
            result = await session.list_tools()
            all_tools.extend(result.tools)
        return all_tools

    async def call_tool(self, name: str, arguments: dict):
        """Cherche et appelle l'outil sur la bonne session"""
        for session in self.sessions:
            tools = await session.list_tools()
            if any(t.name == name for t in tools.tools):
                return await session.call_tool(name, arguments)
        raise ValueError(f"Outil {name} non trouvé sur aucun serveur.")

    def ollama_chat(self, messages: list[dict], tools: list[dict]) -> any:
        """Appelle Ollama via l'interface OpenAI-compatible (synchrone)."""
        openai_tools = [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": t["input_schema"],
                },
            }
            for t in tools
        ]
        return ollama_client.chat.completions.create(
            model=OLLAMA_MODEL,
            messages=messages,
            tools=openai_tools,
            temperature=0.3,
            max_tokens=1000,
        )

    async def chat_with_tools(self, user_query: str) -> str:
        tools_list = await self.get_all_tools()
        
        # Convert Tool objects → OpenAI-compatible dicts
        tools_meta = [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": t.inputSchema,
            }
            for t in tools_list
        ]
        
        tool_index = {t["name"]: t for t in tools_meta}  # now consistent
        
        messages = [
            {"role": "system", "content": "Tu es un assistant personnel. Utilise les outils disponibles pour répondre."},
            {"role": "user", "content": user_query},
        ]

        while True:
            response = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.ollama_chat(messages, tools_meta)
            )
            msg = response.choices[0].message
            messages.append({"role": "assistant", "content": msg.content, "tool_calls": msg.tool_calls})

            if not msg.tool_calls:
                return msg.content or "(pas de réponse)"

            for tc in msg.tool_calls:
                args = json.loads(tc.function.arguments or "{}")
                print(f"\n-> Tool call : {tc.function.name}({json.dumps(args, ensure_ascii=False)})")
                result = await self.call_tool(tc.function.name, args)
                result_text = result.content[0].text if result.content else "Pas de résultat"  # ← CallToolResult has .content
                print(f"<- Résultat  : {result_text[:200]}...")
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": result_text})
    
    async def close(self):
        await self.exit_stack.aclose()


# =================================================================
# EXECUTION
# =================================================================
async def main():
    # Connexion aux serveurs (utilisation de sys.executable pour plus de fiabilité)
    client = MCPOrchestrator(model=OLLAMA_MODEL)

    # Connection au serveur local (mcp_local_server.py)
    script_path = os.path.join(os.path.dirname(__file__), "..", "mcp_local_server.py")
    await client.connect_local_server(sys.executable, [script_path])
    
    # Connection au serveur distant (FastAPI + outils météo/doctolib)
    await client.connect_remote_server("http://192.168.1.12:8123/sse/")
    #await client.connect_remote_server("https://ddcm-local.myftp.org/mcp/sse/")
    print("--- Orchestrateur MCP prêt (Ollama) ---")
    print("Posez une question (ex: 'Quel temps fait-il à Paris ?' ou 'Cherche des jobs Python à Lyon')")

    while True:
        query = input("\n> ")
        if query.lower() in ["exit", "quit"]:
            break
        await client.chat_with_tools(query)


if __name__ == "__main__":
    import sys

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
