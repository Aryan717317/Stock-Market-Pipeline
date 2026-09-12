# Minimum viable product

## Outcome

An evaluator configures a free Alpha Vantage key, starts Docker Compose, triggers an Airflow DAG, and verifies daily stock prices in PostgreSQL. Repeating the run preserves one row per symbol and trading date.

## Included

- Daily ingestion of the configured symbols, defaulting to `IBM`.
- Raw daily OHLCV JSON from `TIME_SERIES_DAILY`, using the free-compatible `compact` response.
- One independently retryable Airflow task per symbol, with serialized execution to limit API usage.
- A reusable Python pipeline and standalone command-line script.
- Validation, explicit failure categories, bounded retries, and useful logs.
- Transactional PostgreSQL upserts and persistent storage.
- Automated, repeatable initialization and a local authenticated Airflow UI.
- Tests, setup documentation, and the four assignment deliverables.

## Excluded

Intraday or real-time data, adjusted prices, unlimited historical backfills, a custom UI, trading recommendations, portfolio calculations, multiple API providers, distributed workers, and cloud hosting. These are not needed to demonstrate the assignment.

## Demonstration

1. Copy `.env.example` to `.env` and replace its secret placeholders.
2. Run `docker compose up --build -d` and wait for service health checks.
3. Open the Airflow UI and trigger `stock_market_pipeline`.
4. Query `stock_prices` to inspect dates, OHLC prices, and volume.
5. Trigger the DAG again. Verify that the duplicate-key query returns no rows.
6. Run the unit and PostgreSQL integration tests, including correction and rollback cases.
7. Inspect a failed task from an intentionally invalid symbol, then restore the configuration. Do not use an invalid key against the provider merely to demonstrate tests; failure fixtures cover that case offline.

## Completion criteria

The MVP is demonstrated only after the containers are healthy, the DAG has run against the live provider, and PostgreSQL contains valid data. Unit tests alone do not establish live integration. See `VERIFICATION.md` for the checks actually executed in the build environment.

## Known boundaries

The compact endpoint returns a limited recent history, not every historical date. Weekends and holidays need not add rows. Provider availability and free-tier quotas remain external constraints. The deployment runs on one Docker host and is intended for local assessment use.
