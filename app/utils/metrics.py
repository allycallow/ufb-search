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

search_zero_results_total = Counter(
    "ufb_search_zero_results_total",
    "Total search requests that returned no results",
    ["endpoint"],
)

search_lead_expansions_total = Counter(
    "ufb_search_lead_expansions_total",
    "Total top searches that returned a label or artist with its releases and tracks",
    ["lead_type"],
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
