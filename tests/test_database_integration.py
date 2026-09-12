import os
import uuid
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlparse

import psycopg2
import pytest

from stock_pipeline.database import upsert_records
from stock_pipeline.parsing import parse_daily

pytestmark = pytest.mark.integration


@pytest.fixture
def connection():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set TEST_DATABASE_URL to the dedicated stocks_test database.")
    if urlparse(url).path != "/stocks_test":
        pytest.fail("Integration tests only run against a database named stocks_test.")
    conn = psycopg2.connect(url)
    with conn:
        with conn.cursor() as cursor:
            cursor.execute((Path(__file__).resolve().parents[1] / "sql" / "schema.sql").read_text())
    yield conn
    conn.close()


@pytest.fixture
def records(payload, connection):
    symbol = "TEST_" + uuid.uuid4().hex[:20].upper()
    payload["Meta Data"]["2. Symbol"] = symbol
    rows, _ = parse_daily(payload, symbol)
    yield rows
    connection.rollback()
    with connection:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM public.stock_prices WHERE symbol = %s", (symbol,))


def count(connection, symbol):
    with connection.cursor() as cursor:
        cursor.execute("SELECT count(*) FROM public.stock_prices WHERE symbol = %s", (symbol,))
        return cursor.fetchone()[0]


def test_insert_then_replay_has_no_duplicates(connection, records):
    assert upsert_records(connection, records) == 2
    assert upsert_records(connection, records) == 0
    assert count(connection, records[0].symbol) == 2


def test_correction_updates_same_key(connection, records):
    upsert_records(connection, records)
    corrected = replace(records[0], close=Decimal("249.125"))
    assert upsert_records(connection, [corrected]) == 1
    assert count(connection, corrected.symbol) == 2
    with connection.cursor() as cursor:
        cursor.execute("SELECT close FROM public.stock_prices WHERE symbol=%s AND trading_date=%s",
                       (corrected.symbol, corrected.trading_date))
        assert cursor.fetchone()[0] == Decimal("249.125")


def test_failed_write_rolls_back_all_rows(connection, records):
    invalid = replace(records[1], volume=-1)
    with pytest.raises(psycopg2.IntegrityError):
        upsert_records(connection, [records[0], invalid])
    assert count(connection, records[0].symbol) == 0
