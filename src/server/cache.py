import sqlite3

import db
from bilibili.types import Live

_lives: list[Live] = []


def get_lives() -> list[Live]:
    return _lives


def refresh(conn: sqlite3.Connection) -> None:
    global _lives
    _lives = db.get_lives_this_week(conn)
