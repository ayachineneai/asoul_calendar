from threading import Lock

_cookie: str | None = None
_lock = Lock()


def get_cookie() -> str | None:
    with _lock:
        return _cookie


def set_cookie(value: str | None) -> None:
    global _cookie
    with _lock:
        _cookie = value
