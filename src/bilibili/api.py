from typing import Any, Callable

from .types import ApiConfig
from . import wbi, code

_wbi_key: wbi.WbiKey | None = None

def nav(api_config: ApiConfig) -> dict:
    url = "https://api.bilibili.com/x/web-interface/nav"
    headers = _headers(api_config)
    return api_config.session.get(url, headers=headers).json()

def reservation(api_config: ApiConfig, vmid: int) -> dict:
    url = "https://api.bilibili.com/x/space/reservation"
    headers = _headers(api_config)
    params = {"vmid": vmid}
    return api_config.session.get(url, headers=headers, params=params).json()


def get_space_dynamics(
    api_config: ApiConfig,
    host_mid: int,
    offset: str = "",
) -> dict:
    return _call_with_wbi(
        api_config,
        lambda key: _get_space_dynamics(api_config, host_mid, offset, key)
    )


def _get_space_dynamics(
    api_config: ApiConfig,
    host_mid: int,
    offset: str,
    wbi_key: wbi.WbiKey,
) -> dict:
    url = "https://api.bilibili.com/x/polymer/web-dynamic/v1/feed/space"
    params: dict[str, Any] = wbi.with_wbi({
        "host_mid": host_mid,
        "offset": offset,
        "features": "itemOpusStyle,listOnlyfans,opusBigCover,onlyfansVote,forwardListHidden,decorationCard,commentsNewVersion,onlyfansAssetsV2,ugcDelete,onlyfansQaCard,avatarAutoTheme,sunflowerStyle,cardsEnhance,eva3CardOpus,eva3CardVideo,eva3CardComment,eva3CardUser"
    }, wbi_key)
    headers = _headers(api_config)
    return api_config.session.get(url, params=params, headers=headers).json()


def _call_with_wbi(api_config: ApiConfig, call: Callable[[wbi.WbiKey], dict]) -> dict:
    result = call(_get_wbi_key(api_config))
    if _is_risk_control_failure(result):
        result = call(_get_wbi_key(api_config, True))
    return result


def _get_wbi_key(api_config: ApiConfig, refresh: bool = False) -> wbi.WbiKey:
    global _wbi_key
    if refresh or not _wbi_key:
        new_wbi_key = wbi.parse_wbi_key(nav(api_config))
        _wbi_key = new_wbi_key
        return new_wbi_key
    return _wbi_key


def _is_risk_control_failure(rsp) -> bool:
    return _get_code(rsp) == code.RISK_CTL

def _get_code(rsp):
    return rsp.get('code')


def _headers(api_config: ApiConfig) -> dict:
    return {
        "Cookie": api_config.cookie,
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
        "Origin": "https://www.bilibili.com",
        "Referer": "https://www.bilibili.com/"
    }

