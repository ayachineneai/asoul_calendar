import asyncio
import logging
import threading

import db
from bilibili.types import ClaudeConfig
from db import init_db
from schedule import fetch_all_reserves, fetch_official_schedule
from server.cache import refresh_lives
from server.config import ASOUL_UID, DB_PATH, get_api_config
from utils import today

_INTERVAL = 30 * 60
_logger = logging.getLogger(__name__)
_write_lock = threading.Lock()


def _try_fetch(claude_config: ClaudeConfig) -> None:
    day = today()
    conn = init_db(DB_PATH)
    try:
        if db.has_schedule_this_week(conn, day):
            return
        lives = fetch_official_schedule(get_api_config(), claude_config, ASOUL_UID, day)
        if lives:
            with _write_lock:
                db.save_lives(conn, lives)
                refresh_lives(conn, day)
            _logger.info("本周官方日程已入库。")
    finally:
        conn.close()


def _fetch_reserves() -> None:
    day = today()
    conn = init_db(DB_PATH)
    try:
        lives = fetch_all_reserves(get_api_config(), day)
        _logger.info("找到直播：%s", lives)
        with _write_lock:
            db.save_lives(conn, lives)
            refresh_lives(conn, day)
    finally:
        conn.close()


async def reserves_loop() -> None:
    while True:
        try:
            await asyncio.to_thread(_fetch_reserves)
        except Exception:
            _logger.exception("抓取预约失败，下次重试。")
        await asyncio.sleep(_INTERVAL)


async def schedule_loop(claude_config: ClaudeConfig) -> None:
    while True:
        try:
            await asyncio.to_thread(_try_fetch, claude_config)
        except Exception:
            _logger.exception("抓取官方日程失败，下次重试。")
        await asyncio.sleep(_INTERVAL)
