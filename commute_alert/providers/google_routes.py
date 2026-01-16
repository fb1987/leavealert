import datetime as dt
import json
from typing import Any, Dict

import requests

from commute_alert.errors import ProviderError

ROUTES_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"


def _format_location(location: Dict[str, Any]) -> Dict[str, Any]:
    if "address" in location:
        return {"address": location["address"]}
    return {
        "location": {
            "latLng": {
                "latitude": float(location["lat"]),
                "longitude": float(location["lng"]),
            }
        }
    }


def compute_route_duration(route: Dict[str, Any], api_key: str) -> dt.timedelta:
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "routes.duration,routes.travelAdvisory",
    }
    payload = {
        "origin": _format_location(route["origin"]),
        "destination": _format_location(route["destination"]),
        "travelMode": route.get("mode", "DRIVE"),
        "routingPreference": "TRAFFIC_AWARE",
        "departureTime": dt.datetime.utcnow().isoformat() + "Z",
    }
    if route.get("waypoints"):
        payload["intermediates"] = [
            _format_location(waypoint) for waypoint in route["waypoints"]
        ]

    response = requests.post(ROUTES_URL, headers=headers, data=json.dumps(payload), timeout=20)
    if response.status_code != 200:
        raise ProviderError(
            f"Routes API error {response.status_code}: {response.text}"
        )
    data = response.json()
    try:
        duration_str = data["routes"][0]["duration"]
    except (KeyError, IndexError) as exc:
        raise ProviderError("Routes API response missing duration") from exc

    seconds = _parse_duration_seconds(duration_str)
    return dt.timedelta(seconds=seconds)


def _parse_duration_seconds(duration: str) -> int:
    if duration.endswith("s"):
        return int(duration[:-1])
    raise ProviderError(f"Unknown duration format: {duration}")
