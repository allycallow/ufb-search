import asyncio
from http import HTTPStatus
from os import getenv
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.auth import verify_api_key
from app.routers.get_item import get_item_details
from app.routers.queries import (fetch_artist_results, fetch_labels_results,
                                 fetch_releases_results, fetch_top_results,
                                 fetch_tracks_results)
from app.utils import logger
from app.utils.opensearch import client

router = APIRouter(dependencies=[Depends(verify_api_key)])

INDEX = getenv("OPENSEARCH_INDEX_NAME", "upfrontbeats")


class Detail(BaseModel):
    id: str


class Event(BaseModel):
    version: str
    id: str
    detail_type: str = Field(..., alias="detail-type")
    source: str
    account: str
    time: str
    region: str
    resources: List
    detail: Detail


def fetch_type(type: str):
    if type == "artist":
        return "artists"
    elif type == "label":
        return "labels"
    elif type == "release":
        return "releases"
    elif type == "track":
        return "tracks"
    else:
        raise ValueError(f"Unknown type: {type}")


@router.get("/")
async def search(q: str = Query(..., description="Search query"), tags=["search"]):
    logger.info("Search query received", extra={"query": q})

    if not q:
        logger.warning("Empty search query received")
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail="Query parameter 'q' is required"
        )

    decode = q.encode("utf-8").decode("unicode_escape")

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


@router.get("/{item_id}")
async def get_search_item(item_id: str):
    return {"id": item_id, "title": f"Result {item_id}", "query": "example query"}


@router.post("/add", description="Add item to index", tags=["custom"])
async def create_search_item(event: Event):
    logger.info("Creating search item", extra={"event": event.model_dump()})

    type = fetch_type(event.detail_type.split(".")[0].lower())

    response = get_item_details(event.detail.id, type)

    client.index(
        index=INDEX,
        id=event.detail.id,
        body={**response, "type": type},
    )

    logger.info("Search item created successfully", extra={"item_id": event.detail.id})

    return {"success": True}


@router.put("/update", description="Update item to index", tags=["custom"])
async def update_search_item(event: Event):
    logger.info("Updating search item", extra={"event": event.model_dump()})

    type = fetch_type(event.detail_type.split(".")[0].lower())

    response = get_item_details(event.detail.id, type)

    client.update(
        index=INDEX,
        id=event.detail.id,
        body={
            "doc": {**response, "type": type},
            "doc_as_upsert": True,
        },
    )

    logger.info("Search item updated successfully", extra={"item_id": event.detail.id})

    return {"success": True}


@router.put("/delete", description="Delete item from index", tags=["custom"])
async def delete_search_item(event: Event):
    logger.info("Deleting search item", extra={"event": event.model_dump()})

    client.update(index=INDEX, id=event.detail.id)

    logger.info("Search item updated successfully", extra={"item_id": event.detail.id})

    return {"success": True}


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
