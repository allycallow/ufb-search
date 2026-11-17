from unittest.mock import patch

import pytest

from app.routers.queries.fetch_top_results import fetch_top_results
from app.routers.queries.name_match import name_match_query


def _bool_query(mock_client):
    return mock_client.search.call_args.kwargs["body"]["query"]["function_score"][
        "query"
    ]["bool"]


@pytest.mark.asyncio
@patch("app.routers.queries.fetch_top_results.client")
async def test_fetch_top_results_returns_hits(mock_client):
    mock_client.search.return_value = {
        "hits": {
            "hits": [
                {"_source": {"name": "Top1"}},
                {"_source": {"name": "Top2"}},
            ]
        }
    }
    results = await fetch_top_results("Top")
    assert results == [{"name": "Top1"}, {"name": "Top2"}]


@pytest.mark.asyncio
@patch("app.routers.queries.fetch_top_results.client")
async def test_fetch_top_results_returns_empty_when_no_hits(mock_client):
    mock_client.search.return_value = {"hits": {"hits": []}}
    results = await fetch_top_results("Unknown")
    assert results == []


@pytest.mark.asyncio
@patch("app.routers.queries.fetch_top_results.client")
async def test_fetch_top_results_boosts_playlists(mock_client):
    mock_client.search.return_value = {"hits": {"hits": []}}
    await fetch_top_results("query")

    should = _bool_query(mock_client)["should"]
    assert {"match": {"type": {"query": "playlists", "boost": 1}}} in should


@pytest.mark.asyncio
@patch("app.routers.queries.fetch_top_results.client")
async def test_fetch_top_results_excludes_unpublished_and_unready(mock_client):
    mock_client.search.return_value = {"hits": {"hits": []}}
    await fetch_top_results("query")

    query_filter = _bool_query(mock_client)["filter"][0]["bool"]

    should = query_filter["should"]
    assert {
        "bool": {"must_not": {"terms": {"type": ["releases", "tracks"]}}},
    } in should
    assert {"term": {"is_visible": True}} in should


@pytest.mark.asyncio
@patch("app.routers.queries.fetch_top_results.client")
async def test_fetch_top_results_requires_every_word(mock_client):
    mock_client.search.return_value = {"hits": {"hits": []}}
    await fetch_top_results("Hot Creations")

    must = _bool_query(mock_client)["must"]
    assert must == [name_match_query("Hot Creations")]
    assert "query_string" not in str(mock_client.search.call_args)


@pytest.mark.asyncio
@patch("app.routers.queries.fetch_top_results.client")
async def test_fetch_top_results_ranks_by_popularity_without_filtering(mock_client):
    mock_client.search.return_value = {"hits": {"hits": []}}
    await fetch_top_results("query")

    function_score = mock_client.search.call_args.kwargs["body"]["query"][
        "function_score"
    ]
    assert function_score["field_value_factor"]["field"] == "popularity"
    assert "range" not in str(function_score["query"]["bool"]["should"])
