from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.grpc import search_pb2, search_pb2_grpc
from app.grpc.server import SearchServicer


@pytest.mark.asyncio
async def test_search_returns_playlists():
    with (
        patch("app.grpc.server.fetch_top_results", new_callable=AsyncMock) as top,
        patch("app.grpc.server.fetch_artist_results", new_callable=AsyncMock) as a,
        patch("app.grpc.server.fetch_labels_results", new_callable=AsyncMock) as lb,
        patch("app.grpc.server.fetch_releases_results", new_callable=AsyncMock) as r,
        patch("app.grpc.server.fetch_tracks_results", new_callable=AsyncMock) as t,
        patch(
            "app.grpc.server.fetch_playlist_results", new_callable=AsyncMock
        ) as playlists,
    ):
        for mock in (top, a, lb, r, t):
            mock.return_value = []
        playlists.return_value = [{"id": "1", "name": "Late Night House"}]

        response = await SearchServicer().Search(
            search_pb2.SearchRequest(query="late night"), MagicMock()
        )

    playlists.assert_called_once_with("late night")
    assert [dict(p) for p in response.playlists] == [
        {"id": "1", "name": "Late Night House"}
    ]


@pytest.mark.asyncio
async def test_search_passes_an_accented_query_unchanged():
    with (
        patch("app.grpc.server.fetch_top_results", new_callable=AsyncMock) as top,
        patch("app.grpc.server.fetch_artist_results", new_callable=AsyncMock) as a,
        patch("app.grpc.server.fetch_labels_results", new_callable=AsyncMock) as lb,
        patch("app.grpc.server.fetch_releases_results", new_callable=AsyncMock) as r,
        patch("app.grpc.server.fetch_tracks_results", new_callable=AsyncMock) as t,
        patch("app.grpc.server.fetch_playlist_results", new_callable=AsyncMock) as p,
    ):
        for mock in (top, a, lb, r, t, p):
            mock.return_value = []

        await SearchServicer().Search(
            search_pb2.SearchRequest(query="Âme"), MagicMock()
        )

    top.assert_called_once_with("Âme")


def test_index_rpcs_are_not_implemented():
    base = search_pb2_grpc.SearchServiceServicer
    assert SearchServicer.CreateIndex is base.CreateIndex
    assert SearchServicer.DeleteIndex is base.DeleteIndex
