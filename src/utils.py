from datetime import date, datetime, timedelta, timezone

import hashlib

_CST = timezone(timedelta(hours=8))

_DATETIME_FMT = "%Y-%m-%d %H:%M:%S"


def live_slug(start_time: str, title: str) -> str:
    return hashlib.md5(f"{start_time}{title}".encode()).hexdigest()


def parse_datetime(s: str) -> datetime:
    return datetime.strptime(s, _DATETIME_FMT)


def format_datetime(dt: datetime) -> str:
    return dt.strftime(_DATETIME_FMT)


def week_range(day: date) -> tuple[date, date]:
    monday = day - timedelta(days=day.weekday())
    sunday = monday + timedelta(days=6)
    return monday, sunday


def today() -> date:
    return datetime.now(tz=_CST).date()
