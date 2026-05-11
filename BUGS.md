# Bug Report — infralightio/test-integration-api
**Tester:** Collins Muema
**Date:** 2026-05-10
**Tool:** pytest 8.3.5 | Python 3.11.2 | Windows 10
**Test Run Summary:** 33 passed · 31 failed · 9 skipped · 0 errors · 33 seconds

---

## Summary Table

| Bug ID | Severity | Endpoint | Description | Status |
|--------|----------|----------|-------------|--------|
| BUG-001 | High | All error responses | Error body `code` field always 400 regardless of actual HTTP status | Confirmed |
| BUG-002 | Low | DELETE /integrations/{id} | Returns 200 instead of 204 — inconsistent with DELETE /assets/{id} | Confirmed |
| BUG-003 | Medium | GET /assets/{id} | Path parameter type inconsistency — spec says integer but responses use string IDs | Confirmed |
| BUG-004 | Low | PATCH /assets | ID passed in body instead of path — inconsistent with REST conventions | Confirmed |
| BUG-005 | Critical | All /integrations, /assets | Tenant isolation broken — users can read other tenants' data | Confirmed |
| BUG-006 | High | POST /integrations | Returns null body intermittently instead of created object | Confirmed |
| BUG-007 | Critical | Multiple endpoints | Server hangs indefinitely on cross-tenant requests — never responds | Confirmed |
| BUG-008 | Medium | POST /integrations | Returns 201 instead of spec-defined 200 | Confirmed |
| BUG-009 | High | POST /assets | Accepts requests with missing required fields and returns 201 | Confirmed |
| BUG-010 | Medium | PATCH /assets | Returns 500 on nonexistent asset instead of 404 | Confirmed |
| BUG-011 | Medium | DELETE /assets/{id} | Returns 204 on nonexistent asset instead of 404 | Confirmed |
| BUG-012 | Medium | POST /integrations | Swagger UI missing Authorize button — auth not documented in spec | Confirmed |

---

## BUG-001 — Error response body `code` field does not match HTTP status

**Severity:** High
**Endpoints:** All endpoints returning 4xx and 5xx responses
**Test:** `tests/test_contract.py::TestErrorResponseContract::test_error_code_field_matches_http_status_404`

**Steps to reproduce:**
```bash
curl -u test1:test123 http://localhost:8080/api/v1/integrations/nonexistent-id
```

**Expected:**
```json
{ "code": 404, "message": "integration not found" }
```

**Actual:**
```json
{ "error": "integration not found" }
```

**Additional finding:** The error response body does not follow the schema defined in the OpenAPI spec at all. The spec defines `{ "code": integer, "message": string }` but the actual response uses `{ "error": string }` — completely different field names.

**Impact:** Any client parsing error responses per the OpenAPI spec will break. Error handling code will fail to find the `code` or `message` fields.

---

## BUG-002 — DELETE /integrations/{id} returns 200 instead of 204

**Severity:** Low
**Endpoint:** `DELETE /integrations/{id}`
**Test:** `tests/test_contract.py::TestErrorResponseContract::test_delete_asset_vs_integration_status_code_consistency`

**Steps to reproduce:**
```bash
curl -u test1:test123 -X DELETE http://localhost:8080/api/v1/integrations/{id}
```

**Expected:** `204 No Content` (consistent with `DELETE /assets/{id}` which correctly returns 204)

**Actual:** `200 OK`

**Impact:** Inconsistency between two DELETE endpoints on the same API. Clients that check for 204 on DELETE operations will incorrectly treat integration deletions as failures.

---

## BUG-003 — Asset ID type inconsistency between path param and response body

**Severity:** Medium
**Endpoint:** `GET /assets/{id}`, `DELETE /assets/{id}`

**Steps to reproduce:**
```bash
# Path param defined as integer in spec
curl -u test1:test123 http://localhost:8080/api/v1/assets/abc-string-id
```

**Expected:** Spec defines `id` path parameter as `integer`. Response body returns `id` as `string`.

**Actual:** Passing a string ID to an integer path param causes inconsistent behaviour — sometimes 400, sometimes unexpected results.

**Impact:** API contract is ambiguous. Clients cannot reliably determine the correct ID type to use.

---

## BUG-004 — PATCH /assets uses body ID instead of path parameter

**Severity:** Low (Design)
**Endpoint:** `PATCH /assets`

**Description:** Unlike `GET /assets/{id}` and `DELETE /assets/{id}` which correctly use path parameters, `PATCH /assets` takes the asset ID in the request body. This violates REST conventions and is inconsistent with the rest of the API.

