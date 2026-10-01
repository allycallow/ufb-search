from os import getenv

from app.utils import client

INDEX_NAME = getenv("OPENSEARCH_INDEX_NAME", "upfrontbeats")


async def fetch_suggestions_results(query: str) -> list[dict[str, str | int | bool | None]]:
    response = client.search(
        index=INDEX_NAME,
        body={
            "size": 10,
            "query": {
                "bool": {
                    "must": [
                        {"match_phrase_prefix": {"name": {"query": query}}},
                    ],
                    "filter": [
                        {
                            "bool": {
                                "should": [
                                    {
                                        "bool": {
                                            "must_not": {
                                                "terms": {
                                                    "type": ["releases", "tracks"],
                                                },
                                            },
                                        },
                                    },
                                    {
                                        "term": {
                                            "is_visible": True,
                                        },
                                    },
                                ],
                                "minimum_should_match": 1,
                            },
                        },
                    ],
                },
            },
            "sort": ["_score", {"popularity": "desc"}],
        },
    )

    return (
        list(map(lambda hit: hit["_source"], response["hits"]["hits"]))
        if response["hits"]["hits"]
        else []
    )
