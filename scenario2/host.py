import asyncio
from fastmcp import Client

async def main():
    client=Client("http://127.0.0.1:8000/mcp")

    async with client:
        print("connected to calculator MCP server")
        await client.ping()

        print("ping successful")

        tools=await client.list_tools()
        print("list tools")

        for tool in tools:
            print(tool.name,tool.description)


        result=await client.call_tool(
            tool_n,
            arguments={"x":x,"y":y}
        )
        
        print(result.content)

if __name__=="__main__":
    tool_n=input("Enter tool name: ")
    x=int(input("Enter x: "))
    y=int(input("Enter y: "))
    asyncio.run(main())