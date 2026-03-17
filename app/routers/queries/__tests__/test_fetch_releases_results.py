from unittest.mock import patch

import pytest

from app.routers.queries.fetch_releases_results import fetch_releases_results


@pytest.mark.asyncio
@patch("app.routers.queries.fetch_releases_results.client")
async def test_fetch_release_results_returns_hits(mock_client):
    mock_client.search.return_value = {
        "hits": {
            "hits": [
                {"_source": {"title": "Release1"}},
                {"_source": {"title": "Release2"}},
            ]
        }
    }
    results = await fetch_releases_results("Release")
    assert results == [{"title": "Release1"}, {"title": "Release2"}]


@pytest.mark.asyncio
@patch("app.routers.queries.fetch_releases_results.client")
async def test_fetch_release_results_returns_empty_when_no_hits(mock_client):
    mock_client.search.return_value = {"hits": {"hits": []}}
    results = await fetch_releases_results("Unknown")
    assert results == []