**Impact:** Increases risk of updating the wrong resource. Non-standard pattern makes the API harder to use and document.

---

## BUG-005 — CRITICAL: Tenant isolation completely broken

**Severity:** Critical
**Endpoints:** `GET /integrations/{id}`, all cross-tenant operations
**Test:** `tests/test_tenant.py::TestIntegrationTenantSegregation::test_user2_cannot_read_user1_integration`

**Steps to reproduce:**
```bash
# Step 1: Create integration as user1, note the id
curl -u test1:test123 -X POST http://localhost:8080/api/v1/integrations \
  -H "Content-Type: application/json" \
  -d '{"name": "user1-integration", "type": "aws"}'

# Step 2: Read that integration as user2
curl -u test2:test456 http://localhost:8080/api/v1/integrations/{user1_integration_id}
```

**Expected:** `403 Forbidden` or `404 Not Found`

**Actual:** `200 OK` with full integration data returned

**Evidence from test run:**
```
FAILED test_user2_cannot_read_user1_integration —
CRITICAL BUG: user2 can read user1's integration.
Got status 200, body: {"id":"aa28241a-49d5-44bc-8..."}
```

**Impact:** Any authenticated user can read any other tenant's data by guessing or obtaining resource IDs. This is a complete tenant isolation failure and a critical security vulnerability. In a production environment this would constitute a data breach.

---

## BUG-006 — POST /integrations returns null body intermittently

**Severity:** High
**Endpoint:** `POST /integrations`
**Test:** `tests/test_contract.py::TestIntegrationContract::test_post_integration_response_schema`

**Steps to reproduce:**
```bash
curl -u test1:test123 -X POST http://localhost:8080/api/v1/integrations \
  -H "Content-Type: application/json" \
  -d '{"name": "test-integration", "type": "aws"}'
```

**Expected:**
```json
{ "id": "abc123", "name": "test-integration", "type": "aws", "tenant_id": "xyz" }
```

**Actual (intermittent):**
```
null
```

**Impact:** Callers cannot retrieve the ID of the resource they just created without making a secondary `GET /integrations` request. Any create-then-use workflow breaks. This is intermittent — sometimes returns the object correctly (status 201), sometimes returns null.

---

## BUG-007 — CRITICAL: Server hangs indefinitely on cross-tenant requests

**Severity:** Critical
**Endpoints:** `GET /integrations/{id}`, `PUT /integrations`, `DELETE /integrations/{id}`, `PATCH /assets`, `DELETE /assets/{id}` (when called cross-tenant)
**Test:** All tests in `tests/test_tenant.py::TestIntegrationTenantSegregation` and `TestAssetTenantSegregation`

**Steps to reproduce:**
```bash
# Create integration as user1
# Then from user2, attempt to access it:
curl -u test2:test456 http://localhost:8080/api/v1/integrations/{user1_id}
# Connection hangs — never receives a response
```

**Expected:** `403 Forbidden` or `404 Not Found` returned within milliseconds

**Actual:** Server never responds. Connection hangs indefinitely until client timeout.

**Evidence from test run:**
```
ERROR: requests.exceptions.ReadTimeout:
HTTPConnectionPool(host='localhost', port=8080): Read timed out. (read timeout=3)
```

This was observed consistently across:
- `GET /integrations/{id}` (cross-tenant)
- `PUT /integrations` (cross-tenant)
- `DELETE /integrations/{id}` (cross-tenant)
- `PATCH /assets` (cross-tenant)
- `DELETE /assets/{id}` (cross-tenant)
- `GET /integrations` (list) — also hangs under certain conditions

**Impact:**
- Tenant isolation is broken at the server level — unauthorized requests cause deadlocks
- In production this enables Denial of Service attacks: any user can hang server threads by making cross-tenant requests
- 9 tenant tests had to be skipped because the server could not complete fixture setup reliably

---

## BUG-008 — POST /integrations returns 201 instead of spec-defined 200

**Severity:** Medium
**Endpoint:** `POST /integrations`
**Test:** `tests/test_contract.py::TestIntegrationContract::test_post_integration_returns_200`

**Steps to reproduce:**
```bash
curl -i -u test1:test123 -X POST http://localhost:8080/api/v1/integrations \
  -H "Content-Type: application/json" \
  -d '{"name": "test", "type": "aws"}'
```

**Expected:** `200 OK` (as defined in OpenAPI spec)

**Actual:** `201 Created`

