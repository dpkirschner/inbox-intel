"""Tests for Guesty API client functionality."""

from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest
import requests

from src.guesty_client import GuestyClient


@pytest.fixture
def mock_config():
    """Mock configuration values."""
    with patch("src.guesty_client.config") as mock_cfg:
        mock_cfg.GUESTY_API_KEY = "test_client_id"
        mock_cfg.GUESTY_API_SECRET = "test_client_secret"
        mock_cfg.GUESTY_API_BASE_URL = "https://open-api.guesty.com/v1"
        yield mock_cfg


@pytest.fixture
def client(mock_config):
    """Create a GuestyClient instance with mocked config."""
    return GuestyClient()


@pytest.fixture
def mock_token_response():
    """Mock successful token response."""
    return {
        "access_token": "mock_access_token_12345",
        "token_type": "Bearer",
        "expires_in": 86400,
        "scope": "open-api",
    }


@pytest.fixture
def mock_listings_response():
    """Mock successful listings response."""
    return {
        "results": [
            {
                "_id": "listing_001",
                "title": "Cozy Beach House",
                "accommodates": 4,
                "address": {"city": "Miami", "country": "US"},
            },
            {
                "_id": "listing_002",
                "title": "Downtown Apartment",
                "accommodates": 2,
                "address": {"city": "New York", "country": "US"},
            },
        ],
        "count": 2,
        "limit": 10,
    }


class TestGuestyClientInitialization:
    """Tests for GuestyClient initialization."""

    def test_client_initialization(self, client):
        """Test client is initialized with correct values."""
        assert client.client_id == "test_client_id"
        assert client.client_secret == "test_client_secret"
        assert client.base_url == "https://open-api.guesty.com/v1"
        assert client.token_url == "https://open-api.guesty.com/oauth2/token"
        assert client.access_token is None
        assert client.token_expiry is None


