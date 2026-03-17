from os import getenv

import sentry_sdk
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from .routers import search_router

SENTRY_DSN = getenv("SENTRY_DSN", None)
STAGE = getenv("STAGE", "local")

sentry_sdk.init(dsn=SENTRY_DSN, send_default_pii=True, environment=STAGE)

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


@app.get("/sentry-debug")
async def trigger_error():
    raise Exception("This is a test exception for Sentry debugging")


app.include_router(search_router, prefix="/api/search", tags=["search"])
