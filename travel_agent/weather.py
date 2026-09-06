from requests import request
import requests


condition_map = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    61: "Rain showers",
    71: "Snow fall",
    95: "Thunderstorm",
}

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
        return"unable to get the data of {city}."

    location=geo_data["results"][0]
    lat=location["latitude"]
    lon=location["longitude"]
    city_name=location['name']
    country=location['country']

    weather_url="https://api.open-meteo.com/v1/forecast"
    weather_response=requests.get(
        weather_url,
        params={
            "latitude":lat,
            "longitude":lon,
            "current_weather":True,
            "temperature_unit":"celsius",
            "windspeed_unit":"kmh",
        },
        timeout=10,
    )

    weather_response.raise_for_status()
    weather_data=weather_response.json()

    current=weather_data['current_weather']
    condition = condition_map.get(current["weathercode"], "Unknown")

    return (
        f"Weather in {city_name}, {country}:\n"
        f"Temperature: {current['temperature']} °C\n"
        f"Wind Speed: {current['windspeed']} km/h"
        f"Condition : {condition}"
    )


def forecast_weather(city:str,days:int)->str:
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
        return"unable to get the data of {city}."

    location=geo_data["results"][0]
    lat=location["latitude"]
    lon=location["longitude"]
    city_name=location['name']
    country=location['country']

    weather_url="https://api.open-meteo.com/v1/forecast"
    weather_response=requests.get(
        weather_url,
        params={
            "latitude":lat,
            "longitude":lon,
            "daily":"temperature_2m_max,temperature_2m_min,weathercode",
            "forecast_days":days,
            "temperature_unit":"celsius",
            "windspeed_unit":"kmh",
            "timezone":"auto",
            
        },
        timeout=10,
    )

    weather_response.raise_for_status()
    weather_data=weather_response.json()

    daily=weather_data['daily']
    result=f"forcast for {city_name},{country} for next {days} days:\n"
    for i in range(len(daily['time'])):
        date = daily["time"][i]
        max_temp = daily["temperature_2m_max"][i]
        min_temp = daily["temperature_2m_min"][i]
        condition = condition_map.get(daily["weathercode"][i], "Unknown")

        result += (
            f"{date}: "
            f"Min {min_temp} °C, "
            f"Max {max_temp} °C, "
            f"Condition : {condition}\n"
        )

    return result









    








    