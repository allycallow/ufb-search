import asyncio
from os import getenv

import grpc
from google.protobuf.struct_pb2 import Struct
from grpc_reflection.v1alpha import reflection

from app.grpc import search_pb2, search_pb2_grpc
from app.grpc.interceptors import ApiKeyInterceptor
from app.routers.get_item import get_item_details
from app.routers.queries import (
    fetch_artist_results,
    fetch_labels_results,
    fetch_releases_results,
    fetch_top_results,
    fetch_tracks_results,
)
from app.utils import logger
from app.utils.metrics import search_queries_total, search_terms_total
from app.utils.opensearch import client

INDEX = getenv("OPENSEARCH_INDEX_NAME", "upfrontbeats")
GRPC_PORT = getenv("GRPC_PORT", "50051")

TYPE_NAMES = {
    search_pb2.ARTIST: "artists",
    search_pb2.LABEL: "labels",
    search_pb2.RELEASE: "releases",
    search_pb2.TRACK: "tracks",
}


def _to_structs(items: list[dict]) -> list[Struct]:
    structs = []
    for item in items:
        struct = Struct()
        struct.update(item)
        structs.append(struct)
    return structs


def _decode_query(query: str) -> str:
    return query.encode("utf-8").decode("unicode_escape")


class SearchServicer(search_pb2_grpc.SearchServiceServicer):
    async def Search(self, request, context):
        query = _decode_query(request.query)
        logger.info("gRPC search query received", extra={"query": query})

        search_queries_total.labels(endpoint="general").inc()
        search_terms_total.labels(term=query.lower().strip()).inc()

        top, artists, labels, releases, tracks = await asyncio.gather(
            fetch_top_results(query),
            fetch_artist_results(query),
            fetch_labels_results(query),
            fetch_releases_results(query),
            fetch_tracks_results(query),
        )

        return search_pb2.SearchResponse(
            top=_to_structs(top),
            artists=_to_structs(artists),
            labels=_to_structs(labels),
            releases=_to_structs(releases),
            tracks=_to_structs(tracks),
            playlists=[],
        )

    async def SearchArtists(self, request, context):
        query = _decode_query(request.query)
        logger.info("gRPC artist search query received", extra={"query": query})

        search_queries_total.labels(endpoint="artists").inc()
        search_terms_total.labels(term=query.lower().strip()).inc()

        results = await fetch_artist_results(query)
        return search_pb2.ItemListResponse(results=_to_structs(results))

    async def SearchLabels(self, request, context):
        query = _decode_query(request.query)
        logger.info("gRPC label search query received", extra={"query": query})

        search_queries_total.labels(endpoint="labels").inc()
        search_terms_total.labels(term=query.lower().strip()).inc()

        results = await fetch_labels_results(query)
        return search_pb2.ItemListResponse(results=_to_structs(results))

    async def AddItem(self, request, context):
        logger.info("gRPC creating search item", extra={"item_id": request.id})
        type_name = TYPE_NAMES[request.type]
        response = get_item_details(request.id, type_name)

        client.index(index=INDEX, id=request.id, body={**response, "type": type_name})

        return search_pb2.StatusResponse(success=True)

    async def UpdateItem(self, request, context):
        logger.info("gRPC updating search item", extra={"item_id": request.id})
        type_name = TYPE_NAMES[request.type]
        response = get_item_details(request.id, type_name)

        client.update(
            index=INDEX,
            id=request.id,
            body={"doc": {**response, "type": type_name}, "doc_as_upsert": True},
        )

        return search_pb2.StatusResponse(success=True)

    async def DeleteItem(self, request, context):
        logger.info("gRPC deleting search item", extra={"item_id": request.id})
        client.delete(index=INDEX, id=request.id)

        return search_pb2.StatusResponse(success=True)

    async def CreateIndex(self, request, context):
        logger.info("gRPC creating index")
        client.indices.create(
            index=INDEX,
            body={
                "settings": {
                    "index": {
                        "number_of_shards": 1,
                        "number_of_replicas": 0,
                    },
                },
                "mappings": {
                    "properties": {
                        "popularity": {"type": "integer"},
                    },
                },
            },
        )

        return search_pb2.StatusResponse(success=True)

    async def DeleteIndex(self, request, context):
        logger.info("gRPC deleting index")
        client.indices.delete_index(index=INDEX)

        return search_pb2.StatusResponse(success=True)


async def create_grpc_server() -> grpc.aio.Server:
    server = grpc.aio.server(interceptors=[ApiKeyInterceptor()])
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
