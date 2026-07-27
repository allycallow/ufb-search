import time

import grpc

from app.auth import API_KEY
from app.utils.metrics import grpc_request_duration_seconds, grpc_requests_total


class ApiKeyInterceptor(grpc.aio.ServerInterceptor):
    async def intercept_service(self, continuation, handler_call_details):
        metadata = dict(handler_call_details.invocation_metadata)
        api_key = metadata.get("x-api-key")

        if not api_key or api_key != API_KEY:

            async def deny(request, context):
                await context.abort(
                    grpc.StatusCode.UNAUTHENTICATED, "Missing or invalid API key"
                )

            return grpc.unary_unary_rpc_method_handler(deny)

        return await continuation(handler_call_details)


class PrometheusServerInterceptor(grpc.aio.ServerInterceptor):
    """Records request count and latency for every unary gRPC call."""

    async def intercept_service(self, continuation, handler_call_details):
        handler = await continuation(handler_call_details)
        if handler is None or handler.unary_unary is None:
            return handler

        method = handler_call_details.method
        original_behavior = handler.unary_unary

        async def instrumented_unary_unary(request, context):
            start = time.perf_counter()
            code = grpc.StatusCode.UNKNOWN
            try:
                response = await original_behavior(request, context)
                code = context.code() or grpc.StatusCode.OK
                return response
            except grpc.aio.AbortError:
                code = context.code() or grpc.StatusCode.UNKNOWN
                raise
            finally:
                grpc_request_duration_seconds.labels(grpc_method=method).observe(
                    time.perf_counter() - start
                )
                grpc_requests_total.labels(
                    grpc_method=method, grpc_code=code.name
                ).inc()

        return grpc.aio.unary_unary_rpc_method_handler(
            instrumented_unary_unary,
            request_deserializer=handler.request_deserializer,
            response_serializer=handler.response_serializer,
        )
