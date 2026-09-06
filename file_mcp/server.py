from fastmcp import FastMCP

mcp=FastMCP("server")#this line basicaly creates a new mcp server with the name calculator_mcp

@mcp.tool(name="add",
    description="Add two numbers",
    tags=["math", "addition"])
def add(x:float,y:float)->float:
    """Add two numbers
    args:
        x:first number
        y:secon number
    return : float : addition of the 2 numbers """
    return x+y

@mcp.tool(name="subtract",
    description="Subtract two numbers",
    tags=["math", "subtraction"])       #@mcp.tool is a decorator that registers the function as a tool with out this the function will not be available to the mcp server it will be just a normal fucntion of py.
def subtract(x:float,y:float)->float:
    """Subtract two numbers
    args:
        x:first number
        y:secon number
    return : float : subtraction of the 2 numbers """
    return x-y

@mcp.tool(name='multiply',
    description="multiply two numbers",
    tags=['math', 'multiplication', 'arithmetic'])
def multiply(x:float,y:float)->float:
    """multiply two numbers
    args:
        x:first number
        y:second number
    return : float : multiplication of the 2 numbers """
    return x*y
@mcp.tool(name='divide',
    description="divide two numbers",
    tags=['math', 'division', 'arithmetic'])
def division(x:float,y:float)->float:
    """divide two numbers
    args:
        x:first number
        y:second number
    return : float : division of the 2 numbers """
    return x/y
    
# Add a dynamic greeting resource
@mcp.resource("greeting://{name}")
def get_greeting(name: str) -> str:
    """Get a personalized greeting"""
    return f"Hello, {name}!"

if __name__=="__main__": 
    mcp.run()
"""
basicaly the if __name__=="__main__": is used to check if the script is being run directly or being imported as a module in another script.
if the script is being run directly then the code inside the if block will be executed.
if the script is being imported as a module in another script then the code inside the if block will not be executed.
in simple words it is used to check if the script is being run directly or being imported as a module in another script.
--------------------------
and giving the doc string inside the ucntion at the start is important because it is 
used by the mcp server to understand the function and its parameters is basically tells the mcp what is function about what it takes and what it returns
"""

