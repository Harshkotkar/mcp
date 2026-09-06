from fastmcp import FastMCP
from fastapi import FastAPI
mcp = FastMCP(
    name="Calculator MCP",
    instructions="A simple calculator MCP server."
)
app = FastAPI(
    title="Calculator MCP Server"
)

@mcp.tool()
def add(x: float, y: float) -> float:
    """Add two numbers."""
    return x + y


@mcp.tool()
def subtract(x: float, y: float) -> float:
    """Subtract the second number from the first number."""
    return x - y


@mcp.tool()
def multiply(x: float, y: float) -> float:
    """Multiply two numbers."""
    return x * y


@mcp.tool()
def divide(x: float, y: float) -> float:
    """Divide the first number by the second number."""
    return x / y

# mcp_app=mcp.http_app(
#     path="/mcp"
# ) #asks FastMCP:"Give me an HTTP ASGI application for this MCP server." basically it returns an ASGI( asynchronous server gateway interface)app
app = mcp.http_app(
    transport="streamable-http",
    stateless_http=True,
)
#app.mount("/mcp", mcp_app) # mount that application inside the fastapi

#uvicorn server2:app --reload