import logging
import time

from stock_pipeline.config import Settings, symbols_from_env
from stock_pipeline.errors import PermanentError, TransientError
from stock_pipeline.pipeline import ingest_symbol

log = logging.getLogger(__name__)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    try:
        settings = Settings.from_env()
        symbols = symbols_from_env()
    except PermanentError as exc:
        log.error("configuration_failed: %s", exc)
        return 1
    failed = False
    for symbol in symbols:
        for attempt in range(3):
            try:
                ingest_symbol(symbol, settings)
                break
            except PermanentError as exc:
                log.error("symbol=%s failed: %s", symbol, exc)
                failed = True
                break
            except TransientError as exc:
                if attempt == 2:
                    log.error("symbol=%s retries_exhausted: %s", symbol, exc)
                    failed = True
                    break
                wait = max(30 * (2 ** attempt), exc.retry_after)
                log.warning("symbol=%s retry_in_seconds=%s reason=%s", symbol, wait, exc)
                time.sleep(wait)
    return int(failed)
