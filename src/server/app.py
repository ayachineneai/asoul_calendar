import asyncio
import logging
from contextlib import asynccontextmanager

logging.basicConfig(level=logging.INFO)

from fastapi import FastAPI

from db import init_db
from server.cache import refresh
from server.config import DB_PATH, get_claude_config
from server.routes import router
from server.scheduler import reserves_loop, schedule_loop


@asynccontextmanager
async def lifespan(_: FastAPI):
    conn = init_db(DB_PATH)
    try:
        refresh(conn)
    finally:
        conn.close()
    claude_config = get_claude_config()
    tasks = [
        asyncio.create_task(schedule_loop(claude_config)),
        asyncio.create_task(reserves_loop()),
    ]
    yield
    for task in tasks:
        task.cancel()


app = FastAPI(lifespan=lifespan)
app.include_router(router)
