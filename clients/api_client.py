import requests
from requests import Response
from config.settings import settings


class APIClient:
    """
    Typed HTTP client for the integration API.
    All tests interact via this class.
    """

    def __init__(self, username: str, password: str):
        self.base_url = settings.base_url.rstrip("/")
        self.timeout = 3  # fail fast instead of hanging forever
        self.session = requests.Session()
        self.session.auth = (username, password)
        self.session.headers.update({"Content-Type": "application/json"})

    # Integrations

    def list_integrations(self, page: int = None, limit: int = None) -> Response:
        params = {}
        if page is not None:
            params["page"] = page
        if limit is not None:
            params["limit"] = limit
        return self.session.get(
            f"{self.base_url}/integrations",
            params=params,
            timeout=self.timeout
        )

    def create_integration(self, name: str, type_: str) -> Response:
        return self.session.post(
            f"{self.base_url}/integrations",
            json={"name": name, "type": type_},
            timeout=self.timeout
        )

    def update_integration(self, integration_id: str, name: str) -> Response:
        return self.session.put(
            f"{self.base_url}/integrations",
            json={"id": integration_id, "name": name},
            timeout=self.timeout
        )

    def get_integration(self, integration_id: str) -> Response:
        return self.session.get(
            f"{self.base_url}/integrations/{integration_id}",
            timeout=self.timeout
        )

    def delete_integration(self, integration_id: str) -> Response:
        return self.session.delete(
            f"{self.base_url}/integrations/{integration_id}",
            timeout=self.timeout
        )

    # Assets

    def list_assets(self, integration_id: str, page: int = None, limit: int = None) -> Response:
        params = {"integrationId": integration_id}
        if page is not None:
            params["page"] = page
        if limit is not None:
            params["limit"] = limit
        return self.session.get(
            f"{self.base_url}/assets",
            params=params,
            timeout=self.timeout
        )

    def create_asset(self, integration_id: str, name: str, description: str = "") -> Response:
        return self.session.post(
            f"{self.base_url}/assets",
            json={"integration_id": integration_id, "name": name, "description": description},
            timeout=self.timeout
        )

    def update_asset(self, asset_id: str, name: str = None, description: str = None) -> Response:
        payload = {"id": asset_id}
        if name is not None:
            payload["name"] = name
        if description is not None:
            payload["description"] = description
        return self.session.patch(
            f"{self.base_url}/assets",
            json=payload,
            timeout=self.timeout
        )

    def get_asset(self, asset_id) -> Response:
        return self.session.get(
            f"{self.base_url}/assets/{asset_id}",
            timeout=self.timeout
        )

    def delete_asset(self, asset_id) -> Response:
        return self.session.delete(
            f"{self.base_url}/assets/{asset_id}",
            timeout=self.timeout
        )