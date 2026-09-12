# Dockerized stock market pipeline

Fetch daily stock observations from Alpha Vantage, validate the JSON response, and upsert PostgreSQL through a scheduled Apache Airflow DAG.

The application stores the source trading date, open, high, low, close, and volume. A unique key on symbol and trading date makes repeated runs safe. Corrected observations update the existing row.

## Assignment deliverables

| Deliverable | File |
| --- | --- |
| Docker Compose | [docker-compose.yml](docker-compose.yml) |
| Orchestrator logic | [dags/stock_market_pipeline.py](dags/stock_market_pipeline.py) |
| Fetching and database-update script | [scripts/fetch_stock_data.py](scripts/fetch_stock_data.py), backed by [stock_pipeline](stock_pipeline/) |
| Setup and operation guide | This README |

Additional documents: [MVP](MVP.md), [requirements](requirements.md), [architecture](architecture.md), [agent instructions](AGENTS.md), and [verification record](VERIFICATION.md).

## Prerequisites

- Docker Desktop running Linux containers, or Docker Engine on Linux.
- Docker Compose v2.24 or later.
- At least 4 GB of memory available to Docker; 8 GB is preferable for Airflow.
- A free [Alpha Vantage API key](https://www.alphavantage.co/support/#api-key).
- Network access to Docker Hub, the Python package index, the Airflow constraints file, and Alpha Vantage.

The application runs in Linux containers on Windows, macOS, or Linux. No host Python installation is required for the container workflow.

## Setup

Run all commands from this project directory.

Copy the environment template:

PowerShell:

```powershell
Copy-Item .env.example .env
```

Linux/macOS:

```bash
cp .env.example .env
```

Edit `.env` and replace every `replace-with` value. Supply your real API key, separate database passwords, a UI password, and a random JWT secret of at least 32 characters. Use your password manager to generate secrets. In Compose environment files, single-quote values containing `$`, `#`, or spaces. Do not commit this file.

Build and start everything:

```bash
docker compose up --build -d
docker compose ps -a
docker compose logs airflow-init
```

The initialization container should exit with code 0; the long-running services should become healthy. Startup includes metadata migration, stock table creation, and UI account creation. The first build downloads dependencies and can take several minutes.

Open [Airflow](http://localhost:8080) and sign in using `AIRFLOW_ADMIN_USERNAME` and `AIRFLOW_ADMIN_PASSWORD` from `.env`.

The `stock_market_pipeline` DAG is enabled when first discovered. It runs daily at **02:00 UTC**. Airflow schedules data intervals, so startup does not promise an immediate scheduled run. Trigger a manual run to demonstrate ingestion without waiting.

## Run and inspect

Trigger a run from the UI or CLI:

```bash
docker compose exec airflow-scheduler airflow dags trigger stock_market_pipeline
```

Inspect recent observations:

```bash
docker compose exec stock-db psql -U stocks -d stocks -c "SELECT symbol, trading_date, open, high, low, close, volume FROM stock_prices ORDER BY trading_date DESC, symbol LIMIT 10;"
```

Run the following before and after repeating the DAG. For an unchanged provider response, the count stays the same; a newly published trading date may legitimately increase it.

```bash
docker compose exec stock-db psql -U stocks -d stocks -c "SELECT symbol, count(*), max(trading_date) FROM stock_prices GROUP BY symbol;"
docker compose exec stock-db psql -U stocks -d stocks -c "SELECT symbol, trading_date, count(*) FROM stock_prices GROUP BY symbol, trading_date HAVING count(*) > 1;"
```

The duplicate-key query must return no rows.

To execute the same pipeline without creating an Airflow run:

```bash
docker compose run --rm --no-deps airflow-scheduler python -m scripts.fetch_stock_data
```

Run this only after initialization and database startup. It exits nonzero if any symbol fails. Avoid running it concurrently with scheduled ingestion using the same limited API key.

## Configuration

| Variable | Meaning | Default/example |
| --- | --- | --- |
| `ALPHA_VANTAGE_API_KEY` | Real provider key | Required |
| `STOCK_SYMBOLS` | Comma-separated symbols; normalized and deduplicated | `IBM` |
| `STOCK_DB_PASSWORD` | Application database password | Required |
| `AIRFLOW_DB_PASSWORD` | Metadata database password | Required |
| `AIRFLOW_ADMIN_USERNAME` | Local UI administrator | `admin` |
| `AIRFLOW_ADMIN_PASSWORD` | Local UI password | Required |
| `AIRFLOW_JWT_SECRET` | Shared Airflow signing secret | At least 32 random characters |
| `AIRFLOW_UI_PORT` | Local UI port | `8080` |
| `API_MIN_INTERVAL_SECONDS` | Delay before each provider request | `15` |
| `HTTP_CONNECT_TIMEOUT` | HTTP connection timeout in seconds | `10` |
| `HTTP_READ_TIMEOUT` | HTTP read timeout in seconds | `30` |

The Python script also accepts `STOCK_DB_HOST`, `STOCK_DB_PORT`, `STOCK_DB_NAME`, and `STOCK_DB_USER` when used outside Compose. Their defaults match the Compose application database. The script reads the process environment; it does not automatically load a local `.env`.

After changing symbols or other environment configuration, run `docker compose up --build -d` to recreate affected services. After changing the UI account, explicitly rerun initialization and recreate services:

```bash
docker compose run --rm airflow-init
docker compose up -d --force-recreate airflow-api-server airflow-scheduler airflow-dag-processor
```

Changing a PostgreSQL password in `.env` does not update an existing database role. Change the role password deliberately or use the destructive reset procedure only for disposable local data.

## Data and error behavior

The application uses Alpha Vantage `TIME_SERIES_DAILY` with `outputsize=compact`. The [provider documentation](https://www.alphavantage.co/documentation/#daily) describes the available recent history and free-key support. This is raw daily data, not adjusted or real-time data. Review the provider's current quota before increasing symbol counts.

Prices are parsed as decimal values and stored as `NUMERIC(20,8)`; volume is `BIGINT`. Invalid dates, missing fields, nonfinite or nonpositive prices, fractional or negative volumes, and inconsistent OHLC values are rejected. Valid rows from the same response can still be stored. An empty or entirely invalid series fails the task.

A transaction covers one symbol. PostgreSQL upserts insert new keys and update changed values. Identical values remain untouched, including `updated_at`. Other symbols' successful transactions survive a failed symbol.

Network failures, temporary HTTP errors, and transient database failures receive bounded retries. Airflow retries at most twice, five minutes apart. Explicit daily quota exhaustion, invalid keys/symbols, malformed data, and long provider cooldowns fail clearly. The standalone script owns its own bounded retries; the HTTP function never adds another retry loop.

Logs include symbol, valid/rejected counts, inserted-or-updated count, unchanged count, and latest source date. No sample output is presented as a real ingestion result.

Weekends, holidays, and publication delays can produce no new observations. The pipeline preserves existing data without fabricating rows. Repeated manual runs and retries consume the provider's request budget.

## Tests

The container test command uses fixtures for HTTP behavior and a separate ephemeral PostgreSQL database for SQL tests. It does not contact Alpha Vantage or need a real API key:

```bash
docker compose --env-file .env.example --profile test run --build --rm tests
```

The test profile is excluded from normal startup. Its `local-test-only` password is a disposable test fixture. It does not authenticate to either application database.

For local unit tests on Windows:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q -m "not integration and not airflow"
```

For local unit tests on Linux/macOS:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q -m "not integration and not airflow"
```

Tests cover parsing, provider failures, retry limits, configuration, PostgreSQL replay/correction/rollback, and real DAG import. Database tests require `TEST_DATABASE_URL` pointing to a database named `stocks_test`. They refuse other database names and clean up only their generated symbols. Airflow tests require the actual Airflow package. The container command supplies both.

## Troubleshooting and checks

```bash
docker compose config --quiet
docker compose ps -a
docker compose logs --tail 100 airflow-init airflow-api-server airflow-scheduler airflow-dag-processor
docker compose exec airflow-scheduler airflow dags list-import-errors
```

- **Docker cannot connect:** start Docker Desktop, wait until its Linux engine is ready, and retry `docker version`.
- **Initialization fails:** check that all environment placeholders were replaced and the JWT secret has at least 32 characters.
- **UI port occupied:** change `AIRFLOW_UI_PORT` in `.env` and recreate services.
- **DAG not visible immediately:** allow the DAG processor time to discover it, then check import errors and processor logs.
- **Provider quota reached:** wait for the provider reset; repeated manual retries can extend the problem.
- **No recent trading date:** inspect the latest date reported by the provider; daily data publication can lag the market close.
- **Database write rejected:** inspect the supplied schema and any existing table. Startup intentionally does not overwrite an incompatible schema.
- **Changed Python or DAG files:** rebuild the image; source files are copied into it rather than bind-mounted.

## Stop, restart, and reset

Preserve data while stopping and restarting:

```bash
docker compose stop
docker compose start
```

Remove containers while retaining named volumes:

```bash
docker compose down
docker compose up -d
```

**Destructive reset:** the following deletes this project's application data, Airflow history, UI account file, and logs. Use only when you intend to discard them.

```bash
docker compose --profile test down --volumes
docker compose up --build -d
```

## GitHub submission

Use this directory as the repository root. If it currently sits inside another project, copy this directory to a separate location before initializing its own Git repository. Include the source, configuration template, tests, and Markdown documents. Exclude `.env`, virtual environments, generated logs, and database files.

Before submission, run the container tests, demonstrate a live DAG run and replay, and update [VERIFICATION.md](VERIFICATION.md) with the actual outcomes. Do not claim a successful live run based on mocked tests.

The implementation has no remote repository configured by this build. Add your GitHub repository through your usual Git workflow after reviewing the files.
