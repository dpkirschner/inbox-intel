"""Guesty API client for authentication and API interactions."""

from datetime import datetime, timedelta
from typing import Any

import requests

from .config import config
from .logger import logger


class GuestyClient:
    """Client for interacting with the Guesty Open API."""

    def __init__(self) -> None:
        self.client_id = config.GUESTY_API_KEY
        self.client_secret = config.GUESTY_API_SECRET
        self.base_url = config.GUESTY_API_BASE_URL
        self.token_url = "https://open-api.guesty.com/oauth2/token"
        self.access_token: str | None = None
        self.token_expiry: datetime | None = None

    def _get_access_token(self) -> str:
        """
        Obtain an access token using OAuth2 client credentials flow.
        Tokens are cached and reused until they expire.
        """
        if (
            self.access_token
            and self.token_expiry
            and datetime.now() < self.token_expiry - timedelta(minutes=5)
        ):
            return self.access_token

        logger.info("Requesting new access token from Guesty API")

        payload = {
            "grant_type": "client_credentials",
            "scope": "open-api",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }

        headers = {
            "content-type": "application/x-www-form-urlencoded",
        }

        try:
            response = requests.post(
                self.token_url,
                data=payload,
                headers=headers,
                timeout=30,
            )
            response.raise_for_status()

            token_data = response.json()
            self.access_token = token_data["access_token"]
            expires_in = token_data.get("expires_in", 86400)
            self.token_expiry = datetime.now() + timedelta(seconds=expires_in)

            logger.info("Successfully obtained access token")
            return self.access_token

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to obtain access token: {e}")
            raise

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Make an authenticated request to the Guesty API.
        """
        token = self._get_access_token()
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=data,
                timeout=30,
            )
            response.raise_for_status()
            result: dict[str, Any] = response.json()
            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {method} {url} - {e}")
            raise

    def test_connection(self) -> dict[str, Any]:
        """
        Test the API connection by fetching the list of properties.
        """
        logger.info("Testing Guesty API connection by fetching listings")
        return self._make_request("GET", "listings", params={"limit": 10})

    def get_listings(self, limit: int = 100, skip: int = 0) -> dict[str, Any]:
        """
        Fetch listings (properties) from Guesty.
        """
        params = {"limit": limit, "skip": skip}
        return self._make_request("GET", "listings", params=params)
