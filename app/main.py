from fastapi import FastAPI

from .routers import search_router

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}


app.include_router(search_router, prefix="/api/search", tags=["search"])
