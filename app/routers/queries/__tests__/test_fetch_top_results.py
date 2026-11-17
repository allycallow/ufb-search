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


LABEL = {"id": "L1", "type": "labels", "name": "Hot Creations"}
ARTIST = {"id": "A1", "type": "artists", "name": "Fusion"}
SAME_NAME_LABEL = {"id": "L2", "type": "labels", "name": "Fusion"}


def _children(*groups):
    return {
        "responses": [{"hits": {"hits": [{"_source": d} for d in g]}} for g in groups]
    }


def _release(n):
    return {"id": f"R{n}", "type": "releases", "title": f"Release {n}"}


def _track(n):
    return {"id": f"T{n}", "type": "tracks", "title": f"Track {n}"}


def _search_hits(*docs):
    return {"hits": {"hits": [{"_source": d} for d in docs]}}


@pytest.mark.asyncio
@patch("app.routers.queries.fetch_top_results.client")
async def test_exact_label_name_returns_label_then_its_releases(mock_client):
    mock_client.search.return_value = _search_hits(LABEL, _track(9))
    mock_client.msearch.return_value = _children([_release(1), _release(2)])

    results = await fetch_top_results("  hot   CREATIONS ")

    assert results == [LABEL, _release(1), _release(2), _track(9)]


@pytest.mark.asyncio
@patch("app.routers.queries.fetch_top_results.client")
async def test_label_children_are_searched_by_label_id(mock_client):
    mock_client.search.return_value = _search_hits(LABEL)
    mock_client.msearch.return_value = _children([])

    await fetch_top_results("Hot Creations")

    kwargs = mock_client.msearch.call_args.kwargs
    assert kwargs["body"][0] == {}
    search = kwargs["body"][1]
    assert len(kwargs["body"]) == 2
    assert search["size"] == 7
    assert search["query"]["bool"]["filter"] == [
        {"term": {"type": "releases"}},
        {"term": {"label.id.keyword": "L1"}},
        {"term": {"is_visible": True}},
    ]
    assert search["sort"] == [
        {"release_date": {"order": "desc", "missing": "_last", "unmapped_type": "date"}}
    ]


@pytest.mark.asyncio
@patch("app.routers.queries.fetch_top_results.client")
async def test_artist_children_are_releases_and_tracks_by_artist_id(mock_client):
    mock_client.search.return_value = _search_hits(ARTIST)
    mock_client.msearch.return_value = _children(
        [_release(1), _release(2), _release(3)],
        [_track(1), _track(2), _track(3), _track(4)],
    )

    results = await fetch_top_results("Fusion")

    body = mock_client.msearch.call_args.kwargs["body"]
    releases_search, tracks_search = body[1], body[3]
    assert releases_search["size"] == 3
    assert tracks_search["size"] == 4
    assert {"term": {"artists.id.keyword": "A1"}} in (
        releases_search["query"]["bool"]["filter"]
    )
    assert tracks_search["sort"] == [{"popularity": {"order": "desc"}}]
    assert [d["id"] for d in results] == [
        "A1", "R1", "R2", "R3", "T1", "T2", "T3", "T4",
    ]  # fmt: skip


@pytest.mark.asyncio
@patch("app.routers.queries.fetch_top_results.client")
async def test_an_artist_leads_when_it_shares_an_exact_name_with_a_label(mock_client):
    mock_client.search.return_value = _search_hits(SAME_NAME_LABEL, ARTIST)
    mock_client.msearch.return_value = _children([], [])

    results = await fetch_top_results("fusion")

    assert results == [ARTIST, SAME_NAME_LABEL]
    assert "artists.id.keyword" in str(mock_client.msearch.call_args)


@pytest.mark.asyncio
@patch("app.routers.queries.fetch_top_results.client")
@pytest.mark.parametrize("query", ["Hot Crea", "Hot", "Hot Creations Anthem"])
async def test_a_partial_name_does_not_expand_children(mock_client, query):
    mock_client.search.return_value = _search_hits(LABEL, _track(1))

    results = await fetch_top_results(query)

    assert results == [LABEL, _track(1)]
    mock_client.msearch.assert_not_called()


@pytest.mark.asyncio
@patch("app.routers.queries.fetch_top_results.client")
async def test_a_playlist_or_release_with_the_query_name_is_not_a_lead(mock_client):
    playlist = {"id": "P1", "type": "playlists", "name": "Hot Creations"}
    mock_client.search.return_value = _search_hits(playlist)

    results = await fetch_top_results("Hot Creations")

    assert results == [playlist]
    mock_client.msearch.assert_not_called()


@pytest.mark.asyncio
@patch("app.routers.queries.fetch_top_results.client")
async def test_the_result_is_capped_at_eight_and_never_repeats_a_document(
    mock_client,
):
    others = [_track(n) for n in range(10, 20)]
    mock_client.search.return_value = _search_hits(LABEL, *others)
    mock_client.msearch.return_value = _children([_release(n) for n in range(1, 8)])

    results = await fetch_top_results("Hot Creations")

    assert len(results) == 8
    assert [d["id"] for d in results] == ["L1", *(f"R{n}" for n in range(1, 8))]

    mock_client.search.return_value = _search_hits(LABEL, _release(1))
    mock_client.msearch.return_value = _children([_release(1)])
    results = await fetch_top_results("Hot Creations")
    assert [d["id"] for d in results] == ["L1", "R1"]


@pytest.mark.asyncio
@patch("app.routers.queries.fetch_top_results.sentry_sdk")
@patch("app.routers.queries.fetch_top_results.client")
async def test_a_failed_child_lookup_returns_the_text_matches(mock_client, mock_sentry):
    error = RuntimeError("boom")
    mock_client.search.return_value = _search_hits(LABEL, _track(1))
    mock_client.msearch.side_effect = error

    results = await fetch_top_results("Hot Creations")

    assert results == [LABEL, _track(1)]
    mock_sentry.capture_exception.assert_called_once_with(error)


@pytest.mark.asyncio
@patch("app.routers.queries.fetch_top_results.sentry_sdk")
@patch("app.routers.queries.fetch_top_results.client")
async def test_an_msearch_item_error_is_treated_as_a_failed_lookup(
    mock_client, mock_sentry
):
    mock_client.search.return_value = _search_hits(LABEL)
    mock_client.msearch.return_value = {"responses": [{"error": {"type": "boom"}}]}

    results = await fetch_top_results("Hot Creations")

    assert results == [LABEL]
    mock_sentry.capture_exception.assert_called_once()
