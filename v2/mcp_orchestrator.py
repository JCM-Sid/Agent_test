import asyncio
import json
import os

import httpx
from dotenv import load_dotenv
from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server
from openai import OpenAI

from doctolib import call_doctolib_tool, list_doctolib_tools  # Importation de ta logique
from mcp_tools import call_forecast_tool, call_searx_tool, list_forecast_tools, list_searx_tools
from meteo import list_weather_tools





## CONFIGURATION LLM 
OLLAMA_MODEL = "minimax-m2.7:cloud"  # "qwen3.5:4b"
# Interface OpenAI-compatible d'Ollama
ollama_client = OpenAI(
    api_key="ollama",
    base_url="http://localhost:11434/v1",
)

# --- CONFIGURATION COMMUNE ---
TIMEOUT = 15.0
HEADERS = {"User-Agent": "Mozilla/5.0 (MCP Agent)"}


# =================================================================
# ORCHESTRATEUR MCP (Ollama)
# =================================================================


class MCPOrchestrator:
    def __init__(self, model="minimax-m2.7:cloud"):  # Note: qwen3.5 n'existe pas encore, restez sur 2.5
        self.model = model
        # Mapping direct pour simplifier l'exécution
        self.tools_map = {
            "get_forecast": call_forecast_tool,
            "web_search": call_searx_tool,
        }

    async def get_tools_definitions(self):
        """Récupère les définitions et les formate proprement pour Ollama/OpenAI"""
        forecast = await list_forecast_tools()
        searx    = await list_searx_tools()
        doctolib = await list_doctolib_tools()
        weather = await list_weather_tools()
        

        all_tools = weather + forecast + searx + doctolib

        # On retourne le format standard attendu par l'API Chat Completions
        return [{"type": "function", "function": {"name": t.name, "description": t.description, "parameters": t.inputSchema}} for t in all_tools]

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
            response = await asyncio.get_event_loop().run_in_executor(None, lambda: self.ollama_chat(messages, tools_meta))

            msg = response.choices[0].message

            # Gestion du cas où msg.tool_calls est None
            tool_calls = getattr(msg, "tool_calls", None)

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

                remote_tools = ["doctolib_search", "get_current_weather"]  # Liste des outils à appeler via HTTP
                if func_name in remote_tools:
                    result_text = await self.call_remote_tool(func_name, args)
                elif func_name in self.tools_map:  # Liste des outils definis localement au script
                    result_content = await self.tools_map[func_name](func_name, args)
                    result_text = result_content[0].text
                else:
                    result_text = "Erreur: Outil non trouvé."

                # Retour du résultat au LLM
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "name": func_name,
                        "content": result_text,
                    }
                )

    # pour les outils distants, on fait un appel HTTP classique
    # doctolib, current_weather
    async def call_remote_tool(self, func_name: str, args: dict) -> str:
        """Appelle un outil via HTTP sur mcp_api"""

        remote_tools = {
            "doctolib_search": {
                "url": "https://ddcm-local.myftp.org/mcp/api/doctolib",
                "mapping": {
                    "spec": lambda a: a.get("spec", "").lower().replace(" ", "-").encode("ascii", "ignore").decode(),
                    "location": lambda a: a.get("location", "").replace(" ", "+").lower().encode("ascii", "ignore").decode(),
                    "limit": lambda a: a.get("limit", 10),
                },
            },
            "get_current_weather": {
                "url": "https://ddcm-local.myftp.org/mcp/api/weather",
                "mapping": {
                    "city": lambda a: a.get("city", "").lower().replace(" ", "+").encode("ascii", "ignore").decode(),
                },
            },
        }

        if func_name not in remote_tools:
            return "Erreur: Outil remote non trouvé."

        tool_config = remote_tools[func_name]
        params = {k: v(args) for k, v in tool_config["mapping"].items()}

        async with httpx.AsyncClient(timeout=90) as client:
            resp = await client.get(tool_config["url"], params=params)
            resp.raise_for_status()
            return resp.json().get("result", "")



async def main():
    orchestrator = MCPOrchestrator(model=OLLAMA_MODEL)
    print("--- Orchestrateur MCP prêt (Ollama) ---")
    print("Posez une question (ex: 'Quel temps fait-il à Paris ?' ou 'Cherche des jobs Python à Lyon')")

    while True:
        query = input("\n> ")
        if query.lower() in ["exit", "quit"]:
            break
        await orchestrator.chat_with_tools(query)



if __name__ == "__main__":
    import sys

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
