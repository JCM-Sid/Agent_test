import asyncio
import json
import os

from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

load_dotenv()
nextcloud_dir = os.getenv("NEXTCLOUD")
api_key_path = os.path.join(nextcloud_dir, "ConfigPerso", "api_key.json")
conf_file = json.load(open(api_key_path))
N8N_API_KEY = conf_file["n8n_api_key"]

MCP_URL = "http://localhost:5678/mcp-server/http"

async def main():
    headers = {"authorization": f"Bearer {N8N_API_KEY}"}
    # headers = {"X-N8N-API-KEY": N8N_API_KEY}
    async with streamablehttp_client(MCP_URL, headers=headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            for tool in tools.tools:
                print(tool.name)


asyncio.run(main())
