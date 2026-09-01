"""GitHub release/tag version check. HTTP is stubbed; no live GitHub."""

from unittest.mock import patch

from polyterm.utils.github_update import (
    GITHUB_RELEASES_LATEST_URL,
    GITHUB_TAGS_URL,
    fetch_latest_github_version,
    newer_github_version,
)


def test_newer_tag_available_from_latest_release():
    captured = []

    def get_json(url):
        captured.append(url)
        return {"tag_name": "v0.11.0"}

    latest = newer_github_version("0.10.0", get_json=get_json)

    assert latest == "0.11.0"
    assert captured == [GITHUB_RELEASES_LATEST_URL]
    assert all("pypi.org" not in url for url in captured)
    assert all("api.github.com/repos/NYTEMODEONLY/polyterm" in url for url in captured)


def test_already_current_returns_none():
    def get_json(url):
        return {"tag_name": "v0.10.0"}

    assert newer_github_version("0.10.0", get_json=get_json) is None
    assert fetch_latest_github_version(get_json=get_json) == "0.10.0"


def test_network_error_returns_none():
    def get_json(url):
        raise TimeoutError("network down")

    assert fetch_latest_github_version(get_json=get_json) is None
    assert newer_github_version("0.10.0", get_json=get_json) is None


def test_falls_back_to_tags_when_latest_release_fails():
    def get_json(url):
        if url == GITHUB_RELEASES_LATEST_URL:
            raise OSError("404")
        if url == GITHUB_TAGS_URL:
            return [{"name": "v0.10.0"}, {"name": "v0.11.0"}]
        raise AssertionError(f"unexpected url: {url}")

    assert fetch_latest_github_version(get_json=get_json) == "0.11.0"
    assert newer_github_version("0.10.0", get_json=get_json) == "0.11.0"


def test_urlopen_is_used_and_timeouts_are_swallowed():
    with patch("urllib.request.urlopen", side_effect=OSError("fail")) as mock_open:
        assert newer_github_version("0.10.0") is None
    assert mock_open.called
    request = mock_open.call_args[0][0]
    url = getattr(request, "full_url", str(request))
    assert "api.github.com" in url
    assert "pypi.org" not in url
