from __future__ import annotations

from typing import Any, Dict, Tuple

import requests

from commute_alert.errors import ProviderError

GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
WEATHER_URL = "https://weather.googleapis.com/v1/currentConditions:lookup"


def get_current_conditions(origin: Dict[str, Any], api_key: str) -> Dict[str, Any]:
    lat, lng = _resolve_lat_lng(origin, api_key)
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
    }
    params = {
        "location.latitude": lat,
        "location.longitude": lng,
    }
    response = requests.get(WEATHER_URL, headers=headers, params=params, timeout=20)
    if response.status_code != 200:
        raise ProviderError(
            f"Weather API error {response.status_code}: {response.text}"
        )
    return response.json()


def format_weather_summary(payload: Dict[str, Any]) -> str:
    conditions = payload.get("currentConditions", payload)
    description = _extract_weather_description(conditions)
    temperature = _format_temperature(conditions.get("temperature"))
    feels_like = _format_temperature(conditions.get("feelsLikeTemperature"))
    humidity = _format_humidity(conditions.get("relativeHumidity") or conditions.get("humidity"))
    wind = _format_wind(conditions.get("wind"))

    parts = [part for part in (description, temperature) if part]
    if feels_like:
        parts.append(f"feels like {feels_like}")
    if humidity:
        parts.append(humidity)
    if wind:
        parts.append(wind)
    summary = ", ".join(parts) if parts else "conditions unavailable"
    return f"Weather: {summary}."


def _resolve_lat_lng(origin: Dict[str, Any], api_key: str) -> Tuple[float, float]:
    if "address" in origin:
        return _geocode_address(origin["address"], api_key)
    if {"lat", "lng"}.issubset(origin.keys()):
        return float(origin["lat"]), float(origin["lng"])
    raise ProviderError("Origin location missing address or lat/lng")


def _geocode_address(address: str, api_key: str) -> Tuple[float, float]:
    params = {"address": address, "key": api_key}
    response = requests.get(GEOCODE_URL, params=params, timeout=20)
    if response.status_code != 200:
        raise ProviderError(
            f"Geocoding API error {response.status_code}: {response.text}"
        )
    data = response.json()
    status = data.get("status")
    if status != "OK":
        raise ProviderError(f"Geocoding API error: {status}")
    try:
        location = data["results"][0]["geometry"]["location"]
        return float(location["lat"]), float(location["lng"])
    except (KeyError, IndexError, TypeError) as exc:
        raise ProviderError("Geocoding API response missing location") from exc


def _extract_weather_description(conditions: Dict[str, Any]) -> str | None:
    weather_condition = conditions.get("weatherCondition")
    if isinstance(weather_condition, dict):
        for key in ("description", "type", "text"):
            if weather_condition.get(key):
                return weather_condition[key].replace("_", " ").title()
    if conditions.get("condition"):
        return str(conditions["condition"])
    return None


def _format_temperature(temperature: Any) -> str | None:
    if temperature is None:
        return None
    if isinstance(temperature, dict):
        degrees = temperature.get("degrees") or temperature.get("value")
        unit = temperature.get("unit")
    else:
        degrees = temperature
        unit = None
    if degrees is None:
        return None
    try:
        degrees_value = float(degrees)
    except (TypeError, ValueError):
        return None
    unit_suffix = _format_temperature_unit(unit)
    return f"{degrees_value:.0f}{unit_suffix}"


def _format_temperature_unit(unit: str | None) -> str:
    if not unit:
        return "°"
    unit_upper = unit.upper()
    if "FAHRENHEIT" in unit_upper:
        return "°F"
    if "CELSIUS" in unit_upper:
        return "°C"
    return f"°{unit_upper[:1]}"


def _format_humidity(humidity: Any) -> str | None:
    if humidity is None:
        return None
    try:
        humidity_value = float(humidity)
    except (TypeError, ValueError):
        return None
    if 0 <= humidity_value <= 1:
        humidity_value *= 100
    return f"Humidity {humidity_value:.0f}%"


def _format_wind(wind: Any) -> str | None:
    if not isinstance(wind, dict):
        return None
    speed = wind.get("speed")
    direction = wind.get("direction", {})
    speed_value = None
    speed_unit = None
    if isinstance(speed, dict):
        speed_value = speed.get("value")
        speed_unit = speed.get("unit")
    elif speed is not None:
        speed_value = speed
    if speed_value is None:
        return None
    try:
        speed_value = float(speed_value)
    except (TypeError, ValueError):
        return None
    unit_label = _format_wind_unit(speed_unit)
    direction_label = direction.get("cardinal") or direction.get("degrees")
    if direction_label is not None:
        return f"Wind {speed_value:.0f} {unit_label} {direction_label}"
    return f"Wind {speed_value:.0f} {unit_label}"


def _format_wind_unit(unit: str | None) -> str:
    if not unit:
        return "mph"
    unit_upper = unit.upper()
    if "KILOMETERS_PER_HOUR" in unit_upper or unit_upper == "KPH":
        return "kph"
    if "METERS_PER_SECOND" in unit_upper or unit_upper == "MPS":
        return "m/s"
    if "MILES_PER_HOUR" in unit_upper or unit_upper == "MPH":
        return "mph"
    return unit_upper.lower()
