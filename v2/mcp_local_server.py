import asyncio

import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server

# Importation des fonctions de logique métier depuis votre dossier tools
# Note : Assurez-vous d'avoir un fichier __init__.py vide dans le dossier tools/
from mcp_tools import call_forecast_tool, call_searx_tool, list_forecast_tools, list_searx_tools

# Si vous voulez aussi des outils locaux spécifiques :
# from tools.local_utils import ma_fonction_perso

# 1. Initialisation du Serveur Unique
app = Server("mcp-local-hub")


# 2. Définition de la liste des outils
@app.list_tools()
async def list_tools() -> list[types.Tool]:
    """
    On concatène les listes d'outils provenant des différents modules.
    """
    tools = []

    # On récupère les outils de mcp_tools.py (Searx et Forecast)
    tools.extend(await list_searx_tools())
    tools.extend(await list_forecast_tools())

    # Vous pouvez ajouter manuellement d'autres outils ici si besoin
    return tools


# 3. Gestionnaire d'appels d'outils (Le Dispatcher)
@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    """
    On redirige l'appel vers la bonne fonction selon le nom de l'outil.
    """
    try:
        # Routage vers SearxNG
        if name == "web_search":
            return await call_searx_tool(name, arguments)

        # Routage vers Open-Meteo (Prévisions)
        elif name == "get_forecast":
            return await call_forecast_tool(name, arguments)

        # Ajoutez vos futurs outils locaux ici
        # elif name == "mon_outil_local":
        #     return await ma_fonction_locale(arguments)

        else:
            raise ValueError(f"Outil inconnu sur le serveur local : {name}")

    except Exception as e:
        return [types.TextContent(type="text", text=f"Erreur local_server: {str(e)}")]


# 4. Point d'entrée pour l'exécution en STDIO
async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
