from dataclasses import asdict

import fastapi
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.responses import RedirectResponse, Response
from pydantic import BaseModel

from app.types import BroadcastKind, Live, LiveKind
from datetime import datetime
from utils import today

from infra.db import get_conn, get_lives_this_year, insert_live, set_setting, update_live
from app.ics import generate_ics
from app.members import ALL as ALL_MEMBERS
from server.cache import get_lives
from server.config import config
from server.cookie import set_cookie

_bearer = HTTPBearer()
_VALID_MEMBER_CODES = {m.code for m in ALL_MEMBERS}

router = APIRouter()


class CookieUpdate(BaseModel):
    cookie: str


class LiveBody(BaseModel):
    start_time: datetime
    title: str
    members: list[str]
    host: str
    tag: str
    kind: LiveKind


@router.post("/admin/cookie")
def update_cookie(
    body: CookieUpdate,
    credentials: HTTPAuthorizationCredentials = fastapi.Depends(_bearer),
) -> dict:
    _auth(credentials)
    conn = get_conn(config.db_path)
    try:
        set_setting(conn, "bilibili_cookie", body.cookie)
    finally:
        conn.close()
    set_cookie(body.cookie)
    return {"ok": True}


def _auth(credentials: HTTPAuthorizationCredentials) -> None:
    if credentials.credentials != config.admin_token:
        raise HTTPException(status_code=401, detail="Unauthorized")


@router.post("/admin/lives")
def create_live(
    body: LiveBody,
    credentials: HTTPAuthorizationCredentials = fastapi.Depends(_bearer),
) -> dict:
    _auth(credentials)
    live = Live(**body.model_dump())
    conn = get_conn(config.db_path)
    try:
        insert_live(conn, live)
    finally:
        conn.close()
    return {"ok": True}


@router.patch("/admin/lives/{slug}")
def patch_live(
    slug: str,
    body: LiveBody,
    credentials: HTTPAuthorizationCredentials = fastapi.Depends(_bearer),
) -> dict:
    _auth(credentials)
    live = Live(**body.model_dump())
    conn = get_conn(config.db_path)
    try:
        found = update_live(conn, slug, live)
    finally:
        conn.close()
    if not found:
        raise HTTPException(status_code=404, detail="Live not found")
    return {"ok": True}


def _broadcast_of(live: Live) -> BroadcastKind:
    n = len(live.members)
    if n == 1:
        return BroadcastKind.SOLO
    if n == 2:
        return BroadcastKind.DUO
    return BroadcastKind.GROUP


def _filter_lives_from(
    lives: list[Live],
    members: list[str],
    kind: LiveKind | None,
    broadcast: list[BroadcastKind],
    tag: list[str],
    slug: list[str],
) -> list[Live]:
    member_set = {m for m in members if m in _VALID_MEMBER_CODES}
    broadcast_set = set(broadcast)
    tag_set = set(tag)
    slug_set = set(slug)
    return [
        live for live in lives
        if (not slug_set or live.slug in slug_set)
        and (not member_set or bool(set(live.members) & member_set))
        and (kind is None or live.kind == kind)
        and (not broadcast_set or _broadcast_of(live) in broadcast_set)
        and (not tag_set or live.tag in tag_set)
    ]


@router.get("/lives")
def get_lives_this_week(
    members: list[str] = Query(default=[]),
    kind: LiveKind | None = Query(default=None),
    broadcast: list[BroadcastKind] = Query(default=[]),
    tag: list[str] = Query(default=[]),
    slug: list[str] = Query(default=[]),
) -> list[dict]:
    return [
        {**asdict(live), "start_time": live.start_time.isoformat(), "kind": live.kind.value}
        for live in _filter_lives_from(get_lives(), members, kind, broadcast, tag, slug)
    ]


@router.get("/subscribe")
def subscribe(
    request: Request,
    members: list[str] = Query(default=[]),
    kind: LiveKind | None = Query(default=None),
    broadcast: list[BroadcastKind] = Query(default=[]),
    tag: list[str] = Query(default=[]),
    slug: list[str] = Query(default=[]),
    reminder: int = Query(default=0, ge=0),
    duration: int = Query(default=120, ge=1),
) -> RedirectResponse:
    params: list[tuple] = [("reminder", reminder), ("duration", duration)]
    for m in members:
        params.append(("members", m))
    if kind is not None:
        params.append(("kind", kind.value))
    for b in broadcast:
        params.append(("broadcast", b.value))
    for t in tag:
        params.append(("tag", t))
    for s in slug:
        params.append(("slug", s))
    base = str(request.url_for("get_calendar"))
    query = "&".join(f"{k}={v}" for k, v in params)
    url = f"{base}?{query}".replace("http://", "webcal://").replace("https://", "webcal://")
    return RedirectResponse(url)


@router.get("/calendar.ics")
def get_calendar(
    members: list[str] = Query(default=[]),
    kind: LiveKind | None = Query(default=None),
    broadcast: list[BroadcastKind] = Query(default=[]),
    tag: list[str] = Query(default=[]),
    slug: list[str] = Query(default=[]),
    reminder: int = Query(default=0, ge=0),
    duration: int = Query(default=120, ge=1),
) -> Response:
    conn = get_conn(config.db_path)
    try:
        lives = get_lives_this_year(conn, today().year)
    finally:
        conn.close()
    content = generate_ics(
        _filter_lives_from(lives, members, kind, broadcast, tag, slug),
        reminder_minutes=reminder,
        duration_minutes=duration,
    )
    return Response(
        content=content,
        media_type="text/calendar",
        headers={"Content-Disposition": 'inline; filename="asoul.ics"'},
    )
