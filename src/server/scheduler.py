import asyncio
import logging
import threading

import infra.db as db
from infra.bilibili.types import ApiConfig
from infra.db import init_db
from app.schedule import fetch_all_reserves, fetch_official_schedule
from server.cache import refresh_lives
from server.config import AppConfig
from utils import today

_INTERVAL = 30 * 60
_logger = logging.getLogger(__name__)
_write_lock = threading.Lock()


def _try_fetch(api_config: ApiConfig, config: AppConfig) -> None:
    day = today()
    conn = init_db(config.db_path)
    try:
        if db.has_schedule_this_week(conn, day):
            return
        lives = fetch_official_schedule(api_config, config.claude, config.zhijiang_uid, day)
        if lives:
            with _write_lock:
                db.save_lives(conn, lives)
                refresh_lives(conn, day)
            _logger.info("本周官方日程已入库。")
    finally:
        conn.close()


def _fetch_reserves(api_config: ApiConfig, config: AppConfig) -> None:
    day = today()
    conn = init_db(config.db_path)
    try:
        lives = fetch_all_reserves(api_config, day)
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
