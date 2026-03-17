from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from .routers import search_router

app = FastAPI()


@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail,
            "statusCode": exc.status_code,
        },
    )


@app.get("/")
async def root():
    return {"message": "Hello World"}


app.include_router(search_router, prefix="/api/search", tags=["search"])
