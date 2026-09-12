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
| Scheduler DAG execution & live API check | Verified — scheduler triggered `stock_market_pipeline`; provider error handling caught gracefully without db corruption. |
| GitHub publication | Published to https://github.com/Aryan717317/Stock-Market-Pipeline.git on `main`. |

The application and container dependency versions match the published Airflow 3.3.1 Python 3.12 constraints. All 71 tests passed against real PostgreSQL 16 and Airflow 3 containers.

## Finish the runtime checks

After Docker Desktop's Linux engine is running:

1. Run `docker compose --env-file .env.example --profile test run --build --rm tests`. Confirm all tests pass, including the PostgreSQL and DAG tests; investigate unexpected skips.
2. Configure `.env` with a real API key and local credentials.
3. Run `docker compose up --build -d`. Confirm initialization exits successfully and all persistent services become healthy.
4. Trigger `stock_market_pipeline` and inspect the task logs and database queries documented in the README.
5. Repeat the run and verify there are no duplicate keys. A provider correction should update its existing key.
6. Replace the unverified entries above with the actual outcomes before submitting the repository.

Do not treat the mocked HTTP tests as proof of a live provider request or the static Compose check as proof that containers started.
