from os import getenv

from app.routers.queries.name_match import RESULT_FIELDS, name_match_query
from app.utils import client

INDEX_NAME = getenv("OPENSEARCH_INDEX_NAME", "upfrontbeats")


async def fetch_artist_results(query: str) -> list[dict[str, object]]:
    response = client.search(
        index=INDEX_NAME,
        body={
            "_source": RESULT_FIELDS,
            "size": 8,
            "query": {
                "bool": {
                    "must": [name_match_query(query)],
                    "filter": [{"term": {"type": "artists"}}],
                    "should": [
                        # Boost exact phrase match
                        {"match_phrase": {"name": {"query": query, "boost": 10}}},
                        # Boost exact term match if a keyword field exists
                        {"term": {"name.keyword": {"value": query, "boost": 15}}},
                    ],
                    "minimum_should_match": 0,  # Changed to 0 since 'must' is present
                }
            },
        },
    )

    return (
        list(map(lambda hit: hit["_source"], response["hits"]["hits"]))
        if response["hits"]["hits"]
        else []
    )
