from dataclasses import dataclass
from datetime import date
from itertools import chain, takewhile
from typing import Any, Callable, Iterator, TypeVar

from .api import get_space_dynamics, reservation
from app.types import Reserve
from .types import ApiConfig
from utils import from_timestamp, week_range
from app.members import Member


@dataclass(frozen=True)
class DynamicDraw:
    text: str
    pics: list[str]


def get_dynamic_draw_this_week(api_config: ApiConfig, uid: int, day: date) -> list[DynamicDraw]:
    return [
        _extract_dynamic_draw(item)
        for item in _fetch_dynamics_this_week(api_config, uid, day)
        if item['type'] == 'DYNAMIC_TYPE_DRAW'
    ]


def get_all_reserve(api_config: ApiConfig, member: Member) -> list[Reserve]:
    items = reservation(api_config, member.uid).get('data') or []
    return [
        Reserve(title=item['name'], start_time=from_timestamp(item['live_plan_start_time']), member=member.code)
        for item in items
    ]


def _fetch_dynamics_this_week(api_config: ApiConfig, uid: int, day: date) -> list[dict[str, Any]]:
    start, end = week_range(day)
    return _fetch_dynamics_in_range(api_config, uid, start, end)


def _extract_dynamic_draw(item: dict[str, Any]) -> DynamicDraw:
    opus = item['modules']['module_dynamic']['major']['opus']
    pics = [p['url'] for p in opus.get('pics') or []]
    return DynamicDraw(text=opus['summary']['text'], pics=pics)


def _fetch_dynamics_in_range(api_config: ApiConfig, uid: int, start: date, end: date) -> list[dict[str, Any]]:
    pages: Iterator[list[dict]] = _unfoldr(_dynamics_page_step(api_config, uid), "")
    items: Iterator[dict] = chain.from_iterable(pages)
    return [
        item for item in takewhile(lambda item: _pub_date(item) >= start, items)
        if _pub_date(item) <= end
    ]


_A = TypeVar('_A')
_B = TypeVar('_B')


def _unfoldr(f: Callable[[_B], tuple[_A, _B] | None], seed: _B) -> Iterator[_A]:
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
    return from_timestamp(int(item['modules']['module_author']['pub_ts'])).date()
