import asyncio
import time
from unittest.mock import MagicMock, patch

import pytest

from app.routers.search import search

MODULES = [
    "fetch_artist_results",
    "fetch_labels_results",
    "fetch_playlist_results",
    "fetch_releases_results",
    "fetch_top_results",
    "fetch_tracks_results",
]
DELAY_SECONDS = 0.2


def _slow_search(**kwargs: object) -> dict[str, object]:
    time.sleep(DELAY_SECONDS)
    return {"hits": {"hits": []}}


@pytest.mark.asyncio
async def test_section_searches_run_at_the_same_time() -> None:
    clients = [MagicMock() for _ in MODULES]
    for mock_client in clients:
        mock_client.search.side_effect = _slow_search

    patches = [
        patch(f"app.routers.queries.{module}.client", mock_client)
        for module, mock_client in zip(MODULES, clients)
    ]
    for p in patches:
        p.start()
    try:
        started = time.perf_counter()
        await search(q="query")
        elapsed = time.perf_counter() - started
    finally:
        for p in patches:
            p.stop()

    # One after another would take len(MODULES) * DELAY_SECONDS (1.2s).
    assert elapsed < DELAY_SECONDS * 3


@pytest.mark.asyncio
async def test_a_search_does_not_block_the_event_loop() -> None:
    with patch("app.routers.queries.fetch_labels_results.client") as mock_client:
        mock_client.search.side_effect = _slow_search
        from app.routers.queries import fetch_labels_results

        ticks = 0

        async def tick() -> None:
            nonlocal ticks
            while True:
                await asyncio.sleep(0.01)
                ticks += 1

        ticker = asyncio.create_task(tick())
        await fetch_labels_results("query")
        ticker.cancel()

    assert ticks >= 5
