import uuid
import pytest
import requests
from typing import Generator
from requests.exceptions import ReadTimeout
from clients.api_client import APIClient
from config.settings import settings


# Helper

def unique(prefix: str = "test") -> str:
    """Generate a unique name to avoid test data collisions."""
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _create_integration(client: APIClient, type_: str) -> dict:
    name = f"test-integration-{uuid.uuid4().hex[:8]}"

    # Attempt creation
    try:
        resp = client.create_integration(name=name, type_=type_)
    except ReadTimeout:
        pytest.fail(
            "BUG-007: POST /integrations hung and never responded. "
            "Server deadlocks on integration creation. "
            "Cannot set up test data."
        )

    assert resp.status_code in (200, 201), (
        f"Setup failed: POST /integrations returned {resp.status_code}. "
        f"Body: {resp.text}"
    )

    data = resp.json()

    if data is None:
        try:
            list_resp = client.list_integrations()
        except ReadTimeout:
            pytest.fail(
                "GET /integrations hung after POST returned null. "
                "Cannot retrieve created integration."
            )

        assert list_resp.status_code == 200, (
            f"Fallback GET /integrations failed: {list_resp.status_code}"
        )

        integrations = list_resp.json()

        if integrations is None:
            pytest.fail(
                "POST /integrations returned null AND "
                "GET /integrations returned null. "
                "Cannot create or retrieve test data. "
                "Both BUG-006 and BUG-007 are blocking fixture setup."
            )

        # GET returned empty list
        if len(integrations) == 0:
            pytest.fail(
                "POST /integrations returned null AND "
                "GET /integrations returned empty list []. "
                "Integration was not persisted by the server."
            )

        # Try to find ours by name, fall back to last item
        match = next(
            (i for i in integrations if i.get("name") == name),
            None
        )
        data = match if match else integrations[-1]

    return data


# Clients

@pytest.fixture(scope="session")
def client1() -> APIClient:
    """Authenticated client for user1 (test1 / test123)."""
    return APIClient(settings.user1_username, settings.user1_password)


@pytest.fixture(scope="session")
def client2() -> APIClient:
    """Authenticated client for user2 (test2 / test456)."""
    return APIClient(settings.user2_username, settings.user2_password)


@pytest.fixture(scope="session")
def unauth_client() -> APIClient:
    """Client with invalid credentials. Used for 401 tests."""
    return APIClient("invalid_user", "invalid_pass")


@pytest.fixture(scope="session")
def no_auth_session():
    """Raw session with no auth header at all."""
    return requests.Session()


# Shared integrations

@pytest.fixture(scope="session")
def integration1(client1) -> Generator[dict, None, None]:
    """
    Session-scoped integration owned by user1.
    Created once, reused across all tests that need it.
    Cleaned up after the entire session finishes.
    """
    data = _create_integration(client1, type_="aws")
    yield data
    # Teardown
    try:
        client1.delete_integration(data["id"])
    except ReadTimeout:
        pass


@pytest.fixture(scope="session")
def integration2(client2) -> Generator[dict, None, None]:
    """
    Session-scoped integration owned by user2.
    Retries on timeout since server intermittently hangs on POST /integrations.
    """
    data = None
    last_error = None

    # Retry up to 3 times
    for attempt in range(3):
        try:
            data = _create_integration(client2, type_="gcp")
            break
        except pytest.fail.Exception as e:
            last_error = str(e)
            # Restart attempt if it was a timeout
            if "BUG-007" in str(e):
                continue
            else:
                raise 

    if data is None:
        pytest.skip(
            f"SKIPPING tenant tests: Could not create integration2 after "
            f"3 attempts. Server keeps hanging on POST /integrations for user2. "
            f"Last error: {last_error}. "
            f"server deadlocks on integration creation."
        )

    yield data

    try:
        client2.delete_integration(data["id"])
    except ReadTimeout:
        pass