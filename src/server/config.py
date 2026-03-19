import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from infra.ai import ClaudeConfig

load_dotenv()

@dataclass(frozen=True)
class AppConfig:
    db_path: str
    zhijiang_uid: int
    admin_token: str
    bilibili_cookie: str | None
    claude: ClaudeConfig

    @classmethod
    def from_env(cls) -> "AppConfig":
        return cls(
            db_path=os.environ.get("DB_PATH", str(Path(__file__).parent.parent.parent / "asoul.db")),
            zhijiang_uid=int(os.environ.get("ZHIJIANG_UID", "3493085336046382")),
            admin_token=os.environ["ADMIN_TOKEN"],
            bilibili_cookie=os.environ.get("BILIBILI_COOKIE"),
            claude=ClaudeConfig(
                api_key=os.environ["CLAUDE_API_KEY"],
                model=os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6"),
                max_tokens=int(os.environ.get("CLAUDE_MAX_TOKENS", "4096")),
            ),
        )


config = AppConfig.from_env()
