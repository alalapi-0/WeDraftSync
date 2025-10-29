"""Utilities for retrieving WeChat public account access tokens."""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict

import requests

_CACHE_FILE = Path(__file__).resolve().parent.parent / ".access_token_cache.json"
_CACHE_SAFETY_WINDOW = 60  # seconds


def _load_cache() -> Dict[str, Any]:
    """Load cached access tokens from disk."""
    if not _CACHE_FILE.exists():
        return {}

    try:
        with _CACHE_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (json.JSONDecodeError, OSError) as exc:
        logging.warning("Failed to read cache file %s: %s", _CACHE_FILE, exc)
        return {}

    if not isinstance(data, dict):
        logging.warning("Cache file %s did not contain a mapping. Ignoring.", _CACHE_FILE)
        return {}

    return data


def _save_cache(cache: Dict[str, Any]) -> None:
    """Persist the access token cache to disk."""
    try:
        with _CACHE_FILE.open("w", encoding="utf-8") as file:
            json.dump(cache, file, ensure_ascii=False, indent=2)
    except OSError as exc:
        logging.warning("Failed to write cache file %s: %s", _CACHE_FILE, exc)


def _get_cached_token(appid: str) -> str:
    """Return the cached token for ``appid`` when still valid."""
    cache = _load_cache()
    if not cache:
        return ""

    entry = cache.get(appid)
    if not isinstance(entry, dict):
        return ""

    access_token = entry.get("access_token")
    expires_at = entry.get("expires_at", 0)

    if not isinstance(access_token, str) or not isinstance(expires_at, (int, float)):
        return ""

    if time.time() >= expires_at:
        return ""

    return access_token


def _update_cache(appid: str, access_token: str, expires_in: int) -> None:
    """Update the cache with the freshly retrieved access token."""
    expires_at = time.time() + max(0, expires_in - _CACHE_SAFETY_WINDOW)
    cache = _load_cache()
    cache[appid] = {
        "access_token": access_token,
        "expires_at": expires_at,
    }
    _save_cache(cache)


def get_access_token(appid: str, appsecret: str) -> str:
    """Retrieve the access token for a WeChat public account.

    Parameters
    ----------
    appid: str
        The AppID for the public account.
    appsecret: str
        The AppSecret for the public account.

    Returns
    -------
    str
        The access token string when the request succeeds. Returns an empty
        string and logs error information when the request fails.
    """
    if not appid or not appsecret:
        logging.error("AppID and AppSecret are required to request an access token.")
        return ""

    cached_token = _get_cached_token(appid)
    if cached_token:
        logging.debug("Returning cached access token for appid %s.", appid)
        return cached_token

    request_url = (
        "https://api.weixin.qq.com/cgi-bin/token"
        "?grant_type=client_credential&appid={appid}&secret={secret}"
    ).format(appid=appid, secret=appsecret)

    try:
        response = requests.get(request_url, timeout=10)
    except requests.RequestException as exc:
        logging.error("Network error while fetching access token: %s", exc)
        return ""

    if response.status_code != 200:
        logging.error(
            "WeChat API responded with unexpected status %s when fetching access token.",
            response.status_code,
        )
        return ""

    try:
        data = response.json()
    except ValueError as exc:  # pragma: no cover - defensive
        logging.error("Failed to decode JSON response for access token: %s", exc)
        return ""

    access_token = data.get("access_token")
    expires_in = data.get("expires_in")

    if isinstance(access_token, str) and isinstance(expires_in, (int, float)):
        _update_cache(appid, access_token, int(expires_in))
        return access_token

    errcode = data.get("errcode")
    errmsg = data.get("errmsg", "Unknown error")
    logging.error("Failed to fetch access token. errcode=%s, errmsg=%s", errcode, errmsg)
    return ""
