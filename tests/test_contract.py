import uuid
import pytest
from models.schemas import Asset, Integration, HTTPError


def unique(prefix="test"):
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


# integration contract tests

@pytest.mark.contract
class TestIntegrationContract:

    def test_post_integration_returns_200(self, client1):
        resp = client1.create_integration(name=unique("integ"), type_="aws")
        assert resp.status_code == 200

    def test_post_integration_response_schema(self, client1):
        resp = client1.create_integration(name=unique("integ"), type_="aws")
        assert resp.status_code == 200
        integration = Integration(**resp.json())
        assert integration.id
        assert integration.name
        assert integration.type
        assert integration.tenant_id

    def test_post_integration_response_content_type(self, client1):
        resp = client1.create_integration(name=unique("integ"), type_="aws")
        assert "application/json" in resp.headers.get("Content-Type", "")

    def test_post_integration_name_persisted(self, client1):
        name = unique("integ")
        resp = client1.create_integration(name=name, type_="aws")
        assert resp.json()["name"] == name

    def test_post_integration_type_persisted(self, client1):
        resp = client1.create_integration(name=unique("integ"), type_="gcp")
        assert resp.json()["type"] == "gcp"

    def test_post_integration_missing_name_returns_400(self, client1):
        resp = client1.session.post(
            f"{client1.base_url}/integrations",
            json={"type": "aws"}
        )
        assert resp.status_code == 400

    def test_post_integration_missing_type_returns_400(self, client1):
        resp = client1.session.post(
            f"{client1.base_url}/integrations",
            json={"name": unique("integ")}
        )
        assert resp.status_code == 400

    def test_post_integration_empty_body_returns_400(self, client1):
        resp = client1.session.post(
            f"{client1.base_url}/integrations",
            json={}
        )
        assert resp.status_code == 400

    def test_get_integrations_returns_200(self, client1):
        resp = client1.list_integrations()
        assert resp.status_code == 200

    def test_get_integrations_returns_list(self, client1):
        resp = client1.list_integrations()
        assert isinstance(resp.json(), list)

    def test_get_integrations_items_match_schema(self, client1, integration1):
        resp = client1.list_integrations()
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) > 0
        for item in items:
            Integration(**item)

    def test_get_integrations_pagination_page_param(self, client1):
        resp = client1.list_integrations(page=1, limit=5)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_integration_by_id_returns_200(self, client1, integration1):
        resp = client1.get_integration(integration1["id"])
        assert resp.status_code == 200

    def test_get_integration_by_id_schema(self, client1, integration1):
        resp = client1.get_integration(integration1["id"])
        Integration(**resp.json())

    def test_get_integration_by_id_returns_correct_record(self, client1, integration1):
        resp = client1.get_integration(integration1["id"])
        assert resp.json()["id"] == integration1["id"]

    def test_get_integration_nonexistent_returns_404(self, client1):
        resp = client1.get_integration("nonexistent-id-000")
        assert resp.status_code == 404

    def test_put_integration_returns_200(self, client1, integration1):
        resp = client1.update_integration(
            integration_id=integration1["id"],
            name=unique("updated")
        )
        assert resp.status_code == 200

    def test_put_integration_response_schema(self, client1, integration1):
        resp = client1.update_integration(
            integration_id=integration1["id"],
            name=unique("updated")
        )
        Integration(**resp.json())

    def test_put_integration_name_is_updated(self, client1, integration1):
        new_name = unique("updated")
        client1.update_integration(integration_id=integration1["id"], name=new_name)
        resp = client1.get_integration(integration1["id"])
        assert resp.json()["name"] == new_name

    def test_put_integration_nonexistent_returns_404(self, client1):
        resp = client1.update_integration(
            integration_id="nonexistent-id-000",
            name="doesnt-matter"
        )
        assert resp.status_code == 404

    def test_delete_integration_returns_200(self, client1):
        resp = client1.create_integration(name=unique("todelete"), type_="aws")
        assert resp.status_code == 200
        integration_id = resp.json()["id"]
        delete_resp = client1.delete_integration(integration_id)
        assert delete_resp.status_code == 200

    def test_delete_integration_nonexistent_returns_404(self, client1):
        resp = client1.delete_integration("nonexistent-id-000")
        assert resp.status_code == 404

    def test_delete_integration_then_get_returns_404(self, client1):
        resp = client1.create_integration(name=unique("todelete"), type_="aws")
        integration_id = resp.json()["id"]
        client1.delete_integration(integration_id)
        get_resp = client1.get_integration(integration_id)
        assert get_resp.status_code == 404


