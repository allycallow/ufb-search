from collections.abc import Awaitable, Callable
from unittest.mock import MagicMock, patch

import pytest

from app.routers.queries import (
    fetch_artist_results,
    fetch_labels_results,
    fetch_playlist_results,
    fetch_releases_results,
    fetch_suggestions_results,
    fetch_top_results,
    fetch_tracks_results,
)

FETCHERS: list[tuple[str, Callable[[str], Awaitable[object]]]] = [
    ("fetch_artist_results", fetch_artist_results),
    ("fetch_labels_results", fetch_labels_results),
    ("fetch_playlist_results", fetch_playlist_results),
    ("fetch_releases_results", fetch_releases_results),
    ("fetch_suggestions_results", fetch_suggestions_results),
    ("fetch_top_results", fetch_top_results),
    ("fetch_tracks_results", fetch_tracks_results),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(("module", "fetch"), FETCHERS)
async def test_only_result_fields_are_returned(
    module: str, fetch: Callable[[str], Awaitable[object]]
) -> None:
    with patch(f"app.routers.queries.{module}.client") as mock_client:
        mock_client.search.return_value = {"hits": {"hits": []}}
        await fetch("query")

    body = mock_client.search.call_args.kwargs["body"]
    assert body["_source"] == ["id", "type", "name", "title"]


@pytest.mark.asyncio
@patch("app.routers.queries.fetch_top_results.client")
async def test_lead_children_only_return_result_fields(mock_client: MagicMock) -> None:
    label = {"id": "L1", "type": "labels", "name": "Hot Creations"}
    mock_client.search.return_value = {"hits": {"hits": [{"_source": label}]}}
    mock_client.msearch.return_value = {"responses": [{"hits": {"hits": []}}]}

    await fetch_top_results("Hot Creations")

    child_search = mock_client.msearch.call_args.kwargs["body"][1]
    assert child_search["_source"] == ["id", "type", "name", "title"]
