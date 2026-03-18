from datetime import timedelta
from zoneinfo import ZoneInfo

from icalendar import Alarm, Calendar, Event, vDatetime, vDuration, vText

from bilibili.types import Live
from utils import format_datetime, live_slug

_TZ = ZoneInfo("Asia/Shanghai")


def _uid(live: Live) -> str:
    return live_slug(format_datetime(live.start_time), live.title) + "@asoul-calendar"


def _live_to_event(live: Live, reminder_minutes: int, duration_minutes: int) -> Event:
    start = live.start_time.replace(tzinfo=_TZ)
    end = start + timedelta(minutes=duration_minutes)

    event = Event()
    event.add("uid", vText(_uid(live)))
    event.add("summary", vText(f"【{live.host}】{live.title}"))
    event.add("dtstart", vDatetime(start))
    event.add("dtend", vDatetime(end))
    event.add("description", vText(
        f"成员：{'、'.join(live.members)}\n类型：{live.tag or live.kind.value}"
    ))

    alarm = Alarm()
    alarm.add("action", "DISPLAY")
    alarm.add("description", vText("即将开播"))
    alarm.add("trigger", vDuration(-timedelta(minutes=reminder_minutes)))
    event.add_component(alarm)

    return event


def generate_ics(
    lives: list[Live],
    reminder_minutes: int = 0,
    duration_minutes: int = 120,
) -> str:
    cal = Calendar()
    cal.add("prodid", "-//A-SOUL Calendar//ZH")
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("x-wr-calname", vText("A-SOUL"))
    cal.add("x-wr-relcalid", vText("a-soul-calendar-main"))
    cal.add("x-wr-caldesc", vText("A-SOUL 成员直播日程"))

    for live in lives:
        cal.add_component(_live_to_event(live, reminder_minutes, duration_minutes))

    return cal.to_ical().decode()
