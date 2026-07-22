import grpc

from app.auth import API_KEY


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
