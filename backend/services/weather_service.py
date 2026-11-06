
import httpx

WEATHER_URL = "https://api.open-meteo.com/v1/forecast"


LATITUDE = 45.79
LONGITUDE = 24.15


def get_weather_forecast():
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "hourly": [
            "temperature_2m",
            "cloud_cover",
            "shortwave_radiation"
        ],
        "forecast_days": 7,
        "timezone": "Europe/Bucharest"
    }

    with httpx.Client(timeout=15.0) as client:
        response = client.get(WEATHER_URL, params=params)
        response.raise_for_status()

    data = response.json()
    hourly = data["hourly"]

    forecast = []

    for index, timestamp in enumerate(hourly["time"]):
        forecast.append({
            "time": timestamp,
            "temperature": hourly["temperature_2m"][index],
            "cloud_cover": hourly["cloud_cover"][index],
            "solar_radiation": hourly["shortwave_radiation"][index]
        })

    return forecast
