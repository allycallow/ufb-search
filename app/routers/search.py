import asyncio
from http import HTTPStatus
from os import getenv

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import verify_api_key
from app.routers.queries import (
    fetch_artist_results,
    fetch_labels_results,
    fetch_releases_results,
    fetch_top_results,
    fetch_tracks_results,
)
from app.utils import logger
from app.utils.metrics import search_queries_total, search_terms_total
from app.utils.opensearch import client

router = APIRouter(dependencies=[Depends(verify_api_key)])

INDEX = getenv("OPENSEARCH_INDEX_NAME", "upfrontbeats")


@router.get("/", description="Search query", tags=["search"])
async def search(q: str = Query(..., description="Search query")):
    logger.info("Search query received", extra={"query": q})

    if not q:
        logger.warning("Empty search query received")
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail="Query parameter 'q' is required"
        )

    decode = q.encode("utf-8").decode("unicode_escape")

    search_queries_total.labels(endpoint="general").inc()
    search_terms_total.labels(term=decode.lower().strip()).inc()

    top_results, artist_results, labels_results, releases_results, tracks_results = (
        await asyncio.gather(
            fetch_top_results(decode),
            fetch_artist_results(decode),
            fetch_labels_results(decode),
            fetch_releases_results(decode),
            fetch_tracks_results(decode),
        )
    )

    return {
        "results": {
            "top": top_results,
            "artists": artist_results,
            "labels": labels_results,
            "releases": releases_results,
            "tracks": tracks_results,
            "playlists": [],
        }
    }


@router.get("/artists", description="Search artists", tags=["search"])
async def search_artists(q: str = Query(..., description="Search query")):
    logger.info("Artist search query received", extra={"query": q})

    if not q:
        logger.warning("Empty search query received")
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail="Query parameter 'q' is required"
        )

    decode = q.encode("utf-8").decode("unicode_escape")

    search_queries_total.labels(endpoint="artists").inc()
    search_terms_total.labels(term=decode.lower().strip()).inc()

    results = await fetch_artist_results(decode)

    return {"results": results}


@router.get("/labels", description="Search labels", tags=["search"])
async def search_labels(q: str = Query(..., description="Search query")):
    logger.info("Label search query received", extra={"query": q})

    if not q:
        logger.warning("Empty search query received")
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail="Query parameter 'q' is required"
        )

    decode = q.encode("utf-8").decode("unicode_escape")

    search_queries_total.labels(endpoint="labels").inc()
    search_terms_total.labels(term=decode.lower().strip()).inc()

    results = await fetch_labels_results(decode)

    return {"results": results}


@router.post(
    "/create-index",
    description="Create index",
    tags=["search"],
)
async def create_index():
    logger.info("Creating index")

    client.indices.create(
        index=INDEX,
        body={
            "settings": {
                "index": {
                    "number_of_shards": 1,
                    "number_of_replicas": 0,
                },
            },
            "mappings": {
                "properties": {
                    "popularity": {"type": "integer"},
                },
            },
        },
    )

    logger.info("Index created successfully")

    return {"success": True}


@router.post(
    "/delete-index",
    description="Delete index",
    tags=["search"],
)
async def delete_index():
    logger.info("Deleting index")

    client.indices.delete_index(
        index=INDEX,
    )

    logger.info("Index deleted successfully")

    return {"success": True}
