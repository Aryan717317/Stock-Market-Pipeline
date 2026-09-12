"""Airflow's *_CMD setting consumes this value; never run it to inspect secrets."""
import os
import sys
from urllib.parse import quote

if __name__ == "__main__":
    password = quote(os.environ["AIRFLOW_DB_PASSWORD"], safe="")
    sys.stdout.write(f"postgresql+psycopg2://airflow:{password}@airflow-db:5432/airflow")

