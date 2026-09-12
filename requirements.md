# Requirements

## Source and interpretation

Source: the supplied two-page assignment, “Dockerized Data Pipeline with Airflow/Dagster.” The brief permits either orchestrator and either an hourly or daily schedule. This implementation chooses Apache Airflow and a daily schedule. The source requests an existing PostgreSQL table but provides no schema; a repeatable setup step creates the designated table before ingestion. This is an implementation assumption, not an additional assignment requirement.

## Functional requirements

| ID | Requirement | Acceptance evidence |
| --- | --- | --- |
| F01 | Retrieve stock market JSON from a free API using Python `requests`. | HTTP client calls Alpha Vantage `TIME_SERIES_DAILY` with `compact` and JSON parameters; a live run persists observations. |
| F02 | Execute automatically on a daily schedule inside containerized Airflow. | DAG is discovered and unpaused; daily UTC schedule and manual triggering work. |
| F03 | Extract each returned daily observation’s symbol, trading date, open, high, low, close, and volume. | Parser fixtures verify values, types, source dates, and multiple observations. |
| F04 | Update the designated PostgreSQL table without duplicate observations. | PostgreSQL integration tests cover first insert, replay, and changed values for the same key. |
| F05 | Handle failures and missing data explicitly. | Tests cover HTTP, provider, malformed-response, validation, and transaction failures. |
| F06 | Configure symbols and secrets through environment variables. | Configuration tests and `.env.example`; no committed credentials. |
| F07 | Build and start all required services with one Compose command after configuration. | Fresh-volume startup with `docker compose up --build -d`. |
| F08 | Provide an independently runnable fetching and database-update script. | Script invokes the same functions used by the DAG and returns nonzero when a symbol fails. |

## Data contract

- Table: `public.stock_prices` in the application database.
- Primary key: `(symbol, trading_date)`.
- Prices: positive finite decimals stored as `NUMERIC(20,8)`; excess precision is rejected rather than silently rounded.
- Volume: nonnegative `BIGINT`.
- Trading dates: ISO dates from the provider, with no substitution from execution time.
- OHLC consistency: low is no greater than open or close; high is no less than open or close.
- Audit field: `updated_at TIMESTAMPTZ`, changed only when a row is inserted or its OHLCV values change.
- Invalid individual records are rejected with counts and reasons. Valid records may still be committed. An empty or entirely invalid response fails the symbol task.
- A valid replay is a successful no-op. No synthetic weekend or holiday rows are created.

## Operational requirements

| ID | Requirement | Implementation boundary |
| --- | --- | --- |
| O01 | Bounded retries and clear error reporting. | Retry transient HTTP/network/database failures; fail configuration, quota exhaustion, and invalid data explicitly. |
| O02 | Durable, atomic writes. | One transaction per symbol, persistent PostgreSQL volume, parameterized upserts. |
| O03 | Safe reruns and startup. | Non-destructive schema initialization; no dropping or truncating application tables. |
| O04 | Manage increased symbol counts. | Configurable symbols, indexed keys, batch writes, controlled task concurrency; API quota remains the capacity limit. |
| O05 | Reproducible environment. | Versioned Airflow/Python image, pinned Python dependencies, and documented PostgreSQL major version. |
| O06 | Useful local operation. | Health checks, authenticated UI bound to loopback, documented logs, queries, tests, stop/start, and reset procedure. |

## Required submission files

| Assignment deliverable | Project file |
| --- | --- |
| Docker Compose | `docker-compose.yml` |
| Orchestrator logic | `dags/stock_market_pipeline.py` |
| Fetching and database-update script | `scripts/fetch_stock_data.py`, using `stock_pipeline/` |
| Build and run instructions | `README.md` |

`AGENTS.md`, `MVP.md`, this file, and `architecture.md` are supporting project documents requested by the user. Tests and container initialization files support correctness and repeatability; they do not expand the product scope.

## Evaluation mapping

Correctness is established through parsing and real PostgreSQL tests. Error handling is established through failure fixtures and transaction rollback. Scalability is addressed through configurable symbols, bounded work, and indexed batch upserts. Code quality is addressed through shared functions and focused tests. Dockerization requires an actual container build and startup check, recorded separately from static validation.
