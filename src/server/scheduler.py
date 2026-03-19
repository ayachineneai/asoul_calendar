import asyncio
import logging
import threading
from datetime import date

import infra.db as db
from app.members import ALL
from app.types import Live, LiveKind, Reserve
from infra.ai import ClaudeConfig, find_schedule_dynamic
from infra.bilibili.dynamics import get_dynamic_draw_this_week, get_reserve_this_week
from infra.bilibili.types import ApiConfig
from infra.db import get_conn
from server.cache import refresh_lives
from server.config import AppConfig
from utils import today

_INTERVAL = 30 * 60
_logger = logging.getLogger(__name__)
_write_lock = threading.Lock()


def _reserve_to_live(reserve: Reserve) -> Live:
    return Live(
        start_time=reserve.start_time,
        title=reserve.title.removeprefix("直播预约："),
        members=[reserve.member],
        host=reserve.member,
        tag="突击",
        kind=LiveKind.UNPLANNED,
    )


def _fetch_official_schedule(api_config: ApiConfig, claude_config: ClaudeConfig, uid: int, day: date) -> list[Live]:
    dynamics = get_dynamic_draw_this_week(api_config, uid, day)
    return find_schedule_dynamic(claude_config, dynamics, day)


def _fetch_all_reserves(api_config: ApiConfig, day: date) -> list[Live]:
    lives = []
    for member in ALL:
        reserves = get_reserve_this_week(api_config, member, day)
        lives.extend(_reserve_to_live(r) for r in reserves)
    return lives


def _try_fetch(api_config: ApiConfig, config: AppConfig) -> None:
    day = today()
    conn = get_conn(config.db_path)
    try:
        if db.has_schedule_this_week(conn, day):
            return
        lives = _fetch_official_schedule(api_config, config.claude, config.zhijiang_uid, day)
        if lives:
            with _write_lock:
                db.save_lives(conn, lives)
                refresh_lives(conn, day)
            _logger.info("本周官方日程已入库。")
    finally:
        conn.close()


def _fetch_reserves(api_config: ApiConfig, config: AppConfig) -> None:
    day = today()
    conn = get_conn(config.db_path)
    try:
        lives = _fetch_all_reserves(api_config, day)
        _logger.info("找到直播：%s", lives)
        with _write_lock:
            db.save_lives(conn, lives)
            refresh_lives(conn, day)
    finally:
        conn.close()


async def reserves_loop(api_config: ApiConfig, config: AppConfig) -> None:
    while True:
        try:
            await asyncio.to_thread(_fetch_reserves, api_config, config)
        except Exception:
            _logger.exception("抓取预约失败，下次重试。")
        await asyncio.sleep(_INTERVAL)


async def schedule_loop(api_config: ApiConfig, config: AppConfig) -> None:
    while True:
        try:
            await asyncio.to_thread(_try_fetch, api_config, config)
        except Exception:
            _logger.exception("抓取官方日程失败，下次重试。")
        await asyncio.sleep(_INTERVAL)
