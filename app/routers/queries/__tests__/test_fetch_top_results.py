from unittest.mock import patch

import pytest

from app.routers.queries.fetch_top_results import fetch_top_results


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
async def test_fetch_top_results_excludes_unpublished_and_unready(mock_client):
    mock_client.search.return_value = {"hits": {"hits": []}}
    await fetch_top_results("query")

    query_filter = mock_client.search.call_args.kwargs["body"]["query"]["bool"][
        "filter"
    ][0]["bool"]

    should = query_filter["should"]
    assert {
        "bool": {"must_not": {"terms": {"type": ["releases", "tracks"]}}},
    } in should
    assert {"term": {"is_visible": True}} in should
