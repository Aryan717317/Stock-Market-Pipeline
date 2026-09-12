from datetime import datetime, timedelta, timezone

from airflow.sdk import dag, task
from airflow.sdk.exceptions import AirflowFailException


@dag(
    dag_id="stock_market_pipeline",
    description="Fetch and upsert daily stock observations from Alpha Vantage.",
    schedule="0 2 * * *",
    start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
    catchup=False,
    is_paused_upon_creation=False,
    max_active_runs=1,
    max_active_tasks=1,
    default_args={"owner": "data-pipeline", "retries": 2,
                  "retry_delay": timedelta(minutes=5), "execution_timeout": timedelta(minutes=10)},
    tags=["stocks", "assignment"],
)
def stock_market_pipeline():
    @task(retries=0)
    def configured_symbols():
        from stock_pipeline.config import symbols_from_env
        from stock_pipeline.errors import PermanentError

        try:
            return symbols_from_env()
        except PermanentError as exc:
            raise AirflowFailException(str(exc)) from None

    @task
    def ingest(symbol: str):
        from stock_pipeline.config import Settings
        from stock_pipeline.errors import PermanentError
        from stock_pipeline.pipeline import ingest_symbol

        try:
            return ingest_symbol(symbol, Settings.from_env())
        except PermanentError as exc:
            raise AirflowFailException(str(exc)) from None
        # TransientError propagates. Airflow waits five minutes before retrying,
        # at least the maximum Retry-After accepted by the HTTP client.

    ingest.expand(symbol=configured_symbols())


stock_market_pipeline()
