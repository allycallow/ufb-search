from os import getenv

from app.utils import client

INDEX_NAME = getenv("OPENSEARCH_INDEX_NAME", "upfrontbeats")


async def fetch_artist_results(query):
    response = client.search(
        index=INDEX_NAME,
        body={
            "size": 8,
            "query": {
                "bool": {
                    "must": [{"query_string": {"query": f"*{query}*"}}],
                    "should": [
                        # Boost exact phrase match
                        {"match_phrase": {"name": {"query": query, "boost": 10}}},
                        # Boost exact term match if a keyword field exists
                        {"term": {"name.keyword": {"value": query, "boost": 15}}},
                        # Boost by type
                        {"match": {"type": {"query": "artists", "boost": 3}}},
                        {"match": {"type": {"query": "labels", "boost": 3}}},
                        {"match": {"type": {"query": "tracks", "boost": 1}}},
                        {"match": {"type": {"query": "releases", "boost": 1}}},
                        # Boost popular entries
                        {"range": {"popularity": {"gte": 0, "boost": 3}}},
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
