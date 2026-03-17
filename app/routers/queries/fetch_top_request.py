from os import getenv

from app.utils import client

INDEX_NAME = getenv("OPENSEARCH_INDEX_NAME", "upfrontbeats")


def fetch_top_request(query):
    response = client.search(
        index=INDEX_NAME,
        body={
            "size": 8,
            "query": {
                "bool": {
                    "must": [{"query_string": {"query": f"*{query}*"}}],
                    "should": [
                        {"match_phrase": {"name": {"query": query, "boost": 10}}},
                        {"term": {"name.keyword": {"value": query, "boost": 15}}},
                        {"match": {"type": {"query": "artists", "boost": 3}}},
                        {"match": {"type": {"query": "labels", "boost": 3}}},
                        {"match": {"type": {"query": "tracks", "boost": 1}}},
                        {"match": {"type": {"query": "releases", "boost": 1}}},
                        {"range": {"popularity": {"gte": 0, "boost": 3}}},
                    ],
                    "minimum_should_match": 1,
                }
            },
            "sort": [{"timestamp": {"order": "desc"}}],
        },
    )

    print(response)

    return response["hits"]["hits"][0]["_source"] if response["hits"]["hits"] else None
