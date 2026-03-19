from datetime import date

from bilibili.dynamics import get_dynamic_draw_this_week, get_reserve_this_week
from bilibili.types import ApiConfig, ClaudeConfig, Live, LiveKind, Reserve
from ai import find_schedule_dynamic
from members import ALL, Member


def _reserve_to_live(reserve: Reserve) -> Live:
    return Live(
        start_time=reserve.start_time,
        title=reserve.title.removeprefix("直播预约："),
        members=[reserve.member],
        host=reserve.member,
        tag="突击",
        kind=LiveKind.UNPLANNED,
    )


def fetch_official_schedule(api_config: ApiConfig, claude_config: ClaudeConfig, uid: int, day: date) -> list[Live]:
    dynamics = get_dynamic_draw_this_week(api_config, uid, day)
    return find_schedule_dynamic(claude_config, dynamics, day)


def fetch_all_reserves(api_config: ApiConfig, day: date) -> list[Live]:
    lives = []
    for member in ALL:
        reserves = get_reserve_this_week(api_config, member, day)
        lives.extend(_reserve_to_live(r) for r in reserves)
    return lives
