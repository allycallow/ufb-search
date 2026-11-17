import time
from os import getenv

from opensearchpy.exceptions import TransportError

from app.utils import client, logger
from app.utils.index_mappings import INDEX_PROPERTIES

INDEX_NAME = getenv("OPENSEARCH_INDEX_NAME", "upfrontbeats")

SEED_DOCUMENTS: list[dict[str, object]] = [
    {
        "id": "87ffaaec-3042-43c7-9890-5cf845aaf40c",
        "created_at": "2023-12-15T18:08:57.211246Z",
        "updated_at": "2025-10-13T20:53:11.767559Z",
        "name": "Hot Creations",
        "slug": "hot-creations",
        "biography": None,
        "copyright_copy": "(C) 2025 Hot Creations",
        "main_image": "https://cdn.upfrontbeats.com/images/main/hot-creations.jpg",
        "background_image": None,
        "type": "labels",
        "popularity": 50,
    },
    {
        "id": "a1000000-0000-4000-8000-000000000001",
        "name": "Hot Since 82",
        "slug": "hot-since-82",
        "type": "artists",
        "popularity": 90,
    },
    {
        "id": "a1000000-0000-4000-8000-000000000002",
        "name": "Hot Natured",
        "slug": "hot-natured",
        "type": "artists",
        "popularity": 60,
    },
    {
        "id": "a1000000-0000-4000-8000-000000000003",
        "name": "Ronnie Spiteri",
        "slug": "ronnie-spiteri",
        "type": "artists",
        "popularity": 40,
    },
    {
        "id": "b1000000-0000-4000-8000-000000000001",
        "title": "Double Up",
        "slug": "double-up",
        "type": "releases",
        "release_date": "2024-05-03",
        "is_visible": True,
        "label": {
            "id": "87ffaaec-3042-43c7-9890-5cf845aaf40c",
            "name": "Hot Creations",
        },
        "artists": [
            {"id": "a1000000-0000-4000-8000-000000000003", "name": "Ronnie Spiteri"}
        ],
    },
    {
        "id": "b1000000-0000-4000-8000-000000000002",
        "title": "Bappi",
        "slug": "bappi",
        "type": "releases",
        "release_date": "2023-09-15",
        "is_visible": True,
        "label": {
            "id": "87ffaaec-3042-43c7-9890-5cf845aaf40c",
            "name": "Hot Creations",
        },
        "artists": [],
    },
    {
        "id": "c1000000-0000-4000-8000-000000000001",
        "title": "Double Up",
        "slug": "double-up-track",
        "type": "tracks",
        "popularity": 70,
        "is_visible": True,
        "label": {
            "id": "87ffaaec-3042-43c7-9890-5cf845aaf40c",
            "name": "Hot Creations",
        },
        "release": {"id": "b1000000-0000-4000-8000-000000000001", "title": "Double Up"},
        "artists": [
            {"id": "a1000000-0000-4000-8000-000000000003", "name": "Ronnie Spiteri"}
        ],
    },
    {
        "id": "5b1f0d2e-7c0a-4b64-9d3e-2f8a1c6e9a10",
        "name": "Late Night House",
        "sub_title": "After hours",
        "description": "Deep and warm house for the small hours.",
        "private": False,
        "colour": "#1a1a2e",
        "artwork_url": None,
        "hero_image_url": None,
        "created_by_id": None,
        "type": "playlists",
    },
]


def wait_for_opensearch(retries: int = 30, delay_seconds: float = 2.0) -> None:
    for attempt in range(1, retries + 1):
        try:
            client.cluster.health()
            return
        except TransportError:
            logger.info(
                "Waiting for OpenSearch to be available",
                extra={"attempt": attempt, "retries": retries},
            )
            time.sleep(delay_seconds)

    raise RuntimeError(f"OpenSearch not available after {retries} attempts")


def seed() -> None:
    wait_for_opensearch()

    if not client.indices.exists(index=INDEX_NAME):
        logger.info("Creating index", extra={"index": INDEX_NAME})
        client.indices.create(
            index=INDEX_NAME,
            body={
                "settings": {
                    "index": {
                        "number_of_shards": 1,
                        "number_of_replicas": 0,
                    },
                },
                "mappings": {
                    "properties": INDEX_PROPERTIES,
                },
            },
        )

    for document in SEED_DOCUMENTS:
        logger.info("Seeding document", extra={"document_id": document["id"]})
        client.index(index=INDEX_NAME, id=document["id"], body=document)


if __name__ == "__main__":
    seed()
