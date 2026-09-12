CREATE TABLE IF NOT EXISTS public.stock_prices (
    symbol VARCHAR(32) NOT NULL,
    trading_date DATE NOT NULL,
    open NUMERIC(20,8) NOT NULL CHECK (open > 0),
    high NUMERIC(20,8) NOT NULL CHECK (high > 0),
    low NUMERIC(20,8) NOT NULL CHECK (low > 0),
    close NUMERIC(20,8) NOT NULL CHECK (close > 0),
    volume BIGINT NOT NULL CHECK (volume >= 0),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (symbol, trading_date),
    CHECK (low <= open AND low <= close AND high >= open AND high >= close)
);
