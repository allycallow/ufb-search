import time
from os import getenv

from opensearchpy.exceptions import TransportError

from app.utils import client, logger

INDEX_NAME = getenv("OPENSEARCH_INDEX_NAME", "upfrontbeats")

SEED_DOCUMENTS: list[dict[str, str | None]] = [
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
            },
        )

    for document in SEED_DOCUMENTS:
        logger.info("Seeding document", extra={"document_id": document["id"]})
        client.index(index=INDEX_NAME, id=document["id"], body=document)


if __name__ == "__main__":
    seed()
