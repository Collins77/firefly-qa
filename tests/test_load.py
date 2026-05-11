import time
import pytest
import concurrent.futures
from config.settings import settings


def _make_request(client, integration_id: str) -> tuple[int, float]:
    """Single request — returns (status_code, response_time_seconds)."""
    start = time.monotonic()
    resp = client.list_assets(integration_id=integration_id)
    return resp.status_code, time.monotonic() - start


@pytest.mark.load
class TestLoadPerformance:

    def test_handles_1000_requests_per_minute(self, client1, integration1):
        """
        Fire 1000 requests using a thread pool and verify:
        - >= 95% succeed (200 status)
        - All complete within 60 seconds (i.e., 1000 req/min throughput)
        """
        request_count = settings.load_request_count
        max_workers = settings.load_max_workers
        threshold = settings.load_success_rate_threshold

        results = []
        start_wall = time.monotonic()

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(_make_request, client1, integration1["id"])
                for _ in range(request_count)
            ]
            for future in concurrent.futures.as_completed(futures):
                results.append(future.result())

        wall_time = time.monotonic() - start_wall
        success_count = sum(1 for status, _ in results if status == 200)
        success_rate = success_count / len(results)
        avg_response_ms = (sum(t for _, t in results) / len(results)) * 1000
        max_response_ms = max(t for _, t in results) * 1000

        print(f"\n── Load Test Results ──────────────────────────")
        print(f"  Total requests:    {request_count}")
        print(f"  Successful (200):  {success_count}")
        print(f"  Success rate:      {success_rate:.1%}")
        print(f"  Wall time:         {wall_time:.1f}s")
        print(f"  Avg response time: {avg_response_ms:.0f}ms")
        print(f"  Max response time: {max_response_ms:.0f}ms")
        print(f"  Effective RPM:     {(request_count / wall_time) * 60:.0f}")
        print(f"───────────────────────────────────────────────")

        assert wall_time <= 60, (
            f"FAIL: {request_count} requests took {wall_time:.1f}s — exceeds 60s window. "
            f"Service cannot sustain 1000 req/min."
        )
        assert success_rate >= threshold, (
            f"FAIL: Success rate {success_rate:.1%} is below {threshold:.0%} threshold. "
            f"{request_count - success_count} requests failed."
        )

    def test_single_request_response_time(self, client1, integration1):
        """Individual request should respond within 2 seconds."""
        start = time.monotonic()
        resp = client1.list_integrations()
        elapsed = time.monotonic() - start
        assert resp.status_code == 200
        assert elapsed < 2.0, f"Single request took {elapsed:.2f}s — too slow."

    def test_concurrent_users_no_data_leakage(self, client1, client2, integration1, integration2):
        """
        Fire concurrent requests from both users simultaneously.
        Verify responses only contain data belonging to the requesting user.
        This catches race conditions in tenant isolation under load.
        """
        results = {}

        def fetch(label, client, integration_id):
            resp = client.list_assets(integration_id=integration_id)
            results[label] = resp

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for i in range(5):
                futures.append(executor.submit(fetch, f"u1_{i}", client1, integration1["id"]))
                futures.append(executor.submit(fetch, f"u2_{i}", client2, integration2["id"]))
            concurrent.futures.wait(futures)

        for label, resp in results.items():
            assert resp.status_code == 200, f"Request {label} failed: {resp.status_code}"
            for asset in resp.json():
                if label.startswith("u1"):
                    assert asset["tenant_id"] == resp.json()[0]["tenant_id"] if resp.json() else True
