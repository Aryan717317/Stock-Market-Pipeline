import logging
import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

from stock_pipeline.errors import PermanentError

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Observation:
    symbol: str
    trading_date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int

    def as_tuple(self) -> tuple:
        return (self.symbol, self.trading_date, self.open, self.high, self.low, self.close, self.volume)


def price(value: object) -> Decimal:
    if not isinstance(value, (str, int, Decimal)) or isinstance(value, bool):
        raise ValueError("price must be a decimal string or integer")
    try:
        result = Decimal(value)
        if not result.is_finite() or not 0 < result < Decimal("1000000000000"):
            raise ValueError("price must be positive, finite, and fit NUMERIC(20,8)")
        if result != result.quantize(Decimal("0.00000001")):
            raise ValueError("price has more than eight fractional digits")
        return result
    except InvalidOperation:
        raise ValueError("invalid decimal price") from None


def parse_daily(payload: dict, symbol: str) -> tuple[list[Observation], int]:
    metadata = payload.get("Meta Data")
    if not isinstance(metadata, dict) or str(metadata.get("2. Symbol", "")).upper() != symbol:
        raise PermanentError("Provider metadata is missing or does not match the requested symbol.")
    series = payload.get("Time Series (Daily)")
    if not isinstance(series, dict) or not series:
        raise PermanentError("Provider returned no daily observations.")
    records: list[Observation] = []
    rejected = 0
    for raw_date, values in series.items():
        try:
            if not isinstance(raw_date, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw_date):
                raise ValueError("invalid trading date format")
            trading_date = date.fromisoformat(raw_date)
            if not isinstance(values, dict):
                raise ValueError("observation must be an object")
            opening, high, low, close = (price(values[k]) for k in ("1. open", "2. high", "3. low", "4. close"))
            raw_volume = values["5. volume"]
            if isinstance(raw_volume, bool) or not re.fullmatch(r"\d{1,19}", str(raw_volume)):
                raise ValueError("volume must be a nonnegative integer")
            volume = int(raw_volume)
            if volume > 9223372036854775807:
                raise ValueError("volume exceeds BIGINT capacity")
            if not low <= min(opening, close) <= max(opening, close) <= high:
                raise ValueError("inconsistent OHLC prices")
            records.append(Observation(symbol, trading_date, opening, high, low, close, volume))
        except (KeyError, ValueError, TypeError) as exc:
            rejected += 1
            # Never log the raw response or rejected values.
            reason = "required field missing" if isinstance(exc, KeyError) else str(exc)
            log.warning("symbol=%s rejected_record=%s reason=%s", symbol, rejected, reason)
    if not records:
        raise PermanentError(f"No valid observations remained; rejected={rejected}.")
    return sorted(records, key=lambda record: record.trading_date), rejected
