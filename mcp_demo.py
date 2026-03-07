"""
Demo MCP multi-serveur — météo actuelle (wttr.in) + prévisions (open-meteo)
LLM : Ollama local via interface OpenAI-compatible — 100% gratuit
"""

import asyncio
import json
import os
import sys
from contextlib import AsyncExitStack
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openai import OpenAI

OLLAMA_MODEL = "qwen3.5:4b"
# Interface OpenAI-compatible d'Ollama
ollama_client = OpenAI(
    api_key="ollama",
    base_url="http://localhost:11434/v1",
)


class MCPMultiClient:
    def __init__(self):
        self.exit_stack = AsyncExitStack()
        self.sessions: dict[str, ClientSession] = {}

    async def connect_server(self, name: str, cmd_or_path: str | list[str]):
        """
        Connecte un serveur MCP.
        Accepte soit un chemin (str), soit une commande complète (list).
        """
        if isinstance(cmd_or_path, list):
            # Cas ["python", "mcp_tools.py", "weather"]
            command = cmd_or_path[0]
            args = cmd_or_path[1:]
        else:
            # Cas "server_weather.py" (votre ancien fonctionnement)
            is_python = cmd_or_path.endswith(".py")
            command = sys.executable if is_python else "node"
            args = [str(Path(cmd_or_path).resolve())]

        env = {**os.environ, "PYTHONIOENCODING": "utf-8"}

        # Configuration des paramètres du serveur
        server_params = StdioServerParameters(command=command, args=args, env=env)

        # Connexion via le transport stdio
        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        stdio, write = stdio_transport
        session = await self.exit_stack.enter_async_context(ClientSession(stdio, write))

        await session.initialize()
        self.sessions[name] = session

        # Petit feedback pour confirmer que les outils sont chargés
        resp = await session.list_tools()
        print(f"✅ Serveur [{name}] connecté avec succès ({len(resp.tools)} outils).")

    """
    async def connect_server(self, name: str, server_script_path: str):
        is_python = server_script_path.endswith(".py")
        is_js = server_script_path.endswith(".js")
        if not (is_python or is_js):
            raise ValueError("Server script must be a .py or .js file")

        command = sys.executable if is_python else "node"
        abs_path = str(Path(server_script_path).resolve())
        env = {**os.environ, "PYTHONIOENCODING": "utf-8"}

        server_params = StdioServerParameters(command=command, args=[abs_path], env=env)
        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        stdio, write = stdio_transport
        session = await self.exit_stack.enter_async_context(ClientSession(stdio, write))
        await session.initialize()
        self.sessions[name] = session

        resp = await session.list_tools()
        print(f"[{name}] tools: {[t.name for t in resp.tools]}")
    """

    async def list_all_tools(self) -> list[dict]:
        aggregated = []
        for server_name, session in self.sessions.items():
            resp = await session.list_tools()
            for tool in resp.tools:
                aggregated.append(
                    {
                        "name": f"{server_name}__{tool.name}",
                        "description": tool.description,
                        "input_schema": tool.inputSchema,
                        "server": server_name,
                        "tool_name": tool.name,
                    }
                )
        return aggregated

    async def call_tool(self, server: str, tool_name: str, args: dict) -> str:
        session = self.sessions[server]
        result = await session.call_tool(tool_name, args)
        parts = [block.text for block in result.content if hasattr(block, "text")]
        return "\n".join(parts)

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
        tools_meta = await self.list_all_tools()
        tool_index = {t["name"]: t for t in tools_meta}
        messages = [
            {"role": "system", "content": "Tu es un assistant météo. Utilise les outils disponibles pour répondre."},
            {"role": "user", "content": user_query},
        ]

        while True:
            # ollama_chat est synchrone — on l'exécute dans un thread pour ne pas bloquer asyncio
            response = await asyncio.get_event_loop().run_in_executor(None, lambda: self.ollama_chat(messages, tools_meta))

            msg = response.choices[0].message
            # Ajoute la réponse assistant à l'historique
            messages.append({"role": "assistant", "content": msg.content, "tool_calls": msg.tool_calls})

            # Pas de tool calls → réponse finale
            if not msg.tool_calls:
                return msg.content or "(pas de réponse)"

            # Exécute chaque tool call
            for tc in msg.tool_calls:
                full_name = tc.function.name
                args = json.loads(tc.function.arguments or "{}")
                meta = tool_index.get(full_name)

                if not meta:
                    print(f"[WARN] Tool inconnu: {full_name}")
                    continue

                print(f"\n-> Tool call : {full_name}({json.dumps(args, ensure_ascii=False)})")
                result_text = await self.call_tool(meta["server"], meta["tool_name"], args)
                print(f"<- Résultat  : {result_text[:200]}{'...' if len(result_text) > 200 else ''}")

                # Format OpenAI : tool_call_id requis
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result_text,
                    }
                )

    async def close(self):
        await self.exit_stack.aclose()


async def main():
    print(f"Modèle : {OLLAMA_MODEL}")

    # --- Gestion de l'argument de ligne de commande ---
    # Si sys.argv a plus d'un élément, on prend le texte après le nom du script
    if len(sys.argv) > 1:
        user_query = sys.argv[1]
    else:
        # Valeur par défaut si aucun argument n'est fourni
        user_query = "Donne-moi les previsions sur 3 jours pour dans la ville du chateau du roi soleil ?"

    client = MCPMultiClient()
    try:
        # Connexion aux serveurs (utilisation de sys.executable pour plus de fiabilité)
        await client.connect_server("weather-server", [sys.executable, "mcp_tools.py", "weather"])
        await client.connect_server("forecast-server", [sys.executable, "mcp_tools.py", "forecast"])
        await client.connect_server("searx-server", [sys.executable, "mcp_tools.py", "searx"])
        await client.connect_server("linkedin-server", [sys.executable, "mcp_tools.py", "linkedin"])

        print(f"\n{'=' * 60}")
        print(f"Question : {user_query}")
        print(f"{'=' * 60}")

        # L'agent va maintenant devoir utiliser SearX pour trouver "Versailles"
        # avant d'appeler le forecast-server.
        answer = await client.chat_with_tools(user_query)

        print(f"\nReponse :\n{answer}")

    except Exception as e:
        print(f"\n[ERREUR] Une erreur est survenue : {e}")
    finally:
        await client.close()


if __name__ == "__main__":
    # On s'assure que l'encodage est correct pour Windows (évite les erreurs de caractères spéciaux)
    if sys.platform == "win32":
        import os

        os.environ["PYTHONIOENCODING"] = "utf-8"

    asyncio.run(main())
