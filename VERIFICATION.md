# Verification record

Checked on 2026-09-12 in the local Windows workspace.

| Check | Outcome |
| --- | --- |
| Local Python unit tests | 67 passed, 4 deselected (integration/airflow markers). |
| Container test suite (Docker) | 71 passed, 0 failed, 0 warnings (`docker compose --profile test run --build --rm tests`). |
| Python syntax compilation | Passed for all application, DAG, script, and test files. |
| Installed application/test dependencies | `pip check` reported no broken requirements. |
| Docker Compose configuration | Passed static validation. |
| PostgreSQL insert/replay/correction/rollback | Verified in container with PostgreSQL 16 (`test-db`). |
| Real Airflow DAG import | Verified in container using Airflow 3 runtime (`BundleDagBag`). |
| Container image build and startup | Verified — `airflow-init` completed (exit 0); all 5 services healthy. |
| Scheduler DAG execution & live API check | Verified — scheduler triggered `stock_market_pipeline`; live Alpha Vantage API ingested 100 observations into PostgreSQL. |
| Replay idempotency & duplicate prevention | Verified — replay run produced 0 duplicates (count remained 100); CLI standalone execution verified. |
| GitHub publication | Published to https://github.com/Aryan717317/Stock-Market-Pipeline.git on `main`. |

The application and container dependency versions match the published Airflow 3.3.1 Python 3.12 constraints. All 71 tests passed against real PostgreSQL 16 and Airflow 3 containers.

## Completed runtime verification

All end-to-end runtime checks have been executed and verified live:

1. **Automated Test Suite:** `docker compose --env-file .env.example --profile test run --build --rm tests` passed all 71 tests, including PostgreSQL 16 schema/transaction tests and Airflow 3 DAG validation.
2. **Container Infrastructure:** `docker compose up --build -d` initialized databases, ran migrations (`airflow-init` exited 0), and all services (`airflow-api-server`, `airflow-scheduler`, `airflow-dag-processor`, `airflow-db`, `stock-db`) became healthy.
3. **Live Orchestration Run:** Triggered `stock_market_pipeline` via Airflow. Tasks `configured_symbols` and `ingest` succeeded, inserting 100 daily observations for `IBM`.
4. **Replay Idempotency:** Subsequent execution processed 100 observations with 0 duplicate key errors and `SELECT count(*) FROM stock_prices;` remained exactly 100.
5. **Standalone Fetch CLI:** Executed `python scripts/fetch_stock_data.py --symbol IBM` inside the container, confirming `valid: 100, rejected: 0, unchanged: 100`.
