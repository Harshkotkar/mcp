from fastmcp import FastMCP
from fastapi import FastAPI

from weather import get_weather,forecast_weather
mcp = FastMCP("Weather MCP")
app=FastAPI(title="weather app")

@mcp.tool()
def get_current_weather(city: str) -> str:
    """Get the current weather for a city."""
    return get_weather(city) 

@mcp.tool()
def get_forcat_data(city:str,days:int)->str:
    "forcast the weather data"
    return forecast_weather(city,days)

@mcp.prompt()
def weather_details(city:str)->str:
    """weather report and details"""
    return f"""
     Analyze the weather in {city}.

    Determine:
    - Rain risk
    - Temperature
    - Best days for outdoor activities
    - Weather risks
    - Clothing recommendations

    Return a concise report for day to day life.
    Rules:
    -dont use the asumptions.
    -be explicit and provide details.
    -use provided data only.
    -dont create your own data and prediction.
    -if you dont have the data contact the user.
    -always use the tools to get the data.
    follow the rules.
    """

app=mcp.http_app(
    transport="http",

)
# if __name__ == "__main__":
#     mcp.run()

