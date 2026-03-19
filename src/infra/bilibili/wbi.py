import hashlib
import re
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode, quote


@dataclass(frozen=True)
class WbiKey:
    img_key: str
    sub_key: str


def with_wbi(data: dict[str, Any], wbi_key: WbiKey) -> dict[str, Any]:
    mixin_key = _gen_mixin_key(wbi_key.img_key, wbi_key.sub_key)
    w_rid, wts = _calc_w_rid(data, mixin_key)
    return {**data, 'w_rid': w_rid, 'wts': wts}


def parse_wbi_key(nav_data: dict[str, Any]) -> WbiKey:
    def key(url: str) -> str:
        return re.search(r'/([^/]+)\.\w+$', url).group(1)

    wbi_img = nav_data['data']['wbi_img']
    return WbiKey(img_key=key(wbi_img['img_url']), sub_key=key(wbi_img['sub_url']))


MIXIN_KEY_ENC_TAB: tuple[int, ...] = (
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
    33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40,
    61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11,
    36, 20, 34, 44, 52
)


def _gen_mixin_key(img_key: str, sub_key: str) -> str:
    raw_wbi_key = img_key + sub_key
    return ''.join(raw_wbi_key[i] for i in MIXIN_KEY_ENC_TAB)[:32]


def _calc_w_rid(data: dict[str, Any], mixin_key: str) -> tuple[str, int]:
    def encode(s: str, *_) -> str:
        return quote(s, safe='')

    wts = int(time.time())
    signed = dict(sorted({**data, 'wts': wts}.items()))
    query = urlencode(signed, quote_via=encode)
    w_rid = hashlib.md5((query + mixin_key).encode()).hexdigest()
    return w_rid, wts