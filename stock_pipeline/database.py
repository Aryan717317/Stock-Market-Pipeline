from contextlib import closing

import psycopg2
from psycopg2.extras import execute_values

from stock_pipeline.config import Settings
from stock_pipeline.errors import PermanentError, TransientError
from stock_pipeline.parsing import Observation

UPSERT = """
INSERT INTO public.stock_prices AS current
    (symbol, trading_date, open, high, low, close, volume)
VALUES %s
ON CONFLICT (symbol, trading_date) DO UPDATE SET
    open = EXCLUDED.open, high = EXCLUDED.high, low = EXCLUDED.low,
    close = EXCLUDED.close, volume = EXCLUDED.volume,
    updated_at = CURRENT_TIMESTAMP
WHERE (current.open, current.high, current.low, current.close, current.volume)
    IS DISTINCT FROM
    (EXCLUDED.open, EXCLUDED.high, EXCLUDED.low, EXCLUDED.close, EXCLUDED.volume)
RETURNING 1
"""


def connect(settings: Settings):
    return psycopg2.connect(
        host=settings.db_host, port=settings.db_port, dbname=settings.db_name,
        user=settings.db_user, password=settings.db_password,
        connect_timeout=10, application_name="stock-market-pipeline",
        options="-c statement_timeout=60000 -c lock_timeout=10000",
    )


def upsert_records(connection, records: list[Observation]) -> int:
    """Commit the whole symbol, or roll it back; return inserted + changed rows."""
    if not records:
        return 0
    with connection:
        with connection.cursor() as cursor:
            changed = execute_values(cursor, UPSERT, [r.as_tuple() for r in records], page_size=100, fetch=True)
    return len(changed)


def store_records(settings: Settings, records: list[Observation]) -> int:
    try:
        with closing(connect(settings)) as connection:
            return upsert_records(connection, records)
    except psycopg2.Error as exc:
        if exc.pgcode and exc.pgcode.startswith("28"):
            raise PermanentError("PostgreSQL authentication failed; check database credentials.") from None
        if isinstance(exc, (psycopg2.OperationalError, psycopg2.InterfaceError)):
            raise TransientError("PostgreSQL is unavailable or the transaction was interrupted.") from None
        raise PermanentError("PostgreSQL rejected the write; check the schema and validated data.") from None
