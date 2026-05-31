from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.auth import verify_api_key
from app.main import app

VALID_EVENT = {
    "version": "0",
    "id": "abc123",
    "detail-type": "artist.created",
    "source": "upfrontbeats",
    "account": "123456789",
    "time": "2024-01-01T00:00:00Z",
    "region": "eu-west-2",
    "resources": [],
    "detail": {"id": "item-123"},
}


@pytest.fixture
def client():
    app.dependency_overrides[verify_api_key] = lambda: None
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def unauthenticated_client():
    with TestClient(app) as c:
        yield c


class TestRoot:
    def test_root(self, client):
        response = client.get("/")
        assert response.status_code == 200
        assert response.json() == {"message": "Hello World"}


class TestAuth:
    def test_missing_api_key_returns_401(self, unauthenticated_client):
        response = unauthenticated_client.get("/api/search/?q=test")
        assert response.status_code == 401

    def test_invalid_api_key_returns_401(self, unauthenticated_client, monkeypatch):
        monkeypatch.setattr("app.auth.API_KEY", "valid-key")
        response = unauthenticated_client.get(
            "/api/search/?q=test", headers={"X-API-Key": "wrong-key"}
        )
        assert response.status_code == 401

    def test_valid_api_key_passes(self, unauthenticated_client, monkeypatch):
        monkeypatch.setattr("app.auth.API_KEY", "valid-key")
        with (
            patch(
                "app.routers.search.fetch_top_results", new_callable=AsyncMock
            ) as mock_top,
            patch(
                "app.routers.search.fetch_artist_results", new_callable=AsyncMock
            ) as mock_artists,
            patch(
                "app.routers.search.fetch_labels_results", new_callable=AsyncMock
            ) as mock_labels,
            patch(
                "app.routers.search.fetch_releases_results", new_callable=AsyncMock
            ) as mock_releases,
            patch(
                "app.routers.search.fetch_tracks_results", new_callable=AsyncMock
            ) as mock_tracks,
        ):
            mock_top.return_value = []
            mock_artists.return_value = []
            mock_labels.return_value = []
            mock_releases.return_value = []
            mock_tracks.return_value = []
            response = unauthenticated_client.get(
                "/api/search/?q=test", headers={"X-API-Key": "valid-key"}
            )
        assert response.status_code == 200


class TestSearch:
    @patch("app.routers.search.fetch_top_results", new_callable=AsyncMock)
    @patch("app.routers.search.fetch_artist_results", new_callable=AsyncMock)
    @patch("app.routers.search.fetch_labels_results", new_callable=AsyncMock)
    @patch("app.routers.search.fetch_releases_results", new_callable=AsyncMock)
    @patch("app.routers.search.fetch_tracks_results", new_callable=AsyncMock)
    def test_search_returns_all_result_groups(
        self, mock_tracks, mock_releases, mock_labels, mock_artists, mock_top, client
    ):
        mock_top.return_value = [{"name": "Top"}]
        mock_artists.return_value = [{"name": "Artist1"}]
        mock_labels.return_value = [{"name": "Label1"}]
        mock_releases.return_value = [{"name": "Release1"}]
        mock_tracks.return_value = [{"name": "Track1"}]

        response = client.get("/api/search/?q=test")

        assert response.status_code == 200
        data = response.json()
        assert data["results"]["top"] == [{"name": "Top"}]
        assert data["results"]["artists"] == [{"name": "Artist1"}]
        assert data["results"]["labels"] == [{"name": "Label1"}]
        assert data["results"]["releases"] == [{"name": "Release1"}]
        assert data["results"]["tracks"] == [{"name": "Track1"}]
        assert data["results"]["playlists"] == []

    def test_search_missing_query_param_returns_422(self, client):
        response = client.get("/api/search/")
        assert response.status_code == 422

    @patch("app.routers.search.fetch_top_results", new_callable=AsyncMock)
    @patch("app.routers.search.fetch_artist_results", new_callable=AsyncMock)
    @patch("app.routers.search.fetch_labels_results", new_callable=AsyncMock)
    @patch("app.routers.search.fetch_releases_results", new_callable=AsyncMock)
    @patch("app.routers.search.fetch_tracks_results", new_callable=AsyncMock)
    def test_search_calls_all_fetch_functions(
        self, mock_tracks, mock_releases, mock_labels, mock_artists, mock_top, client
    ):
        for m in [mock_top, mock_artists, mock_labels, mock_releases, mock_tracks]:
            m.return_value = []

        client.get("/api/search/?q=jazz")

        mock_top.assert_called_once_with("jazz")
        mock_artists.assert_called_once_with("jazz")
        mock_labels.assert_called_once_with("jazz")
        mock_releases.assert_called_once_with("jazz")
        mock_tracks.assert_called_once_with("jazz")


class TestSearchArtists:
    @patch("app.routers.search.fetch_artist_results", new_callable=AsyncMock)
    def test_search_artists_returns_results(self, mock_artists, client):
        mock_artists.return_value = [{"name": "Artist1"}]

        response = client.get("/api/search/artists?q=artist")

        assert response.status_code == 200
        assert response.json() == {"results": [{"name": "Artist1"}]}

    @patch("app.routers.search.fetch_artist_results", new_callable=AsyncMock)
    def test_search_artists_returns_empty_list(self, mock_artists, client):
        mock_artists.return_value = []

        response = client.get("/api/search/artists?q=unknown")

        assert response.status_code == 200
        assert response.json() == {"results": []}

    def test_search_artists_missing_query_param_returns_422(self, client):
        response = client.get("/api/search/artists")
        assert response.status_code == 422


