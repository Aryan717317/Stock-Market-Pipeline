import logging

from stock_pipeline.api import fetch_daily
from stock_pipeline.config import Settings
from stock_pipeline.database import store_records
from stock_pipeline.parsing import parse_daily

log = logging.getLogger(__name__)


def ingest_symbol(symbol: str, settings: Settings) -> dict:
    symbol = symbol.strip().upper()
    payload = fetch_daily(symbol, settings)
    records, rejected = parse_daily(payload, symbol)
    changed = store_records(settings, records)
    result = {"symbol": symbol, "valid": len(records), "rejected": rejected,
              "inserted_or_updated": changed, "unchanged": len(records) - changed,
              "latest_date": records[-1].trading_date.isoformat()}
    log.info("ingestion_complete %s", result)
    return result
