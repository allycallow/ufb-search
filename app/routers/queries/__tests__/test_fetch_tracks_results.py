from unittest.mock import patch

import pytest

from app.routers.queries.fetch_tracks_results import fetch_tracks_results


@pytest.mark.asyncio
@patch("app.routers.queries.fetch_tracks_results.client")
async def test_fetch_tracks_results_returns_hits(mock_client):
    mock_client.search.return_value = {
        "hits": {
            "hits": [
                {"_source": {"title": "Track1"}},
                {"_source": {"title": "Track2"}},
            ]
        }
    }
    results = await fetch_tracks_results("Track")
    assert results == [{"title": "Track1"}, {"title": "Track2"}]


@pytest.mark.asyncio
@patch("app.routers.queries.fetch_tracks_results.client")
async def test_fetch_track_results_returns_empty_when_no_hits(mock_client):
    mock_client.search.return_value = {"hits": {"hits": []}}
    results = await fetch_tracks_results("Unknown")
    assert results == []