# Asset contract tests

@pytest.mark.contract
class TestAssetContract:

    def test_post_asset_returns_200(self, client1, integration1):
        resp = client1.create_asset(
            integration_id=integration1["id"],
            name=unique("asset"),
            description="test asset"
        )
        assert resp.status_code == 200

    def test_post_asset_response_schema(self, client1, integration1):
        resp = client1.create_asset(
            integration_id=integration1["id"],
            name=unique("asset"),
            description="test"
        )
        assert resp.status_code == 200
        Asset(**resp.json())

    def test_post_asset_fields_persisted(self, client1, integration1):
        name = unique("asset")
        desc = "my description"
        resp = client1.create_asset(
            integration_id=integration1["id"],
            name=name,
            description=desc
        )
        data = resp.json()
        assert data["name"] == name
        assert data["description"] == desc
        assert data["integration_id"] == integration1["id"]

    def test_post_asset_missing_integration_id_returns_400(self, client1):
        resp = client1.session.post(
            f"{client1.base_url}/assets",
            json={"name": unique("asset"), "description": "test"}
        )
        assert resp.status_code == 400

    def test_post_asset_missing_name_returns_400(self, client1, integration1):
        resp = client1.session.post(
            f"{client1.base_url}/assets",
            json={"integration_id": integration1["id"], "description": "test"}
        )
        assert resp.status_code == 400

    def test_post_asset_invalid_integration_id_returns_404(self, client1):
        resp = client1.create_asset(
            integration_id="nonexistent-integration-id",
            name=unique("asset")
        )
        assert resp.status_code in (400, 404)

    def test_get_assets_by_integration_id_returns_200(self, client1, integration1):
        resp = client1.list_assets(integration_id=integration1["id"])
        assert resp.status_code == 200

    def test_get_assets_returns_list(self, client1, integration1):
        resp = client1.list_assets(integration_id=integration1["id"])
        assert isinstance(resp.json(), list)

    def test_get_assets_items_match_schema(self, client1, integration1):
        client1.create_asset(integration_id=integration1["id"], name=unique("asset"))
        resp = client1.list_assets(integration_id=integration1["id"])
        for item in resp.json():
            Asset(**item)

    def test_get_assets_missing_integration_id_returns_400(self, client1):
        resp = client1.session.get(f"{client1.base_url}/assets")
        assert resp.status_code == 400

    def test_get_assets_pagination(self, client1, integration1):
        resp = client1.list_assets(integration_id=integration1["id"], page=1, limit=2)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_asset_by_id_returns_200(self, client1, integration1):
        created = client1.create_asset(
            integration_id=integration1["id"],
            name=unique("asset")
        ).json()
        resp = client1.get_asset(created["id"])
        assert resp.status_code == 200

    def test_get_asset_by_id_schema(self, client1, integration1):
        created = client1.create_asset(
            integration_id=integration1["id"],
            name=unique("asset")
        ).json()
        resp = client1.get_asset(created["id"])
        Asset(**resp.json())

    def test_get_asset_by_id_returns_correct_record(self, client1, integration1):
        created = client1.create_asset(
            integration_id=integration1["id"],
            name=unique("asset")
        ).json()
        resp = client1.get_asset(created["id"])
        assert resp.json()["id"] == created["id"]

    def test_get_asset_nonexistent_returns_404(self, client1):
        resp = client1.get_asset(999999)
        assert resp.status_code == 404

    def test_patch_asset_returns_200(self, client1, integration1):
        created = client1.create_asset(
            integration_id=integration1["id"],
            name=unique("asset")
        ).json()
        resp = client1.update_asset(asset_id=created["id"], name=unique("updated"))
        assert resp.status_code == 200

    def test_patch_asset_response_schema(self, client1, integration1):
        created = client1.create_asset(
            integration_id=integration1["id"],
            name=unique("asset")
        ).json()
        resp = client1.update_asset(asset_id=created["id"], name=unique("updated"))
        Asset(**resp.json())

    def test_patch_asset_name_is_updated(self, client1, integration1):
        created = client1.create_asset(
            integration_id=integration1["id"],
            name=unique("asset")
        ).json()
        new_name = unique("renamed")
        client1.update_asset(asset_id=created["id"], name=new_name)
        resp = client1.get_asset(created["id"])
        assert resp.json()["name"] == new_name

    def test_patch_asset_nonexistent_returns_404(self, client1):
        resp = client1.update_asset(asset_id="nonexistent-id", name="doesnt-matter")
        assert resp.status_code == 404

    def test_delete_asset_returns_204(self, client1, integration1):
        created = client1.create_asset(
            integration_id=integration1["id"],
            name=unique("todelete")
        ).json()
        resp = client1.delete_asset(created["id"])
        assert resp.status_code == 204

    def test_delete_asset_then_get_returns_404(self, client1, integration1):
        created = client1.create_asset(
            integration_id=integration1["id"],
            name=unique("todelete")
        ).json()
        client1.delete_asset(created["id"])
        get_resp = client1.get_asset(created["id"])
        assert get_resp.status_code == 404

    def test_delete_asset_nonexistent_returns_404(self, client1):
        resp = client1.delete_asset(999999)
        assert resp.status_code == 404


