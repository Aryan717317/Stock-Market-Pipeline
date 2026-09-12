import json
import os
import re
import subprocess
from contextlib import closing
from pathlib import Path

from stock_pipeline.config import Settings, required, symbols_from_env
from stock_pipeline.database import connect
from stock_pipeline.errors import PermanentError

ROOT = Path(__file__).resolve().parents[1]


def main():
    settings = Settings.from_env()
    symbols_from_env()
    required(os.environ, "AIRFLOW_DB_PASSWORD")
    username = required(os.environ, "AIRFLOW_ADMIN_USERNAME")
    password = required(os.environ, "AIRFLOW_ADMIN_PASSWORD")
    secret = required(os.environ, "AIRFLOW__API_AUTH__JWT_SECRET")
    if len(secret) < 32:
        raise PermanentError("AIRFLOW_JWT_SECRET must contain at least 32 random characters.")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", username):
        raise PermanentError("AIRFLOW_ADMIN_USERNAME may contain letters, digits, underscores, periods, or hyphens.")

    subprocess.run(["airflow", "db", "migrate"], check=True)
    with closing(connect(settings)) as connection:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute((ROOT / "sql" / "schema.sql").read_text(encoding="utf-8"))

    target = Path(os.environ["AIRFLOW__CORE__SIMPLE_AUTH_MANAGER_PASSWORDS_FILE"])
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".tmp")
    temporary.write_text(json.dumps({username: password}), encoding="utf-8")
    temporary.chmod(0o600)
    temporary.replace(target)
    print("Airflow metadata, stock schema, and UI account initialized.")


if __name__ == "__main__":
    try:
        main()
    except PermanentError as exc:
        raise SystemExit(str(exc)) from None
