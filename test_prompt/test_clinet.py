import asyncio

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


MCP_URL = "http://127.0.0.1:8000/mcp"


async def main():

    async with streamable_http_client(MCP_URL) as (read, write, _):

        async with ClientSession(read, write) as session:

            await session.initialize()

            print("\nConnected to MCP server!")

            # Discover tools
            tools = await session.list_tools()

            print("\nTools:")

            for tool in tools.tools:
                print(f"- {tool.name}")

            # Discover prompts
            prompts = await session.list_prompts()

            print("\nPrompts:")

            for prompt in prompts.prompts:
                print(f"- {prompt.name}")


if __name__ == "__main__":
    asyncio.run(main())