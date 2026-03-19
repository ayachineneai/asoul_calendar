from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class LiveKind(Enum):
    SCHEDULE = "schedule"
    UNPLANNED = "unplanned"


class BroadcastKind(Enum):
    SOLO = "solo"
    DUO = "duo"
    GROUP = "group"


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
