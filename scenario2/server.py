from fastapi import FastAPI
from fastapi_mcp import FastApiMCP
app=FastAPI(title="calculator")

@app.post("/add")
def add(x:float,y:float)->float:
    """Add two numbers
    args:
        x:first number
        y:secon number
    return : float : addition of the 2 numbers """
    return x+y

@app.post("/subtract")
def subtract(x:float,y:float)->float:
    """Subtract two numbers
    args:
        x:first number
        y:secon number
    return : float : subtraction of the 2 numbers """
    return x-y
@app.post("/multiply")
def multiply(x:float,y:float)->float:
    """Multiply two numbers
    args:
        x:first number
        y:secon number
    return : float : multiplication of the 2 numbers """
    return x*y
@app.post("/divide")
def divide(x:float,y:float)->float:
    """Divide two numbers
    args:
        x:first number
        y:secon number
    return : float : division of the 2 numbers """
    return x/y


#converting to mcp
mcp=FastApiMCP(app,name="calculator mcp")
mcp.mount_http()

if __name__=="__main__":
    import uvicorn
    uvicorn.run(app,host='localhost',port=8080)