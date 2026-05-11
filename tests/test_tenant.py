import uuid
import pytest
from requests.exceptions import ReadTimeout


def unique(prefix="test"):
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


@pytest.mark.tenant
class TestIntegrationTenantSegregation:

    def test_user1_cannot_read_user2_integration(self, client1, client2, integration2):
        """user1 should NOT be able to GET an integration created by user2."""
        try:
            resp = client1.get_integration(integration2["id"])
            assert resp.status_code in (403, 404), (
                f"CRITICAL BUG: user1 can read user2's integration. "
                f"Got status {resp.status_code}, body: {resp.text}"
            )
        except ReadTimeout:
            pytest.fail(
                "Server hung on cross-tenant "
                "GET /integrations/{id}. Expected 403 or 404 but server "
                "never responded. Tenant isolation is broken."
            )

    def test_user2_cannot_read_user1_integration(self, client1, client2, integration1):
        """user2 should NOT be able to GET an integration created by user1."""
        try:
            resp = client2.get_integration(integration1["id"])
            assert resp.status_code in (403, 404), (
                f"CRITICAL BUG: user2 can read user1's integration. "
                f"Got status {resp.status_code}, body: {resp.text}"
            )
        except ReadTimeout:
            pytest.fail(
                "Server hung on cross-tenant "
                "GET /integrations/{id}. Expected 403 or 404 but server "
                "never responded. Tenant isolation is broken."
            )

    def test_user1_list_does_not_contain_user2_integrations(self, client1, client2, integration1, integration2):
        """GET /integrations for user1 should only return user1's integrations."""
        try:
            resp = client1.list_integrations()
            assert resp.status_code == 200
            ids = [i["id"] for i in resp.json()]
            assert integration2["id"] not in ids, (
                f"CRITICAL BUG: user2's integration {integration2['id']} "
                f"appears in user1's integration list."
            )
        except ReadTimeout:
            pytest.fail(
                "Server hung on "
                "GET /integrations for user1. Never responded."
            )

    def test_user2_list_does_not_contain_user1_integrations(self, client1, client2, integration1, integration2):
        """GET /integrations for user2 should only return user2's integrations."""
        try:
            resp = client2.list_integrations()
            assert resp.status_code == 200
            ids = [i["id"] for i in resp.json()]
            assert integration1["id"] not in ids, (
                f"CRITICAL BUG: user1's integration {integration1['id']} "
                f"appears in user2's integration list."
            )
        except ReadTimeout:
            pytest.fail(
                "Server hung on "
                "GET /integrations for user2. Never responded."
            )

    def test_user1_cannot_update_user2_integration(self, client1, integration2):
        """user1 should NOT be able to PUT user2's integration."""
        try:
            resp = client1.update_integration(
                integration_id=integration2["id"],
                name=unique("hacked")
            )
            assert resp.status_code in (403, 404), (
                f"CRITICAL BUG: user1 was able to update user2's integration. "
                f"Got status {resp.status_code}"
            )
        except ReadTimeout:
            pytest.fail(
                "Server hung on cross-tenant "
                "PUT /integrations. Expected 403 or 404 but server "
                "never responded. Tenant isolation is broken."
            )

    def test_user1_cannot_delete_user2_integration(self, client2, client1):
        """user1 should NOT be able to DELETE user2's integration."""
        try:
            victim = client2.create_integration(
                name=unique("victim"), type_="aws"
            )
            assert victim.status_code in (200, 201)
            victim_data = victim.json()
            if victim_data is None:
                list_resp = client2.list_integrations()
                integrations = list_resp.json() or []
                victim_data = integrations[-1] if integrations else None
            if victim_data is None:
                pytest.skip("Could not create victim integration for deletion test")

            resp = client1.delete_integration(victim_data["id"])
            assert resp.status_code in (403, 404), (
                f"user1 was able to delete user2's integration. "
                f"Got status {resp.status_code}"
            )
            # Cleanup
            client2.delete_integration(victim_data["id"])

        except ReadTimeout:
            pytest.fail(
                "Server hung on cross-tenant "
                "DELETE /integrations/{id}. Expected 403 or 404 but server "
                "never responded. Tenant isolation is broken."
            )

    def test_integration_tenant_id_is_scoped_to_user(self, client1, client2, integration1, integration2):
        """tenant_id on integration1 must differ from integration2's tenant_id."""
        try:
            resp1 = client1.get_integration(integration1["id"])
            resp2 = client2.get_integration(integration2["id"])
            if resp1.status_code == 200 and resp2.status_code == 200:
                assert resp1.json()["tenant_id"] != resp2.json()["tenant_id"], (
                    "Both users share the same tenant_id. "
                    "Tenant isolation is completely broken."
                )
        except ReadTimeout:
            pytest.fail(
                "CRITICAL BUG — BUG-007: Server hung on GET /integrations/{id}. "
                "Never responded."
            )


