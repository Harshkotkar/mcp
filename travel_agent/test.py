
from requests import request
import requests

city="mumbai"
def get_weather(city:str)->str:
    geo_url="https://geocoding-api.open-meteo.com/v1/search"

    geo_response=requests.get(
        geo_url,
        params={
            "name":city,
            "count":1,
            "language":"en"
        },
        timeout=10,
    )

    geo_response.raise_for_status()
    geo_data=geo_response.json()

    if not geo_data.get("results"):
        return f"unable to get the data of {city}."

    location=geo_data["results"][0]
    lat=location["latitude"]
    lon=location["longitude"]
    city_name=location['name']
    country=location['country']
    return f"{city_name}, {country} is at latitude {lat} and longitude {lon}."
print(get_weather(city))


