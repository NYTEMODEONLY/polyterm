"""Compare the installed version to GitHub releases/tags. Do not query PyPI."""

from __future__ import annotations

import json
import urllib.request
from typing import Any, Callable, Optional

from packaging.version import InvalidVersion, Version

GITHUB_OWNER = "NYTEMODEONLY"
GITHUB_REPO = "polyterm"
GITHUB_RELEASES_LATEST_URL = (
    f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
)
GITHUB_TAGS_URL = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/tags"

JsonFetcher = Callable[[str], Any]

_TIMEOUT_SECONDS = 5
_USER_AGENT = "polyterm"


def _parse_version(value: str) -> Optional[Version]:
    text = (value or "").strip()
    if text[:1] in ("v", "V"):
        text = text[1:]
    if not text:
        return None
    try:
        return Version(text)
    except InvalidVersion:
        return None


def _version_from_release_payload(payload: Any) -> Optional[Version]:
    if not isinstance(payload, dict):
        return None
    return _parse_version(str(payload.get("tag_name") or ""))


def _versions_from_tags_payload(payload: Any) -> list[Version]:
    if not isinstance(payload, list):
        return []
    versions: list[Version] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        parsed = _parse_version(str(item.get("name") or ""))
        if parsed is not None:
            versions.append(parsed)
    return versions


def _get_json(url: str) -> Any:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": _USER_AGENT,
        },
    )
    with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS) as response:
        raw = response.read()
    return json.loads(raw.decode("utf-8"))


def fetch_latest_github_version(*, get_json: Optional[JsonFetcher] = None) -> Optional[str]:
    """Return the latest GitHub release/tag version, or None on failure.

    Prefers ``/releases/latest`` ``tag_name``. Falls back to git tags and
    picks the highest parseable semver. Never raises. Does not query PyPI.
    """
    fetcher = get_json or _get_json
    try:
        parsed = _version_from_release_payload(fetcher(GITHUB_RELEASES_LATEST_URL))
        if parsed is not None:
            return str(parsed)
    except Exception:
        pass
    try:
        versions = _versions_from_tags_payload(fetcher(GITHUB_TAGS_URL))
        if versions:
            return str(max(versions))
    except Exception:
        pass
    return None


def newer_github_version(
    current: str,
    *,
    get_json: Optional[JsonFetcher] = None,
) -> Optional[str]:
    """Return the GitHub version if it is newer than ``current``, else None.

    Network and parse failures return None and never raise.
    """
    try:
        current_parsed = _parse_version(current)
        if current_parsed is None:
            return None
        latest = fetch_latest_github_version(get_json=get_json)
        if latest is None:
            return None
        latest_parsed = _parse_version(latest)
        if latest_parsed is None:
            return None
        if latest_parsed > current_parsed:
            return latest
        return None
    except Exception:
        return None
