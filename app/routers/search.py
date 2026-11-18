import asyncio
from http import HTTPStatus

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import verify_api_key
from app.routers.queries import (
    fetch_artist_results,
    fetch_labels_results,
    fetch_playlist_results,
    fetch_releases_results,
    fetch_suggestions_results,
    fetch_top_results,
    fetch_tracks_results,
)
from app.utils import logger
from app.utils.metrics import search_queries_total

router = APIRouter(dependencies=[Depends(verify_api_key)])


@router.get("/", description="Search query", tags=["search"])
async def search(q: str = Query(..., description="Search query")):
    logger.info("Search query received", extra={"query": q})

    if not q:
        logger.warning("Empty search query received")
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail="Query parameter 'q' is required"
        )

    search_queries_total.labels(endpoint="general").inc()

    (
        top_results,
        artist_results,
        labels_results,
        releases_results,
        tracks_results,
        playlist_results,
    ) = await asyncio.gather(
        fetch_top_results(q),
        fetch_artist_results(q),
        fetch_labels_results(q),
        fetch_releases_results(q),
        fetch_tracks_results(q),
        fetch_playlist_results(q),
    )

    return {
        "results": {
            "top": top_results,
            "artists": artist_results,
            "labels": labels_results,
            "releases": releases_results,
            "tracks": tracks_results,
            "playlists": playlist_results,
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

    search_queries_total.labels(endpoint="artists").inc()

    results = await fetch_artist_results(q)

    return {"results": results}


@router.get("/labels", description="Search labels", tags=["search"])
async def search_labels(q: str = Query(..., description="Search query")):
    logger.info("Label search query received", extra={"query": q})

    if not q:
        logger.warning("Empty search query received")
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail="Query parameter 'q' is required"
        )

    search_queries_total.labels(endpoint="labels").inc()

    results = await fetch_labels_results(q)

    return {"results": results}


@router.get("/playlists", description="Search playlists", tags=["search"])
async def search_playlists(q: str = Query(..., description="Search query")):
    logger.info("Playlist search query received", extra={"query": q})

    if not q:
        logger.warning("Empty search query received")
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail="Query parameter 'q' is required"
        )

    search_queries_total.labels(endpoint="playlists").inc()

    results = await fetch_playlist_results(q)

    return {"results": results}


@router.get("/suggestions", description="Search suggestions", tags=["search"])
async def search_suggestions(q: str = Query(..., description="Search query")):
    logger.info("Suggestions query received", extra={"query": q})

    if not q:
        logger.warning("Empty search query received")
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail="Query parameter 'q' is required"
        )

    search_queries_total.labels(endpoint="suggestions").inc()

    results = await fetch_suggestions_results(q)

    return {"results": results}
