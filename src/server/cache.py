import sqlite3
from datetime import date

import infra.db as db
from app.types import Live

_lives: list[Live] = []


def get_lives() -> list[Live]:
    return _lives


def refresh_lives(conn: sqlite3.Connection, day: date) -> None:
    global _lives
    _lives = db.get_lives_this_week(conn, day)
