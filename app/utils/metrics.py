from prometheus_client import Counter, Histogram

search_queries_total = Counter(
    "ufb_search_queries_total",
    "Total number of search requests",
    ["endpoint"],
)

search_terms_total = Counter(
    "ufb_search_terms_total",
    "Total searches by query term (high cardinality — use for top-N analysis only)",
    ["term"],
)

grpc_requests_total = Counter(
    "ufb_search_grpc_requests_total",
    "Total number of gRPC requests handled, by method and status code",
    ["grpc_method", "grpc_code"],
)

grpc_request_duration_seconds = Histogram(
    "ufb_search_grpc_request_duration_seconds",
    "Latency of gRPC requests in seconds",
    ["grpc_method"],
)