class TestAuthentication:
    """Tests for authentication functionality."""

    @patch("src.guesty_client.requests.post")
    def test_get_access_token_success(self, mock_post, client, mock_token_response):
        """Test successfully obtaining an access token."""
        mock_response = Mock()
        mock_response.json.return_value = mock_token_response
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        token = client._get_access_token()

        assert token == "mock_access_token_12345"
        assert client.access_token == "mock_access_token_12345"
        assert client.token_expiry is not None
        assert client.token_expiry > datetime.now()

        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "https://open-api.guesty.com/oauth2/token"
        assert call_args[1]["data"]["grant_type"] == "client_credentials"
        assert call_args[1]["data"]["scope"] == "open-api"
        assert call_args[1]["data"]["client_id"] == "test_client_id"
        assert call_args[1]["data"]["client_secret"] == "test_client_secret"

    @patch("src.guesty_client.requests.post")
    def test_get_access_token_reuses_cached_token(self, mock_post, client):
        """Test that cached token is reused when not expired."""
        client.access_token = "cached_token"
        client.token_expiry = datetime.now() + timedelta(hours=12)

        token = client._get_access_token()

        assert token == "cached_token"
        mock_post.assert_not_called()

    @patch("src.guesty_client.requests.post")
    def test_get_access_token_refreshes_near_expiry(
        self, mock_post, client, mock_token_response
    ):
        """Test token is refreshed when near expiration."""
        client.access_token = "old_token"
        client.token_expiry = datetime.now() + timedelta(minutes=3)

        mock_response = Mock()
        mock_response.json.return_value = mock_token_response
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        token = client._get_access_token()

        assert token == "mock_access_token_12345"
        mock_post.assert_called_once()

    @patch("src.guesty_client.requests.post")
    def test_get_access_token_handles_request_exception(self, mock_post, client):
        """Test handling of request exceptions during token retrieval."""
        mock_post.side_effect = requests.exceptions.RequestException("Network error")

        with pytest.raises(requests.exceptions.RequestException):
            client._get_access_token()

    @patch("src.guesty_client.requests.post")
    def test_get_access_token_handles_http_error(self, mock_post, client):
        """Test handling of HTTP errors during token retrieval."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "401 Unauthorized"
        )
        mock_post.return_value = mock_response

        with pytest.raises(requests.exceptions.HTTPError):
            client._get_access_token()


class TestAPIRequests:
    """Tests for API request functionality."""

    @patch("src.guesty_client.requests.request")
    def test_make_request_success(self, mock_request, client):
        """Test successful API request."""
        client.access_token = "valid_token"
        client.token_expiry = datetime.now() + timedelta(hours=12)

        mock_response = Mock()
        mock_response.json.return_value = {"data": "test"}
        mock_response.raise_for_status = Mock()
        mock_request.return_value = mock_response

        result = client._make_request("GET", "test/endpoint", params={"foo": "bar"})

        assert result == {"data": "test"}
        mock_request.assert_called_once()
        call_args = mock_request.call_args[1]
        assert call_args["method"] == "GET"
        assert call_args["url"] == "https://open-api.guesty.com/v1/test/endpoint"
        assert call_args["headers"]["Authorization"] == "Bearer valid_token"
        assert call_args["params"] == {"foo": "bar"}

    @patch("src.guesty_client.requests.post")
    @patch("src.guesty_client.requests.request")
    def test_make_request_gets_token_if_missing(
        self, mock_request, mock_post, client, mock_token_response
    ):
        """Test that _make_request obtains token if not cached."""
        mock_token_resp = Mock()
        mock_token_resp.json.return_value = mock_token_response
        mock_token_resp.raise_for_status = Mock()
        mock_post.return_value = mock_token_resp

        mock_api_resp = Mock()
        mock_api_resp.json.return_value = {"success": True}
        mock_api_resp.raise_for_status = Mock()
        mock_request.return_value = mock_api_resp

        result = client._make_request("GET", "listings")

        assert result == {"success": True}
        mock_post.assert_called_once()
        mock_request.assert_called_once()

    @patch("src.guesty_client.requests.request")
    def test_make_request_handles_http_error(self, mock_request, client):
        """Test handling of HTTP errors during API requests."""
        client.access_token = "valid_token"
        client.token_expiry = datetime.now() + timedelta(hours=12)

        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")
        mock_request.return_value = mock_response

        with pytest.raises(requests.exceptions.HTTPError):
            client._make_request("GET", "nonexistent")

    @patch("src.guesty_client.requests.request")
    def test_make_request_handles_request_exception(self, mock_request, client):
        """Test handling of request exceptions during API requests."""
        client.access_token = "valid_token"
        client.token_expiry = datetime.now() + timedelta(hours=12)

        mock_request.side_effect = requests.exceptions.RequestException("Connection timeout")

        with pytest.raises(requests.exceptions.RequestException):
            client._make_request("GET", "listings")


class TestClientMethods:
    """Tests for specific client methods."""

    @patch.object(GuestyClient, "_make_request")
    def test_test_connection(self, mock_make_request, client, mock_listings_response):
        """Test test_connection method."""
        mock_make_request.return_value = mock_listings_response

        result = client.test_connection()

        assert result == mock_listings_response
        mock_make_request.assert_called_once_with("GET", "listings", params={"limit": 10})

    @patch.object(GuestyClient, "_make_request")
    def test_get_listings_default_params(self, mock_make_request, client, mock_listings_response):
        """Test get_listings with default parameters."""
        mock_make_request.return_value = mock_listings_response

        result = client.get_listings()

        assert result == mock_listings_response
        mock_make_request.assert_called_once_with(
            "GET", "listings", params={"limit": 100, "skip": 0}
        )

    @patch.object(GuestyClient, "_make_request")
    def test_get_listings_custom_params(self, mock_make_request, client, mock_listings_response):
        """Test get_listings with custom parameters."""
        mock_make_request.return_value = mock_listings_response

        result = client.get_listings(limit=50, skip=25)

        assert result == mock_listings_response
        mock_make_request.assert_called_once_with(
            "GET", "listings", params={"limit": 50, "skip": 25}
        )


class TestIntegration:
    """Integration tests (require actual API credentials)."""

    @pytest.mark.skip(reason="Requires valid Guesty API credentials")
    def test_real_api_connection(self):
        """Test actual API connection with real credentials."""
        client = GuestyClient()
        result = client.test_connection()
        assert "results" in result or "data" in result
