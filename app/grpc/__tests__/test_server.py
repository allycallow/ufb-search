from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.grpc import search_pb2
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
async def test_create_index_includes_playlist_mapping():
    with patch("app.grpc.server.client") as mock_client:
        await SearchServicer().CreateIndex(MagicMock(), MagicMock())

    properties = mock_client.indices.create.call_args.kwargs["body"]["mappings"][
        "properties"
    ]
    assert properties["popularity"] == {"type": "integer"}
    assert properties["description"] == {"type": "text", "index": False}
    assert properties["id"] == {"type": "keyword"}
