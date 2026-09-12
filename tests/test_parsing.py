from datetime import date
from decimal import Decimal

import pytest

from stock_pipeline.errors import PermanentError
from stock_pipeline.parsing import parse_daily


def test_extracts_all_records_in_date_order_without_rounding(payload):
    records, rejected = parse_daily(payload, "IBM")
    assert rejected == 0
    assert len(records) == 2
    assert records[0].trading_date == date(2026, 9, 9)
    assert records[1].open == Decimal("250.1200")
    assert records[1].close == Decimal("252.2500")
    assert records[1].volume == 1234567


@pytest.mark.parametrize("field,value", [
    ("1. open", None), ("1. open", "NaN"), ("1. open", "Infinity"),
    ("1. open", "-1"), ("1. open", 250.12), ("1. open", True),
    ("1. open", "250.123456789"), ("1. open", "1000000000000"),
    ("2. high", "200"), ("3. low", "300"),
    ("5. volume", "-1"), ("5. volume", "1.5"), ("5. volume", True),
    ("5. volume", "9223372036854775808"),
])
def test_rejects_bad_record_but_preserves_valid_record(payload, field, value, caplog):
    payload["Time Series (Daily)"]["2026-09-10"][field] = value
    records, rejected = parse_daily(payload, "IBM")
    assert len(records) == 1
    assert rejected == 1
    assert "rejected_record=1" in caplog.text


def test_missing_field_is_rejected(payload):
    del payload["Time Series (Daily)"]["2026-09-10"]["4. close"]
    records, rejected = parse_daily(payload, "IBM")
    assert len(records) == rejected == 1


@pytest.mark.parametrize("bad_date", ["2026-02-30", "20260910", "not-a-date"])
def test_invalid_date_is_rejected(payload, bad_date):
    series = payload["Time Series (Daily)"]
    series[bad_date] = series.pop("2026-09-10")
    records, rejected = parse_daily(payload, "IBM")
    assert len(records) == rejected == 1


@pytest.mark.parametrize("series", [{}, None, [], {"2026-09-10": {}}])
def test_empty_or_unusable_series_fails(payload, series):
    payload["Time Series (Daily)"] = series
    with pytest.raises(PermanentError):
        parse_daily(payload, "IBM")


@pytest.mark.parametrize("metadata", [None, {}, {"2. Symbol": "MSFT"}, {"2. Symbol": None}])
def test_missing_or_mismatched_metadata_fails(payload, metadata):
    payload["Meta Data"] = metadata
    with pytest.raises(PermanentError):
        parse_daily(payload, "IBM")


def test_zero_volume_is_valid(payload):
    payload["Time Series (Daily)"]["2026-09-10"]["5. volume"] = "0"
    records, rejected = parse_daily(payload, "IBM")
    assert rejected == 0
    assert records[-1].volume == 0
