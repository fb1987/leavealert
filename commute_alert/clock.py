import datetime as dt
from zoneinfo import ZoneInfo


def get_now(timezone: str) -> dt.datetime:
    return dt.datetime.now(tz=ZoneInfo(timezone))


def local_date(now: dt.datetime) -> dt.date:
    return now.date()


def parse_local_time(time_str: str) -> dt.time:
    return dt.datetime.strptime(time_str, "%H:%M").time()


def arrival_datetime_for_today(now: dt.datetime, arrival_time: str) -> dt.datetime:
    arrival = parse_local_time(arrival_time)
    return dt.datetime.combine(now.date(), arrival, tzinfo=now.tzinfo)


def is_within_quiet_hours(now: dt.datetime, start: str, end: str) -> bool:
    start_time = parse_local_time(start)
    end_time = parse_local_time(end)
    if start_time == end_time:
        return False

    now_time = now.timetz()
    if start_time < end_time:
        return start_time <= now_time < end_time
    return now_time >= start_time or now_time < end_time
