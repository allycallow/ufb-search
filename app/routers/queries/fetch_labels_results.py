from os import getenv

from app.routers.queries.name_match import name_match_query
from app.utils import client

INDEX_NAME = getenv("OPENSEARCH_INDEX_NAME", "upfrontbeats")


async def fetch_labels_results(query: str) -> list[dict[str, object]]:
    response = client.search(
        index=INDEX_NAME,
        body={
            "size": 8,
            "query": {
                "bool": {
                    "must": [name_match_query(query)],
                    "filter": [
                        {
                            "term": {
                                "type": "labels",
                            },
                        },
                    ],
                },
            },
        },
    )

    return (
        list(map(lambda hit: hit["_source"], response["hits"]["hits"]))
        if response["hits"]["hits"]
        else []
    )
