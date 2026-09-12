from unittest.mock import MagicMock, patch

import pytest
import requests

from stock_pipeline.api import fetch_daily, retry_wait
from stock_pipeline.errors import PermanentError, TransientError


def response(status=200, body=None, headers=None):
    value = MagicMock()
    value.status_code = status
    value.headers = headers or {}
    value.json.return_value = body
    return value


def call_with_response(value, settings):
    with patch("stock_pipeline.api.requests.Session") as session:
        client = session.return_value.__enter__.return_value
        client.get.return_value = value
        result = fetch_daily("IBM", settings)
        return result, client.get.call_args


def test_calls_json_endpoint_with_timeout(payload, settings):
    result, args = call_with_response(response(body=payload), settings)
    assert result == payload
    assert args.kwargs["params"]["function"] == "TIME_SERIES_DAILY"
    assert args.kwargs["params"]["outputsize"] == "compact"
    assert args.kwargs["params"]["apikey"] == settings.api_key
    assert args.kwargs["timeout"] == (10, 30)
    assert args.kwargs["allow_redirects"] is False


@pytest.mark.parametrize("status", [429, 500, 502, 503])
def test_transient_http_errors(status, settings):
    with pytest.raises(TransientError):
        call_with_response(response(status), settings)


@pytest.mark.parametrize("status", [301, 400, 401, 403, 404])
def test_permanent_http_errors(status, settings):
    with pytest.raises(PermanentError):
        call_with_response(response(status), settings)


@pytest.mark.parametrize("body,exception", [
    ({"Error Message": "Invalid API call"}, PermanentError),
    ({"Information": "Invalid API key"}, PermanentError),
    ({"Information": "25 requests per day"}, PermanentError),
    ({"Note": "API call frequency limit"}, TransientError),
    ({"Information": "This is a premium endpoint"}, PermanentError),
    ([], PermanentError),
])
def test_provider_body_errors(body, exception, settings):
    with pytest.raises(exception):
        call_with_response(response(body=body), settings)


def test_network_error_does_not_expose_key(settings):
    with patch("stock_pipeline.api.requests.Session") as session:
        session.return_value.__enter__.return_value.get.side_effect = requests.Timeout(
            "https://example.com?apikey=unit-test-key"
        )
        with pytest.raises(TransientError) as caught:
            fetch_daily("IBM", settings)
    assert "unit-test-key" not in str(caught.value)
    assert caught.value.__suppress_context__


def test_invalid_json_fails(settings):
    value = response()
    value.json.side_effect = ValueError("invalid")
    with pytest.raises(PermanentError, match="invalid JSON"):
        call_with_response(value, settings)


def test_retry_after_is_preserved(settings):
    with pytest.raises(TransientError) as caught:
        call_with_response(response(429, headers={"Retry-After": "120"}), settings)
    assert caught.value.retry_after == 120


def test_long_cooldown_is_not_retried_early(settings):
    with pytest.raises(PermanentError, match="longer cooldown"):
        call_with_response(response(429, headers={"Retry-After": "3600"}), settings)


@pytest.mark.parametrize("header,expected", [(None, 0), ("bad", 0), ("-1", 0), ("30", 30)])
def test_retry_wait(header, expected):
    assert retry_wait(header) == expected
