import asyncio
import logging
from contextlib import asynccontextmanager

logging.basicConfig(level=logging.INFO)

import httpx
from fastapi import FastAPI

from infra.bilibili.types import ApiConfig
from infra.db import init_db, get_setting
from server.cache import refresh_lives
from server.config import config
from server.cookie import get_cookie, set_cookie
from server.routes import router
from server.scheduler import reserves_loop, schedule_loop
from utils import today


@asynccontextmanager
async def lifespan(_: FastAPI):
    conn = init_db(config.db_path)
    try:
        set_cookie(get_setting(conn, "bilibili_cookie") or config.bilibili_cookie)
        refresh_lives(conn, today())
    finally:
        conn.close()
    api_config = ApiConfig(cookie=get_cookie, session=httpx.Client(proxy=None))
    tasks = [
        asyncio.create_task(schedule_loop(api_config, config)),
        asyncio.create_task(reserves_loop(api_config, config)),
    ]
    yield
    for task in tasks:
        task.cancel()


app = FastAPI(lifespan=lifespan)
app.include_router(router)
