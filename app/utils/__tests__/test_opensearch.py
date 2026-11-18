from app.utils.opensearch import OPENSEARCH_TIMEOUT_SECONDS, client


def test_opensearch_calls_time_out_before_the_backend_deadline() -> None:
    # The backend gives a search 5 seconds; top results makes two calls in a row.
    assert OPENSEARCH_TIMEOUT_SECONDS * 2 < 5
    assert client.transport.get_connection().timeout == OPENSEARCH_TIMEOUT_SECONDS
