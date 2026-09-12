"""Fetch configured symbols and upsert PostgreSQL; exit nonzero if any fail."""
from stock_pipeline.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
