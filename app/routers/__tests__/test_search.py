from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.auth import verify_api_key
from app.main import app


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
            patch(
                "app.routers.search.fetch_playlist_results", new_callable=AsyncMock
            ) as mock_playlists,
        ):
            mock_top.return_value = []
            mock_artists.return_value = []
            mock_labels.return_value = []
            mock_releases.return_value = []
            mock_tracks.return_value = []
            mock_playlists.return_value = []
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
    @patch("app.routers.search.fetch_playlist_results", new_callable=AsyncMock)
    def test_search_returns_all_result_groups(
        self,
        mock_playlists,
        mock_tracks,
        mock_releases,
        mock_labels,
        mock_artists,
        mock_top,
        client,
    ):
        mock_top.return_value = [{"name": "Top"}]
        mock_artists.return_value = [{"name": "Artist1"}]
        mock_labels.return_value = [{"name": "Label1"}]
        mock_releases.return_value = [{"name": "Release1"}]
        mock_tracks.return_value = [{"name": "Track1"}]
        mock_playlists.return_value = [{"name": "Playlist1"}]

        response = client.get("/api/search/?q=test")

        assert response.status_code == 200
        data = response.json()
        assert data["results"]["top"] == [{"name": "Top"}]
        assert data["results"]["artists"] == [{"name": "Artist1"}]
        assert data["results"]["labels"] == [{"name": "Label1"}]
        assert data["results"]["releases"] == [{"name": "Release1"}]
        assert data["results"]["tracks"] == [{"name": "Track1"}]
        assert data["results"]["playlists"] == [{"name": "Playlist1"}]

    def test_search_missing_query_param_returns_422(self, client):
        response = client.get("/api/search/")
        assert response.status_code == 422

    @patch("app.routers.search.fetch_top_results", new_callable=AsyncMock)
    @patch("app.routers.search.fetch_artist_results", new_callable=AsyncMock)
    @patch("app.routers.search.fetch_labels_results", new_callable=AsyncMock)
    @patch("app.routers.search.fetch_releases_results", new_callable=AsyncMock)
    @patch("app.routers.search.fetch_tracks_results", new_callable=AsyncMock)
    @patch("app.routers.search.fetch_playlist_results", new_callable=AsyncMock)
    def test_search_calls_all_fetch_functions(
        self,
        mock_playlists,
        mock_tracks,
        mock_releases,
        mock_labels,
        mock_artists,
        mock_top,
        client,
    ):
        for m in [
            mock_top,
            mock_artists,
            mock_labels,
            mock_releases,
            mock_tracks,
            mock_playlists,
        ]:
            m.return_value = []

        client.get("/api/search/?q=jazz")

        mock_top.assert_called_once_with("jazz")
        mock_artists.assert_called_once_with("jazz")
        mock_labels.assert_called_once_with("jazz")
        mock_releases.assert_called_once_with("jazz")
        mock_tracks.assert_called_once_with("jazz")
        mock_playlists.assert_called_once_with("jazz")


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


class TestSearchPlaylists:
    @patch("app.routers.search.fetch_playlist_results", new_callable=AsyncMock)
    def test_search_playlists_returns_results(self, mock_playlists, client):
        mock_playlists.return_value = [{"name": "Playlist1"}]

        response = client.get("/api/search/playlists?q=playlist")

        assert response.status_code == 200
        assert response.json() == {"results": [{"name": "Playlist1"}]}
        mock_playlists.assert_called_once_with("playlist")

    @patch("app.routers.search.fetch_playlist_results", new_callable=AsyncMock)
    def test_search_playlists_returns_empty_list(self, mock_playlists, client):
        mock_playlists.return_value = []

        response = client.get("/api/search/playlists?q=unknown")

        assert response.status_code == 200
        assert response.json() == {"results": []}

    def test_search_playlists_missing_query_param_returns_422(self, client):
        response = client.get("/api/search/playlists")
        assert response.status_code == 422


class TestSearchSuggestions:
    @patch("app.routers.search.fetch_suggestions_results", new_callable=AsyncMock)
    def test_search_suggestions_returns_results(self, mock_suggestions, client):
        mock_suggestions.return_value = [{"name": "Hot Creations"}]

        response = client.get("/api/search/suggestions?q=hot")

        assert response.status_code == 200
        assert response.json() == {"results": [{"name": "Hot Creations"}]}
        mock_suggestions.assert_called_once_with("hot")

    @patch("app.routers.search.fetch_suggestions_results", new_callable=AsyncMock)
    def test_search_suggestions_returns_empty_list(self, mock_suggestions, client):
        mock_suggestions.return_value = []

        response = client.get("/api/search/suggestions?q=unknown")

        assert response.status_code == 200
        assert response.json() == {"results": []}

    def test_search_suggestions_missing_query_param_returns_422(self, client):
        response = client.get("/api/search/suggestions")
        assert response.status_code == 422


class TestQueryDecoding:
    @patch("app.routers.search.fetch_artist_results", new_callable=AsyncMock)
    def test_accented_query_reaches_search_unchanged(self, mock_artists, client):
        mock_artists.return_value = []

        response = client.get("/api/search/artists", params={"q": "Âme"})

        assert response.status_code == 200
        mock_artists.assert_called_once_with("Âme")

    @patch("app.routers.search.fetch_artist_results", new_callable=AsyncMock)
    def test_query_with_a_backslash_does_not_fail(self, mock_artists, client):
        mock_artists.return_value = []

        response = client.get("/api/search/artists", params={"q": "AC\\x"})

        assert response.status_code == 200
        mock_artists.assert_called_once_with("AC\\x")


class TestIndexEndpointsRemoved:
    @pytest.mark.parametrize("path", ["create-index", "delete-index"])
    def test_index_endpoints_do_not_exist(self, path, client):
        response = client.post(f"/api/search/{path}")

        assert response.status_code in (404, 405)