class TestSearchLabels:
    @patch("app.routers.search.fetch_labels_results", new_callable=AsyncMock)
    def test_search_labels_returns_results(self, mock_labels, client):
        mock_labels.return_value = [{"name": "Label1"}]

        response = client.get("/api/search/labels?q=label")

        assert response.status_code == 200
        assert response.json() == {"results": [{"name": "Label1"}]}

    @patch("app.routers.search.fetch_labels_results", new_callable=AsyncMock)
    def test_search_labels_returns_empty_list(self, mock_labels, client):
        mock_labels.return_value = []

        response = client.get("/api/search/labels?q=unknown")

        assert response.status_code == 200
        assert response.json() == {"results": []}

    def test_search_labels_missing_query_param_returns_422(self, client):
        response = client.get("/api/search/labels")
        assert response.status_code == 422


class TestAddItem:
    @patch("app.routers.search.get_item_details")
    @patch("app.routers.search.client")
    def test_add_item_indexes_document(self, mock_os_client, mock_get_item, client):
        mock_get_item.return_value = {"name": "Test Artist"}

        response = client.post("/api/search/add", json=VALID_EVENT)

        assert response.status_code == 200
        assert response.json() == {"success": True}
        mock_os_client.index.assert_called_once()

    @patch("app.routers.search.get_item_details")
    @patch("app.routers.search.client")
    def test_add_item_uses_correct_type(self, mock_os_client, mock_get_item, client):
        mock_get_item.return_value = {"name": "Test Artist"}

        client.post("/api/search/add", json=VALID_EVENT)

        call_kwargs = mock_os_client.index.call_args
        assert call_kwargs.kwargs["body"]["type"] == "artists"

    @patch("app.routers.search.get_item_details")
    @patch("app.routers.search.client")
    def test_add_item_each_type(self, mock_os_client, mock_get_item, client):
        mock_get_item.return_value = {"name": "Test"}
        type_map = {
            "artist.created": "artists",
            "label.created": "labels",
            "release.created": "releases",
            "track.created": "tracks",
        }
        for detail_type, expected_type in type_map.items():
            event = {**VALID_EVENT, "detail-type": detail_type}
            response = client.post("/api/search/add", json=event)
            assert response.status_code == 200
            body = mock_os_client.index.call_args.kwargs["body"]
            assert body["type"] == expected_type

    def test_add_item_missing_body_returns_422(self, client):
        response = client.post("/api/search/add")
        assert response.status_code == 422


class TestUpdateItem:
    @patch("app.routers.search.get_item_details")
    @patch("app.routers.search.client")
    def test_update_item_upserts_document(self, mock_os_client, mock_get_item, client):
        mock_get_item.return_value = {"name": "Test Artist"}

        response = client.put("/api/search/update", json=VALID_EVENT)

        assert response.status_code == 200
        assert response.json() == {"success": True}
        mock_os_client.update.assert_called_once()

    @patch("app.routers.search.get_item_details")
    @patch("app.routers.search.client")
    def test_update_item_uses_doc_as_upsert(
        self, mock_os_client, mock_get_item, client
    ):
        mock_get_item.return_value = {"name": "Test"}

        client.put("/api/search/update", json=VALID_EVENT)

        body = mock_os_client.update.call_args.kwargs["body"]
        assert body["doc_as_upsert"] is True

    def test_update_item_missing_body_returns_422(self, client):
        response = client.put("/api/search/update")
        assert response.status_code == 422


class TestDeleteItem:
    @patch("app.routers.search.client")
    def test_delete_item_removes_document(self, mock_os_client, client):
        response = client.request("DELETE", "/api/search/delete", json=VALID_EVENT)

        assert response.status_code == 200
        assert response.json() == {"success": True}
        mock_os_client.delete.assert_called_once()

    @patch("app.routers.search.client")
    def test_delete_item_uses_correct_id(self, mock_os_client, client):
        client.request("DELETE", "/api/search/delete", json=VALID_EVENT)

        call_kwargs = mock_os_client.delete.call_args
        assert call_kwargs.kwargs["id"] == "item-123"

    def test_delete_item_missing_body_returns_422(self, client):
        response = client.request("DELETE", "/api/search/delete")
        assert response.status_code == 422


class TestCreateIndex:
    @patch("app.routers.search.client")
    def test_create_index_succeeds(self, mock_os_client, client):
        response = client.post("/api/search/create-index")

        assert response.status_code == 200
        assert response.json() == {"success": True}
        mock_os_client.indices.create.assert_called_once()


class TestDeleteIndex:
    @patch("app.routers.search.client")
    def test_delete_index_succeeds(self, mock_os_client, client):
        response = client.post("/api/search/delete-index")

        assert response.status_code == 200
        assert response.json() == {"success": True}
        mock_os_client.indices.delete_index.assert_called_once()
