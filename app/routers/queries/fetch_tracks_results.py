from os import getenv

from app.routers.queries.name_match import RESULT_FIELDS, name_match_query
from app.utils import client

INDEX_NAME = getenv("OPENSEARCH_INDEX_NAME", "upfrontbeats")


async def fetch_tracks_results(query: str) -> list[dict[str, object]]:
    response = client.search(
        index=INDEX_NAME,
        body={
            "_source": RESULT_FIELDS,
            "size": 8,
            "query": {
                "bool": {
                    "must": [name_match_query(query)],
                    "filter": [
                        {
                            "term": {
                                "type": "tracks",
                            },
                        },
                        {
                            "term": {
                                "is_visible": True,
                            },
                        },
                    ],
                    "should": [
                        {
                            "range": {
                                "popularity": {
                                    "boost": 3,
                                    "gte": 0,
                                },
                            },
                        },
                    ],
                    "minimum_should_match": 1,
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
