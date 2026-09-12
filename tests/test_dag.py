from pathlib import Path

import pytest

pytestmark = pytest.mark.airflow


def test_dag_loads_without_external_connections(monkeypatch):
    pytest.importorskip("airflow")
    import psycopg2
    import requests
    from airflow.models import DagBag

    def forbidden(*args, **kwargs):
        raise AssertionError("DAG import must not contact external services")

    monkeypatch.setattr(requests.Session, "get", forbidden)
    monkeypatch.setattr(psycopg2, "connect", forbidden)
    bag = DagBag(dag_folder=str(Path(__file__).resolve().parents[1] / "dags"))
    assert bag.import_errors == {}
    dag = bag.dags["stock_market_pipeline"]
    assert dag.catchup is False
    assert dag.max_active_runs == 1
    assert dag.max_active_tasks == 1
    assert set(dag.task_ids) == {"configured_symbols", "ingest"}
