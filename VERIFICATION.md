# Verification record

Checked on 2026-09-12 in the local Windows workspace.

| Check | Outcome |
| --- | --- |
| Python tests | 66 passed; 4 skipped. |
| Python syntax compilation | Passed for application, DAG, scripts, and tests. |
| Installed application/test dependencies | pip check reported no broken requirements. |
| Docker Compose configuration using .env.example | Passed static validation. |
| PostgreSQL insert/replay/correction/rollback | Tests written; 3 skipped because no test PostgreSQL server was available. |
| Real Airflow DAG import | Test written; skipped because Airflow was not installed in the Windows test environment. |
| Container image build and startup | Not verified: Docker Desktop's Linux engine endpoint was unavailable. |
| Live Alpha Vantage ingestion | Not run: a real API key was not supplied, and containers could not start. |
| GitHub publication | Not performed; no target remote repository was supplied. |

The local dependency versions were requests 2.34.2, psycopg2-binary 2.9.12, pytest 9.0.2, and PyYAML 6.0.3, on Python 3.12.14. The application dependency versions match the published Airflow 3.3.1 Python 3.12 constraints. This does not establish that the container build passed.

## Finish the runtime checks

After Docker Desktop's Linux engine is running:

1. Run `docker compose --env-file .env.example --profile test run --build --rm tests`. Confirm all tests pass, including the PostgreSQL and DAG tests; investigate unexpected skips.
2. Configure `.env` with a real API key and local credentials.
3. Run `docker compose up --build -d`. Confirm initialization exits successfully and all persistent services become healthy.
4. Trigger `stock_market_pipeline` and inspect the task logs and database queries documented in the README.
5. Repeat the run and verify there are no duplicate keys. A provider correction should update its existing key.
6. Replace the unverified entries above with the actual outcomes before submitting the repository.

Do not treat the mocked HTTP tests as proof of a live provider request or the static Compose check as proof that containers started.
