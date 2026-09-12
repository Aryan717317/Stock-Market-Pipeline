import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import requests

from stock_pipeline.config import Settings
from stock_pipeline.errors import PermanentError, TransientError

API_URL = "https://www.alphavantage.co/query"
MAX_RETRY_WAIT = 300


def retry_wait(header: str | None) -> float:
    if not header:
        return 0
    try:
        seconds = float(header)
    except ValueError:
        try:
            target = parsedate_to_datetime(header)
            if target.tzinfo is None:
                target = target.replace(tzinfo=timezone.utc)
            seconds = (target - datetime.now(timezone.utc)).total_seconds()
        except (TypeError, ValueError, OverflowError):
            return 0
    if seconds != seconds or seconds > MAX_RETRY_WAIT:
        raise PermanentError("Provider requests a longer cooldown; retry in a later run.")
    return max(0, seconds)


def fetch_daily(symbol: str, settings: Settings) -> dict:
    """Make one attempt. The caller owns retries, so retry loops do not multiply."""
    time.sleep(settings.min_interval)
    try:
        with requests.Session() as session:
            response = session.get(
                API_URL,
                params={"function": "TIME_SERIES_DAILY", "symbol": symbol,
                        "outputsize": "compact", "datatype": "json", "apikey": settings.api_key},
                timeout=(settings.connect_timeout, settings.read_timeout),
                allow_redirects=False,
            )
            if response.status_code == 429 or 500 <= response.status_code <= 599:
                delay = retry_wait(response.headers.get("Retry-After"))
                raise TransientError(f"Provider returned HTTP {response.status_code}.", delay)
            if response.status_code != 200:
                raise PermanentError(f"Provider rejected the request (HTTP {response.status_code}).")
            if "application/json" not in response.headers.get("Content-Type", "").lower():
                raise PermanentError("Provider returned non-JSON content type.")
            try:
                payload = response.json()
            except ValueError:
                raise PermanentError("Provider returned invalid JSON.") from None
    except requests.RequestException:
        # Requests exceptions can contain the full URL, including the API key.
        raise TransientError("Provider connection failed or timed out.") from None

    if not isinstance(payload, dict):
        raise PermanentError("Provider response must be a JSON object.")
    for key in ("Error Message", "Note", "Information"):
        if key not in payload:
            continue
        message = str(payload[key]).lower()
        if "per day" in message or "daily" in message:
            raise PermanentError("Provider daily quota reached; wait for its quota reset.")
        if key == "Error Message" or any(s in message for s in ("api key", "apikey", "premium", "invalid")):
            raise PermanentError("Provider rejected the key, symbol, or requested endpoint; check configuration.")
        if any(s in message for s in ("rate", "frequency", "limit")):
            raise TransientError("Provider temporarily rate-limited the request.")
        raise PermanentError("Provider returned an information/error response instead of stock data.")
    return payload
