import json
import sqlite3
from datetime import date, timedelta

from app.types import Live, LiveKind
from utils import format_datetime, live_slug, parse_datetime, week_range

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


def init_db(path: str) -> None:
    conn = sqlite3.connect(path)
    conn.executescript(_DDL)
    conn.close()


def get_conn(path: str) -> sqlite3.Connection:
    return sqlite3.connect(path)


def get_lives_this_week(
    conn: sqlite3.Connection,
    day: date,
    members: list[str] | None = None,
    kind: LiveKind | None = None,
) -> list[Live]:
    week_start, week_end = week_range(day)

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


def get_lives_this_year(conn: sqlite3.Connection, year: int) -> list[Live]:
    rows = conn.execute(
        "SELECT title, host, members, start_time, tag, kind, slug"
        " FROM live WHERE start_time >= ? AND start_time < ? ORDER BY start_time",
        (f"{year}-01-01", f"{year + 1}-01-01"),
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


def delete_lives(conn: sqlite3.Connection, slugs: list[str]) -> int:
    placeholders = ",".join("?" * len(slugs))
    cursor = conn.execute(f"DELETE FROM live WHERE slug IN ({placeholders})", slugs)
    conn.commit()
    return cursor.rowcount


def has_schedule_this_week(conn: sqlite3.Connection, day: date) -> bool:
    week_start, week_end = week_range(day)
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


def insert_live(conn: sqlite3.Connection, live: Live) -> None:
    conn.execute(
        "INSERT INTO live (title, host, members, start_time, tag, kind, slug) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            live.title,
            live.host,
            json.dumps(live.members, ensure_ascii=False),
            format_datetime(live.start_time),
            live.tag,
            live.kind.value,
            live_slug(format_datetime(live.start_time), live.title),
        ),
    )
    conn.commit()


def update_live(conn: sqlite3.Connection, slug: str, live: Live) -> bool:
    cursor = conn.execute(
        "UPDATE live SET title=?, host=?, members=?, start_time=?, tag=?, kind=?, slug=? WHERE slug=?",
        (
            live.title,
            live.host,
            json.dumps(live.members, ensure_ascii=False),
            format_datetime(live.start_time),
            live.tag,
            live.kind.value,
            live_slug(format_datetime(live.start_time), live.title),
            slug,
        ),
    )
    conn.commit()
    return cursor.rowcount > 0


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