@pytest.mark.tenant
class TestAssetTenantSegregation:

    def test_user1_cannot_read_user2_asset(self, client1, client2, integration1, integration2):
        """user1 should NOT be able to GET an asset created by user2."""
        try:
            asset_resp = client2.create_asset(
                integration_id=integration2["id"],
                name=unique("u2-asset")
            )
            assert asset_resp.status_code in (200, 201)
            asset = asset_resp.json()
            if asset is None:
                pytest.skip("Could not create user2 asset — POST returned null")

            resp = client1.get_asset(asset["id"])
            assert resp.status_code in (403, 404), (
                f"user1 can read user2's asset. "
                f"Got status {resp.status_code}, body: {resp.text}"
            )
            client2.delete_asset(asset["id"])

        except ReadTimeout:
            pytest.fail(
                "Server hung on cross-tenant "
                "GET /assets/{id}. Expected 403 or 404 but server "
                "never responded. Tenant isolation is broken."
            )

    def test_user1_cannot_list_user2_assets(self, client1, client2, integration1, integration2):
        """user1 cannot list assets belonging to user2's integration."""
        try:
            u2_asset_resp = client2.create_asset(
                integration_id=integration2["id"],
                name=unique("u2-asset")
            )
            assert u2_asset_resp.status_code in (200, 201)
            u2_asset = u2_asset_resp.json()
            if u2_asset is None:
                pytest.skip("Could not create user2 asset — POST returned null")

            resp = client1.list_assets(integration_id=integration2["id"])
            assert resp.status_code in (200, 403, 404)

            if resp.status_code == 200:
                ids = [a["id"] for a in (resp.json() or [])]
                assert u2_asset["id"] not in ids, (
                    f"user1 can see user2's asset {u2_asset['id']} "
                    f"by passing user2's integrationId."
                )
            client2.delete_asset(u2_asset["id"])

        except ReadTimeout:
            pytest.fail(
                "Server hung on cross-tenant "
                "GET /assets. Expected quick response but server "
                "never responded. Tenant isolation is broken."
            )

    def test_user1_cannot_update_user2_asset(self, client1, client2, integration2):
        """user1 should NOT be able to PATCH user2's asset."""
        try:
            asset_resp = client2.create_asset(
                integration_id=integration2["id"],
                name=unique("u2-asset")
            )
            assert asset_resp.status_code in (200, 201)
            asset = asset_resp.json()
            if asset is None:
                pytest.skip("Could not create user2 asset — POST returned null")

            resp = client1.update_asset(
                asset_id=asset["id"],
                name=unique("hacked")
            )
            assert resp.status_code in (403, 404), (
                f"user1 was able to update user2's asset. "
                f"Got status {resp.status_code}"
            )
            client2.delete_asset(asset["id"])

        except ReadTimeout:
            pytest.fail(
                "Server hung on cross-tenant "
                "PATCH /assets. Expected 403 or 404 but server "
                "never responded. Tenant isolation is broken."
            )

    def test_user1_cannot_delete_user2_asset(self, client1, client2, integration2):
        """user1 should NOT be able to DELETE user2's asset."""
        try:
            asset_resp = client2.create_asset(
                integration_id=integration2["id"],
                name=unique("victim-asset")
            )
            assert asset_resp.status_code in (200, 201)
            asset = asset_resp.json()
            if asset is None:
                pytest.skip("Could not create user2 asset — POST returned null")

            resp = client1.delete_asset(asset["id"])
            assert resp.status_code in (403, 404), (
                f"user1 was able to delete user2's asset. "
                f"Got status {resp.status_code}"
            )
            client2.delete_asset(asset["id"])

        except ReadTimeout:
            pytest.fail(
                "Server hung on cross-tenant "
                "DELETE /assets/{id}. Expected 403 or 404 but server "
                "never responded. Tenant isolation is broken."
            )

    def test_asset_tenant_id_matches_owner(self, client1, integration1):
        """The tenant_id on a created asset must match the creating user's tenant."""
        try:
            integ_resp = client1.get_integration(integration1["id"])
            asset_resp = client1.create_asset(
                integration_id=integration1["id"],
                name=unique("asset")
            )
            assert asset_resp.status_code in (200, 201)
            asset = asset_resp.json()
            if asset is None:
                pytest.skip("POST /assets returned null — cannot validate tenant_id")

            if integ_resp.status_code == 200:
                expected_tenant = integ_resp.json()["tenant_id"]
                assert asset["tenant_id"] == expected_tenant, (
                    f"BUG: Asset tenant_id '{asset['tenant_id']}' does not match "
                    f"integration tenant_id '{expected_tenant}'."
                )
            client1.delete_asset(asset["id"])

        except ReadTimeout:
            pytest.fail(
                "Server hung on GET /integrations/{id} or "
                "POST /assets. Never responded."
            )

    def test_asset_belongs_to_correct_integration(self, client1, integration1):
        """Assets created under integration1 must not appear under a different integration."""
        try:
            integ2_resp = client1.create_integration(
                name=unique("integ2"), type_="gcp"
            )
            assert integ2_resp.status_code in (200, 201)
            integ2 = integ2_resp.json()
            if integ2 is None:
                list_resp = client1.list_integrations()
                integrations = list_resp.json() or []
                integ2 = integrations[-1] if integrations else None
            if integ2 is None:
                pytest.skip("Could not create second integration")

            asset_resp = client1.create_asset(
                integration_id=integration1["id"],
                name=unique("asset")
            )
            assert asset_resp.status_code in (200, 201)
            asset = asset_resp.json()
            if asset is None:
                pytest.skip("POST /assets returned null")

            resp = client1.list_assets(integration_id=integ2["id"])
            if resp.status_code == 200:
                ids = [a["id"] for a in (resp.json() or [])]
                assert asset["id"] not in ids, (
                    "Asset created under integration1 appears "
                    "in integration2's asset list."
                )

            client1.delete_asset(asset["id"])
            client1.delete_integration(integ2["id"])

        except ReadTimeout:
            pytest.fail(
                "Server hung during asset belongs to correct "
                "integration test. Never responded."
            )