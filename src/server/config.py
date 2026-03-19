import os

import httpx
from pathlib import Path
from threading import Lock

from dotenv import load_dotenv

from bilibili.types import ApiConfig, ClaudeConfig

load_dotenv()

DB_PATH = os.environ.get("DB_PATH", str(Path(__file__).parent.parent.parent / "asoul.db"))
ASOUL_UID = int(os.environ.get("ASOUL_UID", "3493085336046382"))

_api_config: ApiConfig | None = None
_api_config_lock = Lock()


def get_api_config() -> ApiConfig:
    global _api_config
    with _api_config_lock:
        if _api_config is None:
            from server.cookie import get_cookie
            _api_config = ApiConfig(cookie=get_cookie, session=httpx.Client(proxy=None))
        return _api_config


def get_claude_config() -> ClaudeConfig:
    return ClaudeConfig(
        api_key=os.environ["CLAUDE_API_KEY"],
        model=os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6"),
        max_tokens=int(os.environ.get("CLAUDE_MAX_TOKENS", "4096")),
    )
