from os import getenv

from app.utils import client

INDEX_NAME = getenv("OPENSEARCH_INDEX_NAME", "upfrontbeats")


async def fetch_tracks_results(query):
    response = client.search(
        index=INDEX_NAME,
        body={
            "size": 8,
            "query": {
                "bool": {
                    "must": [
                        {
                            "query_string": {
                                "query": f"*{query}*",
                            },
                        },
                    ],
                    "filter": [
                        {
                            "term": {
                                "type": "tracks",
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
