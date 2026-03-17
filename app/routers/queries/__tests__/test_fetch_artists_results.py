from unittest.mock import patch

import pytest

from app.routers.queries.fetch_artist_results import fetch_artist_results


@pytest.mark.asyncio
@patch("app.routers.queries.fetch_artist_results.client")
async def test_fetch_artist_results_returns_hits(mock_client):
    mock_client.search.return_value = {
        "hits": {
            "hits": [
                {"_source": {"name": "Artist1"}},
                {"_source": {"name": "Artist2"}},
            ]
        }
    }
    results = await fetch_artist_results("Artist")
    assert results == [{"name": "Artist1"}, {"name": "Artist2"}]


@pytest.mark.asyncio
@patch("app.routers.queries.fetch_artist_results.client")
async def test_fetch_artist_results_returns_empty_when_no_hits(mock_client):
    mock_client.search.return_value = {"hits": {"hits": []}}
    results = await fetch_artist_results("Unknown")
    assert results == []
