from os import getenv

import sentry_sdk
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator

# --- OpenTelemetry Imports ---
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# ------------------------------

from .routers import search_router

SENTRY_DSN = getenv("SENTRY_DSN", None)
STAGE = getenv("STAGE", "local")

sentry_sdk.init(dsn=SENTRY_DSN, send_default_pii=True, environment=STAGE)

app = FastAPI()


# --- OpenTelemetry Setup ---
def initialize_tracing(fastapi_app: FastAPI):
    try:
        # Service name as it will appear inside the Jaeger UI dropdown
        resource = Resource.create(
            attributes={"service.search": "fastapi-microservice"}
        )
        provider = TracerProvider(resource=resource)

        # Reads target Jaeger gRPC endpoint from environment variables (e.g., OTEL_EXPORTER_OTLP_ENDPOINT)
        processor = BatchSpanProcessor(OTLPSpanExporter())
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)

        # Instrument FastAPI (extracts trace context from inbound Django headers automatically)
        FastAPIInstrumentor.instrument_app(fastapi_app)
        print("OpenTelemetry tracing successfully initialized for FastAPI.")
    except Exception as e:
        print(f"Failed to initialize OpenTelemetry tracing: {e}")


# Trigger the tracking initialization
initialize_tracing(app)
# ----------------------------

# Prometheus setup (keeps metrics running cleanly alongside tracing)
Instrumentator().instrument(app).expose(app)


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
