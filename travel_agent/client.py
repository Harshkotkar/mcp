import asyncio

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


async def main(tool_name: str, city: str):

    async with streamable_http_client(
        "http://127.0.0.1:8000/mcp"
    ) as (read_stream, write_stream, _):

        async with ClientSession(
            read_stream,
            write_stream
        ) as session:

            await session.initialize()

            print("Connected to Weather MCP")

            # List available tools
            response = await session.list_tools()

            print("\nAvailable tools:")

            for tool in response.tools:
                print(f"- {tool.name}: {tool.description}")

            # Call the selected tool
            result = await session.call_tool(
                tool_name,
                {
                    "city": city
                }
            )

            print("\nResult:")
            #print(result)
            r=result.content[0]
            print(r.text)


if __name__ == "__main__":

    tool_name = input("Enter tool name: ")
    city = input("Enter city name: ")

    asyncio.run(main(tool_name, city))