import asyncio
from os import getenv

import grpc
from google.protobuf.struct_pb2 import Struct
from grpc_reflection.v1alpha import reflection

from app.grpc import search_pb2, search_pb2_grpc
from app.grpc.interceptors import ApiKeyInterceptor, PrometheusServerInterceptor
from app.routers.queries import (
    fetch_artist_results,
    fetch_labels_results,
    fetch_playlist_results,
    fetch_releases_results,
    fetch_top_results,
    fetch_tracks_results,
)
from app.utils import logger
from app.utils.metrics import search_queries_total

GRPC_PORT = getenv("GRPC_PORT", "50051")


def _to_structs(items: list[dict]) -> list[Struct]:
    structs = []
    for item in items:
        struct = Struct()
        struct.update(item)
        structs.append(struct)
    return structs


class SearchServicer(search_pb2_grpc.SearchServiceServicer):
    async def Search(self, request, context):
        query = request.query
        logger.info("gRPC search query received", extra={"query": query})

        search_queries_total.labels(endpoint="general").inc()

        top, artists, labels, releases, tracks, playlists = await asyncio.gather(
            fetch_top_results(query),
            fetch_artist_results(query),
            fetch_labels_results(query),
            fetch_releases_results(query),
            fetch_tracks_results(query),
            fetch_playlist_results(query),
        )

        return search_pb2.SearchResponse(
            top=_to_structs(top),
            artists=_to_structs(artists),
            labels=_to_structs(labels),
            releases=_to_structs(releases),
            tracks=_to_structs(tracks),
            playlists=_to_structs(playlists),
        )

    async def SearchArtists(self, request, context):
        query = request.query
        logger.info("gRPC artist search query received", extra={"query": query})

        search_queries_total.labels(endpoint="artists").inc()

        results = await fetch_artist_results(query)
        return search_pb2.ItemListResponse(results=_to_structs(results))

    async def SearchLabels(self, request, context):
        query = request.query
        logger.info("gRPC label search query received", extra={"query": query})

        search_queries_total.labels(endpoint="labels").inc()

        results = await fetch_labels_results(query)
        return search_pb2.ItemListResponse(results=_to_structs(results))


async def create_grpc_server() -> grpc.aio.Server:
    server = grpc.aio.server(
        interceptors=[PrometheusServerInterceptor(), ApiKeyInterceptor()]
    )
    search_pb2_grpc.add_SearchServiceServicer_to_server(SearchServicer(), server)

    reflection.enable_server_reflection(
        (
            search_pb2.DESCRIPTOR.services_by_name["SearchService"].full_name,
            reflection.SERVICE_NAME,
        ),
        server,
    )

    server.add_insecure_port(f"[::]:{GRPC_PORT}")
    return server
