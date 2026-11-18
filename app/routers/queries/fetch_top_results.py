import asyncio
import re
from os import getenv

import sentry_sdk

from app.routers.queries.name_match import (
    RESULT_FIELDS,
    name_match_query,
    visible_filter,
)
from app.utils import client, logger
from app.utils.metrics import search_lead_expansions_total, search_zero_results_total

INDEX_NAME = getenv("OPENSEARCH_INDEX_NAME", "upfrontbeats")

TOP_SIZE = 8
LABEL_RELEASE_QUOTA = 7
ARTIST_RELEASE_QUOTA = 3
ARTIST_TRACK_QUOTA = 4

# Releases and tracks link to their label and artists by id. These are the
# `.keyword` subfields of the dynamically mapped `label` and `artists` objects.
LABEL_ID_FIELD = "label.id.keyword"
ARTIST_ID_FIELD = "artists.id.keyword"

# When an artist and a label share an exact name, the earlier type leads.
LEAD_TYPE_PRIORITY: tuple[str, ...] = ("artists", "labels")

RELEASE_SORT: list[dict[str, object]] = [
    {"release_date": {"order": "desc", "missing": "_last", "unmapped_type": "date"}}
]
TRACK_SORT: list[dict[str, object]] = [{"popularity": {"order": "desc"}}]


async def fetch_top_results(query: str) -> list[dict[str, object]]:
    response = await asyncio.to_thread(
        client.search,
        index=INDEX_NAME,
        body={
            "_source": RESULT_FIELDS,
            "size": TOP_SIZE,
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

    lead = _find_lead(hits, query)
    if lead is None:
        return hits

    try:
        releases, tracks = await asyncio.to_thread(_fetch_children, lead)
    except Exception as e:
        logger.warning(
            "Failed to fetch children for search lead",
            extra={"query": query, "lead_id": lead["id"], "error": str(e)},
        )
        sentry_sdk.capture_exception(e)
        return hits

    lead_type = str(lead["type"])
    search_lead_expansions_total.labels(lead_type=lead_type).inc()
    logger.info(
        "Top search expanded a lead",
        extra={
            "query": query,
            "lead_type": lead_type,
            "lead_id": lead["id"],
            "releases": len(releases),
            "tracks": len(tracks),
        },
    )
    return _compose(lead, releases, tracks, hits)


def _normalise(text: str) -> str:
    return " ".join(text.split()).casefold()


def _words(text: str) -> list[str]:
    """Punctuation separates words, so "Rossi." is ["rossi"] but "A.D.A.M." is
    ["a", "d", "a", "m"], not ["adam"]."""
    return re.findall(r"\w+", text.casefold())


def _find_lead(hits: list[dict[str, object]], query: str) -> dict[str, object] | None:
    """The label or artist whose name has the same words as the query, if any.

    A name equal to the query as typed beats one that differs only by
    punctuation, then an artist beats a label.
    """
    wanted = _words(query)
    if not wanted:
        return None
    candidates = [
        hit
        for hit in hits
        if hit.get("type") in LEAD_TYPE_PRIORITY
        and hit.get("id")
        and isinstance(hit.get("name"), str)
        and _words(str(hit["name"])) == wanted
    ]
    if not candidates:
        return None
    lead = min(
        candidates,
        key=lambda hit: (
            _normalise(str(hit["name"])) != _normalise(query),
            LEAD_TYPE_PRIORITY.index(str(hit["type"])),
        ),
    )
    if _normalise(str(lead["name"])) != _normalise(query):
        logger.info(
            "Top search chose a lead that differs from the query by punctuation",
            extra={"query": query, "lead_id": lead["id"], "lead_name": lead["name"]},
        )
    return lead


def _child_search(
    link_field: str,
    lead_id: str,
    child_type: str,
    size: int,
    sort: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "_source": RESULT_FIELDS,
        "size": size,
        "query": {
            "bool": {
                "filter": [
                    {"term": {"type": child_type}},
                    {"term": {link_field: lead_id}},
                    {"term": {"is_visible": True}},
                ]
            }
        },
        "sort": sort,
    }


def _fetch_children(
    lead: dict[str, object],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """A label's releases, or an artist's releases and tracks, in one msearch."""
    lead_id = str(lead["id"])
    if lead["type"] == "labels":
        searches = [
            _child_search(
                LABEL_ID_FIELD, lead_id, "releases", LABEL_RELEASE_QUOTA, RELEASE_SORT
            )
        ]
    else:
        searches = [
            _child_search(
                ARTIST_ID_FIELD,
                lead_id,
                "releases",
                ARTIST_RELEASE_QUOTA,
                RELEASE_SORT,
            ),
            _child_search(
                ARTIST_ID_FIELD, lead_id, "tracks", ARTIST_TRACK_QUOTA, TRACK_SORT
            ),
        ]

    response = client.msearch(
        body=[part for search in searches for part in ({}, search)],
        index=INDEX_NAME,
    )

    results: list[list[dict[str, object]]] = []
    for item in response["responses"]:
        if "error" in item:
            raise RuntimeError(f"msearch request failed: {item['error']}")
        results.append([hit["_source"] for hit in item["hits"]["hits"]])

    return results[0], results[1] if len(results) > 1 else []


def _compose(
    lead: dict[str, object],
    releases: list[dict[str, object]],
    tracks: list[dict[str, object]],
    hits: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Lead, its releases, its tracks, then the other text matches, up to 8."""
    top = [lead, *releases, *tracks]
    used_ids = {document.get("id") for document in top}
    refill = [hit for hit in hits if hit.get("id") not in used_ids]
    return [*top, *refill][:TOP_SIZE]