**Note:** While `201` is semantically more correct for a resource creation operation, it directly contradicts the OpenAPI specification which documents `200` as the success response. This breaks contract validation.

**Impact:** Any client that checks for `200` on integration creation will incorrectly treat successful creations as failures.

---

## BUG-009 — POST /assets accepts requests with missing required fields

**Severity:** High
**Endpoint:** `POST /assets`
**Tests:**
- `tests/test_contract.py::TestAssetContract::test_post_asset_missing_integration_id_returns_400`
- `tests/test_contract.py::TestAssetContract::test_post_asset_missing_name_returns_400`

**Steps to reproduce:**
```bash
# Missing integration_id
curl -u test1:test123 -X POST http://localhost:8080/api/v1/assets \
  -H "Content-Type: application/json" \
  -d '{"name": "test-asset", "description": "test"}'

# Missing name
curl -u test1:test123 -X POST http://localhost:8080/api/v1/assets \
  -H "Content-Type: application/json" \
  -d '{"integration_id": "some-id", "description": "test"}'
```

**Expected:** `400 Bad Request` — required fields missing

**Actual:** `201 Created` — asset created despite missing required fields

**Evidence from test run:**
```
FAILED test_post_asset_missing_integration_id_returns_400 — assert 201 == 400
FAILED test_post_asset_missing_name_returns_400 — assert 201 == 400
```

**Impact:** Data integrity is compromised. Assets can be created in an invalid state with missing required fields, causing downstream failures when those assets are accessed.

---

## BUG-010 — PATCH /assets returns 500 on nonexistent asset instead of 404

**Severity:** Medium
**Endpoint:** `PATCH /assets`
**Test:** `tests/test_contract.py::TestAssetContract::test_patch_asset_nonexistent_returns_404`

**Steps to reproduce:**
```bash
curl -u test1:test123 -X PATCH http://localhost:8080/api/v1/assets \
  -H "Content-Type: application/json" \
  -d '{"id": "nonexistent-id", "name": "updated"}'
```

**Expected:** `404 Not Found`

**Actual:** `500 Internal Server Error`

**Evidence from test run:**
```
FAILED test_patch_asset_nonexistent_returns_404 — assert 500 == 404
```

**Impact:** Internal server errors leak implementation details and indicate unhandled exceptions. The server should handle this gracefully with a 404.

---

## BUG-011 — DELETE /assets/{id} returns 204 on nonexistent asset instead of 404

**Severity:** Medium
**Endpoint:** `DELETE /assets/{id}`
**Test:** `tests/test_contract.py::TestAssetContract::test_delete_asset_nonexistent_returns_404`

**Steps to reproduce:**
```bash
curl -i -u test1:test123 -X DELETE http://localhost:8080/api/v1/assets/999999
```

**Expected:** `404 Not Found` — asset does not exist

**Actual:** `204 No Content` — server reports successful deletion of a non-existent resource

**Evidence from test run:**
```
FAILED test_delete_asset_nonexistent_returns_404 — assert 204 == 404
```

**Impact:** Callers cannot distinguish between a successful deletion and an attempt to delete a resource that never existed. Idempotency is violated in a misleading way.

---

## BUG-012 — Swagger UI missing Authorize button

**Severity:** Medium (Documentation)
**Location:** `http://localhost:8080/swagger/index.html`

**Description:** The OpenAPI/Swagger UI does not display an Authorize button or padlock icon, despite the API requiring Basic Authentication on all endpoints. The `securitySchemes` section is either missing or incorrectly defined in the OpenAPI spec.

**Expected:** Authorize button visible in Swagger UI allowing testers to enter credentials and test endpoints interactively.

**Actual:** No Authorize button present. Cannot authenticate through the Swagger UI.

**Impact:** Developers and testers cannot use the Swagger UI to explore or test the API without external tools (curl, Postman). Onboarding friction is significantly increased.

---

## Reproduction Instructions

To reproduce all bugs in a single command:

```bash
# 1. Start the API
docker run -d -p 8080:8080 infralightio/test-integration-api

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the full test suite
pytest --tb=short -q

# 4. Open the HTML report
start reports/report.html   # Windows
open reports/report.html    # Mac/Linux
```

---

## Notes on Skipped Tests

9 tests in `test_tenant.py` were marked as **skipped** rather than failed. This is because `integration2` (the fixture for user2's integration) could not be created reliably — `POST /integrations` for user2 hung and timed out consistently across 3 retry attempts. This is a direct manifestation of **BUG-007**. The skipped tests would be expected to confirm the tenant isolation failures documented in **BUG-005** and **BUG-007**.
