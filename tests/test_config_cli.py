from unittest.mock import patch

import pytest

from stock_pipeline import cli
from stock_pipeline.config import Settings, symbols_from_env
from stock_pipeline.errors import PermanentError, TransientError


def test_normalizes_and_deduplicates_symbols():
    assert symbols_from_env({"STOCK_SYMBOLS": "ibm, MSFT,ibm"}) == ["IBM", "MSFT"]


@pytest.mark.parametrize("value", ["", "IBM,", "IBM;DROP", " "])
def test_rejects_invalid_symbol_list(value):
    with pytest.raises(PermanentError):
        symbols_from_env({"STOCK_SYMBOLS": value})


def test_missing_key_fails_without_printing_database_password():
    with pytest.raises(PermanentError, match="ALPHA_VANTAGE_API_KEY"):
        Settings.from_env({"STOCK_DB_PASSWORD": "secret"})


def test_settings_repr_hides_secrets(settings):
    assert settings.api_key not in repr(settings)
    assert settings.db_password not in repr(settings)


@pytest.mark.parametrize("name,value", [
    ("HTTP_READ_TIMEOUT", "NaN"), ("HTTP_CONNECT_TIMEOUT", "-1"),
    ("API_MIN_INTERVAL_SECONDS", "Infinity"), ("STOCK_DB_PORT", "5432.5"),
])
def test_invalid_numeric_configuration(name, value):
    env = {"ALPHA_VANTAGE_API_KEY": "test-key", "STOCK_DB_PASSWORD": "test-password", name: value}
    with pytest.raises(PermanentError):
        Settings.from_env(env)


def test_cli_continues_after_symbol_failure_and_returns_nonzero(settings):
    with patch.object(cli.Settings, "from_env", return_value=settings), \
         patch.object(cli, "symbols_from_env", return_value=["IBM", "MSFT"]), \
         patch.object(cli, "ingest_symbol", side_effect=[PermanentError("invalid symbol"), {}]) as ingest:
        assert cli.main() == 1
        assert ingest.call_count == 2


def test_cli_retries_only_transient_failures(settings):
    with patch.object(cli.Settings, "from_env", return_value=settings), \
         patch.object(cli, "symbols_from_env", return_value=["IBM"]), \
         patch.object(cli, "ingest_symbol", side_effect=[TransientError("timeout", 90), {}]) as ingest, \
         patch.object(cli.time, "sleep") as sleep:
        assert cli.main() == 0
        assert ingest.call_count == 2
        sleep.assert_called_once_with(90)


def test_cli_bounds_attempts(settings):
    with patch.object(cli.Settings, "from_env", return_value=settings), \
         patch.object(cli, "symbols_from_env", return_value=["IBM"]), \
         patch.object(cli, "ingest_symbol", side_effect=TransientError("timeout")) as ingest, \
         patch.object(cli.time, "sleep"):
        assert cli.main() == 1
        assert ingest.call_count == 3
