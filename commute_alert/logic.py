import datetime as dt
from dataclasses import dataclass
from typing import Any, Dict, Optional

from commute_alert.clock import arrival_datetime_for_today, is_within_quiet_hours


@dataclass
class Decision:
    send: bool
    message: str
    send_type: Optional[str]
    leave_by: dt.datetime
    notify_at: dt.datetime


def should_run_today(days: list[str], now: dt.datetime) -> bool:
    weekday = now.strftime("%a").lower()[:3]
    return weekday in days


def compute_leave_by(
    now: dt.datetime,
    arrival_time: str,
    travel_duration: dt.timedelta,
    buffer_minutes: int,
    lead_minutes: int,
) -> tuple[dt.datetime, dt.datetime]:
    arrival_dt = arrival_datetime_for_today(now, arrival_time)
    leave_by = arrival_dt - travel_duration - dt.timedelta(minutes=buffer_minutes)
    notify_at = leave_by - dt.timedelta(minutes=lead_minutes)
    return leave_by, notify_at


def decide_send(
    now: dt.datetime,
    config: Dict[str, Any],
    travel_duration: dt.timedelta,
    state: Dict[str, Any],
) -> Decision:
    commute = config["commute"]
    notifications = config["notifications"]

    leave_by, notify_at = compute_leave_by(
        now,
        commute["arrival_time"],
        travel_duration,
        int(commute["buffer_minutes"]),
        int(commute["lead_minutes"]),
    )

    grace_minutes = int(notifications["grace_minutes"])
    leave_grace_minutes = int(notifications["leave_grace_minutes"])
    primary_window_end = notify_at + dt.timedelta(minutes=grace_minutes)
    leave_window_end = leave_by + dt.timedelta(minutes=leave_grace_minutes)

    last_sent_date = state.get("last_sent_date")
    last_sent_type = state.get("last_sent_type")
    today_str = now.date().isoformat()
    already_sent_today = last_sent_date == today_str

    quiet_hours = notifications.get("quiet_hours", {})
    if quiet_hours.get("enabled") and is_within_quiet_hours(
        now, quiet_hours["start"], quiet_hours["end"]
    ):
        return Decision(False, "Quiet hours enabled; skipping.", None, leave_by, notify_at)

    if notify_at <= now < primary_window_end and not already_sent_today:
        message = "Primary window trigger"
        return Decision(True, message, "primary", leave_by, notify_at)

    if leave_by <= now < leave_window_end and not already_sent_today:
        message = "Leave-by window trigger"
        return Decision(True, message, "leave_now", leave_by, notify_at)

    return Decision(False, "No notification window matched.", None, leave_by, notify_at)


def _estimate_travel_duration(
    config: Dict[str, Any],
    state: Dict[str, Any],
) -> dt.timedelta | None:
    last_eta_seconds = state.get("last_eta_seconds")
    if last_eta_seconds:
        return dt.timedelta(seconds=int(last_eta_seconds))
    estimated_minutes = config["commute"].get("estimated_duration_minutes")
    if estimated_minutes:
        return dt.timedelta(minutes=int(estimated_minutes))
    return None


def should_fetch_eta(
    now: dt.datetime,
    config: Dict[str, Any],
    state: Dict[str, Any],
) -> tuple[bool, str]:
    commute = config["commute"]
    notifications = config["notifications"]

    today_str = now.date().isoformat()
    if state.get("last_sent_date") == today_str:
        return False, "Alert already sent today; skipping ETA fetch."

    quiet_hours = notifications.get("quiet_hours", {})
    if quiet_hours.get("enabled") and is_within_quiet_hours(
        now, quiet_hours["start"], quiet_hours["end"]
    ):
        return False, "Quiet hours enabled; skipping ETA fetch."

    estimate = _estimate_travel_duration(config, state)
    if not estimate:
        return True, "No ETA estimate available; fetching ETA."

    leave_by, notify_at = compute_leave_by(
        now,
        commute["arrival_time"],
        estimate,
        int(commute["buffer_minutes"]),
        int(commute["lead_minutes"]),
    )
    grace_minutes = int(notifications["grace_minutes"])
    leave_grace_minutes = int(notifications["leave_grace_minutes"])
    primary_window_end = notify_at + dt.timedelta(minutes=grace_minutes)
    leave_window_end = leave_by + dt.timedelta(minutes=leave_grace_minutes)

    if now < notify_at:
        return False, "Before notification window; skipping ETA fetch."
    if now > leave_window_end:
        return False, "After notification window; skipping ETA fetch."
    if notify_at <= now < primary_window_end or leave_by <= now <= leave_window_end:
        return True, "Within notification window; fetching ETA."

    return False, "Outside notification window; skipping ETA fetch."