# Cross-cutting contract checks 

@pytest.mark.contract
class TestErrorResponseContract:

    def test_400_error_schema_integration(self, client1):
        resp = client1.session.post(
            f"{client1.base_url}/integrations", json={}
        )
        assert resp.status_code == 400
        body = resp.json()
        assert "code" in body
        assert "message" in body

    def test_404_error_schema_integration(self, client1):
        resp = client1.get_integration("nonexistent-id-000")
        assert resp.status_code == 404
        body = resp.json()
        assert "code" in body
        assert "message" in body

    def test_error_code_field_matches_http_status_400(self, client1):
        """BUG PROBE: All OpenAPI error examples show code=400. Verify actual responses."""
        resp = client1.session.post(f"{client1.base_url}/integrations", json={})
        assert resp.status_code == 400
        assert resp.json()["code"] == 400

    def test_error_code_field_matches_http_status_404(self, client1):
        """BUG PROBE: OpenAPI 404 example shows code=400. This may be a bug."""
        resp = client1.get_integration("nonexistent-id-000")
        assert resp.status_code == 404
        assert resp.json()["code"] == 404, (
            f"HTTP status 404 but error body code={resp.json()['code']}. "
        )

    def test_delete_asset_vs_integration_status_code_consistency(self, client1, integration1):
        created = client1.create_asset(
            integration_id=integration1["id"],
            name=unique("consistency-check")
        ).json()
        asset_delete = client1.delete_asset(created["id"])
        integ = client1.create_integration(name=unique("integ"), type_="aws").json()
        integ_delete = client1.delete_integration(integ["id"])

        assert asset_delete.status_code == 204
        if integ_delete.status_code != 204:
            pytest.warns(
                UserWarning,
                match=f"DELETE /integrations returns {integ_delete.status_code}, "
                      "expected 204 to be consistent with DELETE /assets which returns 204."
            )
