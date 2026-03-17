from unittest.mock import patch

import pytest

from app.routers.queries.fetch_labels_results import fetch_labels_results


@pytest.mark.asyncio
@patch("app.routers.queries.fetch_labels_results.client")
async def test_fetch_label_results_returns_hits(mock_client):
    mock_client.search.return_value = {
        "hits": {
            "hits": [
                {"_source": {"name": "Label1"}},
                {"_source": {"name": "Label2"}},
            ]
        }
    }
    results = await fetch_labels_results("Label")
    assert results == [{"name": "Label1"}, {"name": "Label2"}]
