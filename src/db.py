import json
import sqlite3
from datetime import timedelta

from bilibili.types import Live, LiveKind
from utils import format_datetime, live_slug, parse_datetime, this_week_range

_DDL = """
CREATE TABLE IF NOT EXISTS live (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    title      TEXT    NOT NULL,
    host       TEXT    NOT NULL,
    members    TEXT    NOT NULL,
    start_time TEXT    NOT NULL,
    tag        TEXT    NOT NULL,
    kind       TEXT    NOT NULL,
    slug       TEXT    NOT NULL DEFAULT '',
    UNIQUE (start_time, title)
);
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def init_db(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.executescript(_DDL)
    return conn


def get_lives_this_week(
    conn: sqlite3.Connection,
    members: list[str] | None = None,
    kind: LiveKind | None = None,
) -> list[Live]:
    week_start, week_end = this_week_range()

    conditions = ["start_time >= ?", "start_time < ?"]
    params: list = [str(week_start), str(week_end + timedelta(days=1))]

    if kind is not None:
        conditions.append("kind = ?")
        params.append(kind.value)

    if members:
        placeholders = ",".join("?" * len(members))
        conditions.append(f"m.value IN ({placeholders})")
        params.extend(members)
        from_clause = "live, json_each(live.members) m"
        select = "SELECT DISTINCT title, host, members, start_time, tag, kind, slug"
    else:
        from_clause = "live"
        select = "SELECT DISTINCT title, host, members, start_time, tag, kind, slug"

    where = " AND ".join(conditions)
    rows = conn.execute(
        f"{select} FROM {from_clause} WHERE {where} ORDER BY start_time",
        params,
    ).fetchall()

    return [
        Live(
            title=row[0],
            host=row[1],
            members=json.loads(row[2]),
            start_time=parse_datetime(row[3]),
            tag=row[4],
            kind=LiveKind(row[5]),
            slug=row[6],
        )
        for row in rows
    ]


def has_schedule_this_week(conn: sqlite3.Connection) -> bool:
    week_start, week_end = this_week_range()
    row = conn.execute(
        "SELECT 1 FROM live WHERE kind = ? AND start_time >= ? AND start_time < ? LIMIT 1",
        (LiveKind.SCHEDULE.value, str(week_start), str(week_end + timedelta(days=1))),
    ).fetchone()
    return row is not None


def get_setting(conn: sqlite3.Connection, key: str) -> str | None:
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return row[0] if row else None


def set_setting(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()


def save_lives(conn: sqlite3.Connection, lives: list[Live]) -> None:
    conn.executemany(
        "INSERT OR REPLACE INTO live (title, host, members, start_time, tag, kind, slug)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            (
                live.title,
                live.host,
                json.dumps(live.members, ensure_ascii=False),
                format_datetime(live.start_time),
                live.tag,
                live.kind.value,
                live_slug(format_datetime(live.start_time), live.title),
            )
            for live in lives
        ],
    )
    conn.commit()
