from dataclasses import asdict

import fastapi
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.responses import RedirectResponse, Response
from pydantic import BaseModel

from app.types import BroadcastKind, Live, LiveKind
from datetime import datetime
from utils import today

from infra.db import delete_lives, get_conn, get_lives_this_year, insert_live, set_live_hide, set_setting, update_live
from app.ics import generate_ics
from app.members import ALL as ALL_MEMBERS
from infra.bilibili.dynamics import get_all_reserve
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
    hide: bool = False


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


def _is_authed(credentials: HTTPAuthorizationCredentials | None) -> bool:
    return credentials is not None and credentials.credentials == config.admin_token


@router.get("/admin/verify")
def verify(
    credentials: HTTPAuthorizationCredentials = fastapi.Depends(_bearer),
) -> dict:
    _auth(credentials)
    return {"ok": True}


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


@router.delete("/admin/lives")
def delete_lives_endpoint(
    slugs: list[str] = Query(default=[]),
    credentials: HTTPAuthorizationCredentials = fastapi.Depends(_bearer),
) -> dict:
    _auth(credentials)
    if not slugs:
        raise HTTPException(status_code=400, detail="No slugs provided")
    conn = get_conn(config.db_path)
    try:
        deleted = delete_lives(conn, slugs)
    finally:
        conn.close()
    return {"deleted": deleted}


@router.patch("/admin/lives/{slug}/hide")
def set_live_hide_endpoint(
    slug: str,
    hide: bool = Query(),
    credentials: HTTPAuthorizationCredentials = fastapi.Depends(_bearer),
) -> dict:
    _auth(credentials)
    conn = get_conn(config.db_path)
    try:
        found = set_live_hide(conn, slug, hide)
    finally:
        conn.close()
    if not found:
        raise HTTPException(status_code=404, detail="Live not found")
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
def get_lives_endpoint(
    members: list[str] = Query(default=[]),
    kind: LiveKind | None = Query(default=None),
    broadcast: list[BroadcastKind] = Query(default=[]),
    tag: list[str] = Query(default=[]),
    slug: list[str] = Query(default=[]),
    credentials: HTTPAuthorizationCredentials | None = fastapi.Depends(HTTPBearer(auto_error=False)),
) -> list[dict]:
    conn = get_conn(config.db_path)
    try:
        lives = get_lives_this_year(conn, today().year, show_hidden=_is_authed(credentials))
    finally:
        conn.close()
    return [
        {**asdict(live), "start_time": live.start_time.isoformat(), "kind": live.kind.value}
        for live in _filter_lives_from(lives, members, kind, broadcast, tag, slug)
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


@router.get("/admin/reserves")
def fetch_reserves(
    request: Request,
    credentials: HTTPAuthorizationCredentials = fastapi.Depends(_bearer),
) -> list[dict]:
    _auth(credentials)
    api_config = request.app.state.api_config
    reserves = []
    for member in ALL_MEMBERS:
        reserves.extend(get_all_reserve(api_config, member))
    return [{"title": r.title, "start_time": r.start_time.isoformat(), "member": r.member} for r in reserves]


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
