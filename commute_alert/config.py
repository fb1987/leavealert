import datetime as dt
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from commute_alert.errors import ConfigError

VALID_DAYS = {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}


@dataclass
class Config:
    version: int
    user: Dict[str, Any]
    commute: Dict[str, Any]
    route: Dict[str, Any]
    notifications: Dict[str, Any]


def load_config(path: str = "config.yml") -> Config:
    config_path = Path(path)
    if not config_path.exists():
        raise ConfigError(f"Config file not found: {config_path}")
    data = yaml.safe_load(config_path.read_text())
    if not isinstance(data, dict):
        raise ConfigError("Config must be a YAML mapping.")

    _validate_required(data, "version")
    _validate_required(data, "user")
    _validate_required(data, "commute")
    _validate_required(data, "route")
    _validate_required(data, "notifications")

    if data["version"] != 1:
        raise ConfigError("Only version: 1 is supported.")

    _validate_user(data["user"])
    _validate_commute(data["commute"])
    _validate_route(data["route"])
    _validate_notifications(data["notifications"])

    return Config(
        version=data["version"],
        user=data["user"],
        commute=data["commute"],
        route=data["route"],
        notifications=data["notifications"],
    )


def _validate_required(data: Dict[str, Any], key: str) -> None:
    if key not in data:
        raise ConfigError(f"Missing required key: {key}")


def _validate_user(user: Dict[str, Any]) -> None:
    _validate_required(user, "github_username")
    _validate_required(user, "timezone")


def _validate_commute(commute: Dict[str, Any]) -> None:
    _validate_required(commute, "arrival_time")
    _validate_required(commute, "days")
    _validate_required(commute, "buffer_minutes")
    _validate_required(commute, "lead_minutes")
    if not isinstance(commute.get("days"), list):
        raise ConfigError("commute.days must be a list.")
    invalid_days = set(commute["days"]) - VALID_DAYS
    if invalid_days:
        raise ConfigError(f"Invalid commute.days: {sorted(invalid_days)}")

    try:
        dt.datetime.strptime(commute["arrival_time"], "%H:%M")
    except ValueError as exc:
        raise ConfigError("commute.arrival_time must be HH:MM") from exc


def _validate_route(route: Dict[str, Any]) -> None:
    _validate_required(route, "mode")
    _validate_required(route, "origin")
    _validate_required(route, "destination")
    for key in ("origin", "destination"):
        location = route.get(key, {})
        if not isinstance(location, dict):
            raise ConfigError(f"route.{key} must be a mapping")
        if "address" in location:
            continue
        if {"lat", "lng"}.issubset(location.keys()):
            continue
        raise ConfigError(f"route.{key} requires address or lat/lng")


def _validate_notifications(notifications: Dict[str, Any]) -> None:
    _validate_required(notifications, "channel")
    _validate_required(notifications, "grace_minutes")
    _validate_required(notifications, "leave_grace_minutes")
    if notifications.get("channel") != "github_mention":
        raise ConfigError("notifications.channel must be github_mention")
    quiet_hours = notifications.get("quiet_hours")
    if quiet_hours and quiet_hours.get("enabled"):
        for field in ("start", "end"):
            if field not in quiet_hours:
                raise ConfigError("quiet_hours requires start and end")
            try:
                dt.datetime.strptime(quiet_hours[field], "%H:%M")
            except ValueError as exc:
                raise ConfigError("quiet_hours times must be HH:MM") from exc


def get_issue_number(config: Config, state: Optional[Dict[str, Any]]) -> Optional[int]:
    issue_number = config.notifications.get("issue_number")
    if issue_number:
        return int(issue_number)
    if state:
        return state.get("issue_number")
    return None


def get_active_days(commute: Dict[str, Any]) -> List[str]:
    return commute.get("days", [])
