from dataclasses import dataclass
from datetime import date, datetime, timezone, timedelta

_CST = timezone(timedelta(hours=8))
from itertools import chain, takewhile
from typing import Any, Callable, Iterator, TypeVar

from .api import get_space_dynamics, reservation
from .types import ApiConfig, Reserve
from utils import week_range
from members import Member


@dataclass(frozen=True)
class DynamicDraw:
    text: str
    pics: list[str]


def extract_dynamic_draw(item: dict[str, Any]) -> DynamicDraw:
    opus = item['modules']['module_dynamic']['major']['opus']
    pics = [p['url'] for p in opus.get('pics') or []]
    return DynamicDraw(text=opus['summary']['text'], pics=pics)


_A = TypeVar('_A')
_B = TypeVar('_B')


def unfoldr(f: Callable[[_B], tuple[_A, _B] | None], seed: _B) -> Iterator[_A]:
    state = seed
    while (result := f(state)) is not None:
        value, state = result
        yield value


def _dynamics_page_step(api_config: ApiConfig, uid: int) -> Callable[[str], tuple[list[dict], str] | None]:
    def step(offset: str) -> tuple[list[dict], str] | None:
        rsp = get_space_dynamics(api_config, uid, offset)
        items = rsp.get("data", {}).get("items", [])
        return (items, rsp["data"]["offset"]) if items else None

    return step


def _pub_date(item: dict[str, Any]) -> date:
    return datetime.fromtimestamp(int(item['modules']['module_author']['pub_ts']), tz=_CST).date()


def fetch_dynamics_in_range(api_config: ApiConfig, uid: int, start: date, end: date) -> list[dict[str, Any]]:
    pages: Iterator[list[dict]] = unfoldr(_dynamics_page_step(api_config, uid), "")
    items: Iterator[dict] = chain.from_iterable(pages)
    return [
        item for item in takewhile(lambda item: _pub_date(item) >= start, items)
        if _pub_date(item) <= end
    ]


def fetch_dynamics_this_week(api_config: ApiConfig, uid: int, day: date) -> list[dict[str, Any]]:
    start, end = week_range(day)
    return fetch_dynamics_in_range(api_config, uid, start, end)


def get_dynamic_draw_this_week(api_config: ApiConfig, uid: int, day: date) -> list[DynamicDraw]:
    return [
        extract_dynamic_draw(item)
        for item in fetch_dynamics_this_week(api_config, uid, day)
        if item['type'] == 'DYNAMIC_TYPE_DRAW'
    ]

def get_reserve_this_week(api_config: ApiConfig, member: Member, day: date) -> list[Reserve]:
    week_start, week_end = week_range(day)
    items = reservation(api_config, member.uid).get('data') or []
    return [
        Reserve(title=item['name'], start_time=start_time, member=member.code)
        for item in items
        if week_start <= (start_time := datetime.fromtimestamp(item['live_plan_start_time'], tz=_CST).replace(tzinfo=None)).date() <= week_end
    ]