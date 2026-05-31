from prometheus_client import Counter

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
