import math
import os
import re
from dataclasses import dataclass, field
from typing import Mapping

from stock_pipeline.errors import PermanentError


def required(env: Mapping[str, str], name: str) -> str:
    value = env.get(name, "").strip()
    if not value or value.lower().startswith("replace-with"):
        raise PermanentError(f"Set {name} in .env before running the pipeline.")
    return value


def symbols_from_env(env: Mapping[str, str] | None = None) -> list[str]:
    env = os.environ if env is None else env
    symbols = list(dict.fromkeys(s.strip().upper() for s in env.get("STOCK_SYMBOLS", "IBM").split(",")))
    if not symbols or any(not re.fullmatch(r"[A-Z0-9][A-Z0-9.^_-]{0,31}", s) for s in symbols):
        raise PermanentError("STOCK_SYMBOLS must contain comma-separated ticker symbols.")
    return symbols


def number(env: Mapping[str, str], name: str, default: str, low: float, high: float) -> float:
    try:
        value = float(env.get(name, default))
        if not math.isfinite(value) or not low <= value <= high:
            raise ValueError
        return value
    except ValueError:
        raise PermanentError(f"{name} must be a number between {low} and {high}.") from None


@dataclass(frozen=True)
class Settings:
    api_key: str = field(repr=False)
    db_password: str = field(repr=False)
    db_host: str = "stock-db"
    db_port: int = 5432
    db_name: str = "stocks"
    db_user: str = "stocks"
    connect_timeout: float = 10
    read_timeout: float = 30
    min_interval: float = 15

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "Settings":
        env = os.environ if env is None else env
        port = number(env, "STOCK_DB_PORT", "5432", 1, 65535)
        if not port.is_integer():
            raise PermanentError("STOCK_DB_PORT must be an integer.")
        return cls(
            api_key=required(env, "ALPHA_VANTAGE_API_KEY"),
            db_password=required(env, "STOCK_DB_PASSWORD"),
            db_host=env.get("STOCK_DB_HOST", "stock-db"),
            db_port=int(port),
            db_name=env.get("STOCK_DB_NAME", "stocks"),
            db_user=env.get("STOCK_DB_USER", "stocks"),
            connect_timeout=number(env, "HTTP_CONNECT_TIMEOUT", "10", 1, 60),
            read_timeout=number(env, "HTTP_READ_TIMEOUT", "30", 1, 120),
            min_interval=number(env, "API_MIN_INTERVAL_SECONDS", "15", 0, 300),
        )
