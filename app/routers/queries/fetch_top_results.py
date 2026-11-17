from os import getenv

from app.routers.queries.name_match import name_match_query, visible_filter
from app.utils import client, logger
from app.utils.metrics import search_zero_results_total

INDEX_NAME = getenv("OPENSEARCH_INDEX_NAME", "upfrontbeats")


async def fetch_top_results(query: str) -> list[dict[str, object]]:
    response = client.search(
        index=INDEX_NAME,
        body={
            "size": 8,
            "query": {
                "function_score": {
                    "query": {
                        "bool": {
                            "must": [name_match_query(query)],
                            "should": [
                                {"match": {"type": {"query": "artists", "boost": 3}}},
                                {"match": {"type": {"query": "labels", "boost": 3}}},
                                {"match": {"type": {"query": "tracks", "boost": 1}}},
                                {"match": {"type": {"query": "releases", "boost": 1}}},
                                {"match": {"type": {"query": "playlists", "boost": 1}}},
                            ],
                            "filter": [visible_filter()],
                        }
                    },
                    "field_value_factor": {
                        "field": "popularity",
                        "modifier": "log1p",
                        "missing": 1,
                    },
                    "boost_mode": "sum",
                }
            },
        },
    )

    hits: list[dict[str, object]] = [hit["_source"] for hit in response["hits"]["hits"]]
    if not hits:
        search_zero_results_total.labels(endpoint="top").inc()
        logger.info("Top search returned no results", extra={"query": query})
    return hits
