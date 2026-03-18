from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

import httpx


class LiveKind(Enum):
    SCHEDULE = "schedule"
    UNPLANNED = "unplanned"


class BroadcastKind(Enum):
    SOLO = "solo"
    DUO = "duo"
    GROUP = "group"


@dataclass(frozen=True)
class ApiConfig:
    cookie: str | None = ""
    session: httpx.Client = field(default_factory=httpx.Client, hash=False, compare=False)


@dataclass(frozen=True)
class ClaudeConfig:
    api_key: str
    model: str
    max_tokens: int


@dataclass(frozen=True)
class Reserve:
    title: str
    start_time: datetime
    member: str


@dataclass(frozen=True)
class Live:
    start_time: datetime
    title: str
    members: list[str]
    host: str
    tag: str
    kind: LiveKind
    slug: str = ""
