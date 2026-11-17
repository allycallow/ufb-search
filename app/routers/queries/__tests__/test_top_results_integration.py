"""Runs fetch_top_results against a real OpenSearch.

Skipped unless OPENSEARCH_INTEGRATION=1. Point OPENSEARCH_INTEGRATION_URL at a
cluster without the security plugin, for example:

    docker run --rm -p 9201:9200 -e discovery.type=single-node \
        -e DISABLE_SECURITY_PLUGIN=true -e DISABLE_INSTALL_DEMO_CONFIG=true \
        opensearchproject/opensearch:latest
    OPENSEARCH_INTEGRATION=1 OPENSEARCH_INTEGRATION_URL=http://localhost:9201 \
        pipenv run tests app/routers/queries/__tests__/test_top_results_integration.py
"""

from collections.abc import Iterator
from os import getenv
from unittest.mock import patch
from uuid import uuid4

import pytest
from opensearchpy import OpenSearch

from app.routers.queries.fetch_top_results import fetch_top_results

pytestmark = pytest.mark.skipif(
    getenv("OPENSEARCH_INTEGRATION") != "1",
    reason="set OPENSEARCH_INTEGRATION=1 to run against a real OpenSearch",
)

HOT_CREATIONS = {"id": "label-hc", "name": "Hot Creations"}
FUSION_LABEL = {"id": "label-fusion", "name": "Fusion"}
FUSION_ARTIST = {"id": "artist-fusion", "name": "Fusion"}


def _release(
    id: str, title: str, date: str | None, label: dict[str, str], visible: bool = True
) -> dict[str, object]:
    return {
        "id": id,
        "type": "releases",
        "title": title,
        "release_date": date,
        "is_visible": visible,
        "label": label,
        "artists": [],
    }


def _track(
    id: str, title: str, popularity: int, label: dict[str, str]
) -> dict[str, object]:
    return {
        "id": id,
        "type": "tracks",
        "title": title,
        "popularity": popularity,
        "is_visible": True,
        "label": label,
        "artists": [],
    }


DOCUMENTS: list[dict[str, object]] = [
    {"type": "labels", "popularity": 50, **HOT_CREATIONS},
    {"id": "artist-hs82", "type": "artists", "name": "Hot Since 82", "popularity": 90},
    {"id": "artist-hn", "type": "artists", "name": "Hot Natured", "popularity": 60},
    _release("r-new", "Double Up", "2024-05-01", HOT_CREATIONS),
    _release("r-old", "Bappi", "2023-01-01", HOT_CREATIONS),
    _release("r-undated", "Old One", None, HOT_CREATIONS),
    _release("r-hidden", "Hidden", "2025-01-01", HOT_CREATIONS, visible=False),
    _release("r-other", "Elsewhere", "2025-02-01", {"id": "label-x", "name": "X"}),
    _track("t-anthem", "Hot Creations Anthem", 5, HOT_CREATIONS),
    {"type": "labels", "popularity": 10, **FUSION_LABEL},
    {"type": "artists", "popularity": 20, **FUSION_ARTIST},
    *[
        {
            "id": f"fr-{n}",
            "type": "releases",
            "title": f"Fusion Release {n}",
            "release_date": f"2024-0{n}-01",
            "is_visible": True,
            "artists": [FUSION_ARTIST],
        }
        for n in range(1, 5)
    ],
    *[
        {
            "id": f"ft-{n}",
            "type": "tracks",
            "title": f"Fusion Track {n}",
            "popularity": n,
            "is_visible": True,
            "artists": [FUSION_ARTIST],
        }
        for n in range(1, 6)
    ],
]


@pytest.fixture(scope="module")
def index_name() -> Iterator[str]:
    name = f"top-results-it-{uuid4().hex[:8]}"
    os_client = OpenSearch(hosts=[getenv("OPENSEARCH_INTEGRATION_URL", "")])
    os_client.indices.create(
        index=name,
        body={"mappings": {"properties": {"popularity": {"type": "integer"}}}},
    )
    for document in DOCUMENTS:
        os_client.index(index=name, id=str(document["id"]), body=document)
    os_client.indices.refresh(index=name)

    with (
        patch("app.routers.queries.fetch_top_results.client", os_client),
        patch("app.routers.queries.fetch_top_results.INDEX_NAME", name),
    ):
        yield name

    os_client.indices.delete(index=name)


def _labels(results: list[dict[str, object]]) -> list[str]:
    return [str(d.get("name") or d.get("title")) for d in results]


@pytest.mark.asyncio
async def test_full_label_name_returns_label_then_its_releases(index_name: str) -> None:
    results = await fetch_top_results("Hot Creations")

    assert _labels(results) == [
        "Hot Creations",
        "Double Up",
        "Bappi",
        "Old One",
        "Hot Creations Anthem",
    ]


@pytest.mark.asyncio
async def test_a_partial_label_name_returns_text_matches_only(index_name: str) -> None:
    results = await fetch_top_results("Hot Crea")

    assert set(_labels(results)) == {"Hot Creations", "Hot Creations Anthem"}


@pytest.mark.asyncio
async def test_one_word_returns_every_name_starting_with_it(index_name: str) -> None:
    results = await fetch_top_results("Hot")

    assert set(_labels(results)) == {
        "Hot Creations",
        "Hot Since 82",
        "Hot Natured",
        "Hot Creations Anthem",
    }


@pytest.mark.asyncio
async def test_same_name_artist_leads_with_three_releases_and_four_tracks(
    index_name: str,
) -> None:
    results = await fetch_top_results("fusion")

    assert [d["type"] for d in results] == ["artists"] + ["releases"] * 3 + [
        "tracks"
    ] * 4
    assert results[0]["id"] == "artist-fusion"
    assert [d["id"] for d in results[1:4]] == ["fr-4", "fr-3", "fr-2"]
    assert [d["id"] for d in results[4:]] == ["ft-5", "ft-4", "ft-3", "ft-2"]


@pytest.mark.asyncio
async def test_results_never_exceed_eight(index_name: str) -> None:
    for query in ["Hot", "Fusion", "Hot Creations", "e"]:
        assert len(await fetch_top_results(query)) <= 8
