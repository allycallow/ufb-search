import asyncio
from http import HTTPStatus
from os import getenv

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import verify_api_key
from app.routers.queries import (
    fetch_top_results,
    fetch_artist_results,
    fetch_labels_results,
    fetch_releases_results,
    fetch_tracks_results,
)
from app.utils import logger
from app.utils.opensearch import client

router = APIRouter(dependencies=[Depends(verify_api_key)])

INDEX = getenv("OPENSEARCH_INDEX_NAME", "upfrontbeats")


@router.get("/")
async def search(q: str = Query(..., description="Search query"), tags=["search"]):
    logger.info("Search query received", extra={"query": q})

    if not q:
        logger.warning("Empty search query received")
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail="Query parameter 'q' is required"
        )

    top_results, artist_results, labels_results, releases_results, tracks_results = (
        await asyncio.gather(
            fetch_top_results(q),
            fetch_artist_results(q),
            fetch_labels_results(q),
            fetch_releases_results(q),
            fetch_tracks_results(q),
        )
    )

    print("--")
    print(top_results)
    print(artist_results)
    print(labels_results)
    print(releases_results)
    print(tracks_results)
    print("--")

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


@router.get("/{item_id}")
async def get_search_item(item_id: str):
    return {"id": item_id, "title": f"Result {item_id}", "query": "example query"}


@router.put(
    "/{item_id}",
    tags=["custom"],
    responses={HTTPStatus.FORBIDDEN.value: {"description": "Operation forbidden"}},
)
async def update_search_item(item_id: str):
    return {"item_id": item_id, "name": "The great Plumbus"}


@router.post("/")
async def create_search_item(
    q: str = Query(..., description="Search query"), tags=["search"]
):
    results = [
        {"id": 1, "title": "Result 1", "query": q},
        {"id": 2, "title": "Result 2", "query": q},
    ]

    return {"results": results}


@router.delete(
    "/{item_id}",
    tags=["search"],
    responses={HTTPStatus.FORBIDDEN.value: {"description": "Operation forbidden"}},
)
async def delete_search_item(item_id: str):
    return {"item_id": item_id, "name": "The great Plumbus"}


@router.post("/create-index")
async def create_index(
    description="Create index",
    tags=["search"],
):
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
        },
    )

    logger.info("Index created successfully")

    return {"success": True}


@router.post("/delete-index")
async def delete_index(
    description="Delete index",
    tags=["search"],
):
    logger.info("Deleting index")

    client.indices.delete_index(
        index=INDEX,
    )

    logger.info("Index deleted successfully")

    return {"success": True}
