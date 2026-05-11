import pytest
import requests
from config.settings import settings


@pytest.mark.auth
class TestAuthentication:

    def test_valid_credentials_integrations_returns_200(self, client1):
        resp = client1.list_integrations()
        assert resp.status_code == 200

    def test_valid_credentials_assets_requires_integration_id(self, client1, integration1):
        resp = client1.list_assets(integration_id=integration1["id"])
        assert resp.status_code == 200

    def test_invalid_credentials_integrations_returns_401(self, unauth_client):
        resp = unauth_client.list_integrations()
        assert resp.status_code == 401

    def test_invalid_credentials_assets_returns_401(self, unauth_client, integration1):
        resp = unauth_client.list_assets(integration_id=integration1["id"])
        assert resp.status_code == 401

    def test_no_auth_header_integrations_returns_401(self, no_auth_session):
        resp = no_auth_session.get(f"{settings.base_url}/integrations")
        assert resp.status_code == 401

    def test_no_auth_header_assets_returns_401(self, no_auth_session, integration1):
        resp = no_auth_session.get(
            f"{settings.base_url}/assets",
            params={"integrationId": integration1["id"]}
        )
        assert resp.status_code == 401

    def test_wrong_password_returns_401(self):
        from clients.api_client import APIClient
        bad_client = APIClient(settings.user1_username, "wrongpassword")
        resp = bad_client.list_integrations()
        assert resp.status_code == 401

    def test_401_response_has_correct_content_type(self, unauth_client):
        resp = unauth_client.list_integrations()
        assert resp.status_code == 401
        assert "application/json" in resp.headers.get("Content-Type", "")

    def test_401_error_body_schema(self, unauth_client):
        """Error body must have 'code' and 'message' fields per OpenAPI spec."""
        resp = unauth_client.list_integrations()
        assert resp.status_code == 401
        body = resp.json()
        assert "code" in body
        assert "message" in body

    def test_401_error_code_field_matches_status(self, unauth_client):
        resp = unauth_client.list_integrations()
        assert resp.status_code == 401
        body = resp.json()
        assert body["code"] == 401, (
            f"HTTP status is 401 but error body 'code' field is {body['code']}. "
        )
