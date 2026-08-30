"""SubgraphClient is retired and must fail on construct."""

import pytest

from polyterm.api.subgraph import SubgraphClient
from polyterm.utils.errors import APIError


def test_construct_raises_api_error():
    with pytest.raises(APIError) as exc:
        SubgraphClient()
    assert "not supported" in exc.value.message
    assert "GammaClient" in (exc.value.suggestion or "")


def test_construct_with_custom_endpoint_still_raises():
    with pytest.raises(APIError):
        SubgraphClient(endpoint="https://example.invalid/subgraph")


def test_not_exported_from_api_package():
    import polyterm.api as api
    assert "SubgraphClient" not in api.__all__
    assert not hasattr(api, "SubgraphClient")
