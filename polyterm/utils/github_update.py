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
_LOOKUP_COMMIT = object()
_MIN_COMMIT_PREFIX = 7

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


def _sha_from_tags_payload(payload: Any, version: Version) -> Optional[str]:
    if not isinstance(payload, list):
        return None
    for item in payload:
        if not isinstance(item, dict):
            continue
        parsed = _parse_version(str(item.get("name") or ""))
        if parsed != version:
            continue
        commit = item.get("commit")
        if not isinstance(commit, dict):
            continue
        sha = str(commit.get("sha") or "").strip()
        if sha:
            return sha
    return None


def _commits_match(installed: str, tag_sha: str) -> bool:
    left = (installed or "").strip().lower()
    right = (tag_sha or "").strip().lower()
    if len(left) < _MIN_COMMIT_PREFIX or len(right) < _MIN_COMMIT_PREFIX:
        return False
    return left == right or left.startswith(right) or right.startswith(left)


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


def _installed_commit_sha(installed_commit: Any) -> Optional[str]:
    if installed_commit is _LOOKUP_COMMIT:
        from .install_source import installed_git_commit

        return installed_git_commit()
    if installed_commit is None:
        return None
    text = str(installed_commit).strip()
    return text or None


def _latest_tag_commit_sha(
    latest_parsed: Version,
    *,
    get_json: Optional[JsonFetcher],
) -> Optional[str]:
    fetcher = get_json or _get_json
    return _sha_from_tags_payload(fetcher(GITHUB_TAGS_URL), latest_parsed)


def newer_github_version(
    current: str,
    *,
    get_json: Optional[JsonFetcher] = None,
    installed_commit: Any = _LOOKUP_COMMIT,
) -> Optional[str]:
    """Return the GitHub version if it is newer than ``current``, else None.

    Does not offer an update when ``current`` is already >= the latest tag.
    If the pipx/pip ``direct_url.json`` commit matches that tag's peel SHA,
    treat the install as current even when version strings drift.

    Network and parse failures return None and never raise. ``installed_commit``
    is injectable for tests; omit it to read PEP 610 metadata.
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
        if latest_parsed <= current_parsed:
            return None
        commit = _installed_commit_sha(installed_commit)
        if commit:
            try:
                tag_sha = _latest_tag_commit_sha(latest_parsed, get_json=get_json)
                if tag_sha and _commits_match(commit, tag_sha):
                    return None
            except Exception:
                pass
        return latest
    except Exception:
        return None
