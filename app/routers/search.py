from http import HTTPStatus

from fastapi import APIRouter, Depends, Query

from app.auth import verify_api_key

router = APIRouter(dependencies=[Depends(verify_api_key)])


@router.get("/")
async def search(q: str = Query(..., description="Search query"), tags=["search"]):
    results = [
        {"id": 1, "title": "Result 1", "query": q},
        {"id": 2, "title": "Result 2", "query": q},
    ]
    return {"results": results}


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
