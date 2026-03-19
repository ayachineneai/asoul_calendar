from dataclasses import dataclass, field
from typing import Callable

import httpx


@dataclass(frozen=True)
class ApiConfig:
    cookie: Callable[[], str | None] = lambda: None
    session: httpx.Client = field(default_factory=httpx.Client, hash=False, compare=False)
