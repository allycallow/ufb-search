from os import getenv
from app.utils import client

INDEX_NAME = getenv("OPENSEARCH_INDEX_NAME", "upfrontbeats")


async def fetch_releases_results(query):
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
                                "type": "releases",
                            },
                        },
                    ],
                },
            },
            "sort": ["_score"],
        },
    )

    return response["hits"]["hits"] if response["hits"]["hits"] else []
