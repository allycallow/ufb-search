from unittest.mock import patch

import pytest

from app.routers.queries.fetch_playlist_results import fetch_playlist_results


@pytest.mark.asyncio
@patch("app.routers.queries.fetch_playlist_results.client")
async def test_fetch_playlist_results_returns_hits(mock_client):
    mock_client.search.return_value = {
        "hits": {
            "hits": [
                {"_source": {"name": "Playlist1"}},
                {"_source": {"name": "Playlist2"}},
            ]
        }
    }
    results = await fetch_playlist_results("Playlist")
    assert results == [{"name": "Playlist1"}, {"name": "Playlist2"}]


@pytest.mark.asyncio
@patch("app.routers.queries.fetch_playlist_results.client")
async def test_fetch_playlist_results_returns_empty_when_no_hits(mock_client):
    mock_client.search.return_value = {"hits": {"hits": []}}
    results = await fetch_playlist_results("Unknown")
    assert results == []


@pytest.mark.asyncio
@patch("app.routers.queries.fetch_playlist_results.client")
async def test_fetch_playlist_results_filters_type_and_matches_name_only(mock_client):
    mock_client.search.return_value = {"hits": {"hits": []}}
    await fetch_playlist_results("late night")

    body = mock_client.search.call_args.kwargs["body"]
    assert body["size"] == 8
    assert body["query"]["bool"]["filter"] == [{"term": {"type": "playlists"}}]
    assert body["query"]["bool"]["must"] == [
        {
            "bool": {
                "must": [
                    {
                        "multi_match": {
                            "query": "late",
                            "fields": ["name"],
                            "operator": "and",
                        }
                    },
                    {
                        "bool": {
                            "should": [{"prefix": {"name": {"value": "night"}}}],
                            "minimum_should_match": 1,
                        }
                    },
                ]
            }
        }
    ]
