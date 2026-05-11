# QA Automation Suite — infralightio/test-integration-api

## Overview
Automated test suite for the integration API service. Covers authentication, OpenAPI
contract validation, multi-tenant segregation, and load performance.

Built with: Python 3.11, pytest, requests & pydantic

## Run Everything (Single Command)

```bash
docker-compose up --abort-on-container-exit
```

This will:
1. Pull and start the API container
2. Wait for it to be healthy
3. Run the full test suite (auth + contract + tenant)
4. Save an HTML report to `reports/report.html`


## Run Locally (Development)

```bash
# 1. Start the API
docker run -d -p 8080:8080 infralightio/test-integration-api

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run all standard tests
pytest

# 4. Run a specific category
pytest -m auth        # authentication tests only
pytest -m contract    # contract validation only
pytest -m tenant      # tenant segregation only
pytest -m load        # load test (takes ~60s)

# 5. Run with verbose output and no HTML report
pytest -v --no-header -p no:html
```

## Project Structure

```
firefly-qa/
├── config/
│   └── settings.py         # All config — override via env vars or .env
├── clients/
│   └── api_client.py       # Typed API wrapper — no raw requests in tests
├── models/
│   └── schemas.py          # Pydantic models matching OpenAPI spec
├── tests/
│   ├── test_auth.py        # Authentication enforcement tests
│   ├── test_contract.py    # OpenAPI schema and status code validation
│   ├── test_tenant.py      # Multi-tenant segregation tests
│   └── test_load.py        # Performance: 1000 req/min requirement
├── reports/                # Generated HTML reports (git-ignored)
├── conftest.py             # Shared fixtures (clients, integrations)
├── pytest.ini
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── BUGS.md                 # All bugs found, with steps to reproduce
```


## Configuration

Override defaults via environment variables or a `.env` file:

| Variable | Default | Description |
|---|---|---|
| `BASE_URL` | `http://localhost:8080` | API base URL |
| `USER1_USERNAME` | `test1` | Tenant 1 username |
| `USER1_PASSWORD` | `test123` | Tenant 1 password |
| `USER2_USERNAME` | `test2` | Tenant 2 username |
| `USER2_PASSWORD` | `test456` | Tenant 2 password |
| `LOAD_REQUEST_COUNT` | `1000` | Number of requests for load test |
| `LOAD_MAX_WORKERS` | `50` | Thread pool size for load test |


## Test Report

After running, open `reports/report.html` in your browser.


## Adding New Tests

1. Choose the right file based on category (auth / contract / tenant / load)
2. Add your test to the appropriate class
3. Use fixtures from `conftest.py`; advisable to never create raw API clients in test functions
4. Mark your test with the appropriate marker (`@pytest.mark.contract`)
5. Use `unique("prefix")` for any names to avoid data collisions between runs

## Known Bugs

See [BUGS.md](./BUGS.md) for all bugs found during testing, with reproduction steps.
