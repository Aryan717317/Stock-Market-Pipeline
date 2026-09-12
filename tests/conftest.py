import json
from pathlib import Path

import pytest

from stock_pipeline.config import Settings


@pytest.fixture
def payload():
    return json.loads((Path(__file__).parent / "fixtures" / "daily.json").read_text())


@pytest.fixture
def settings():
    return Settings(api_key="unit-test-key", db_password="unit-test-password", min_interval=0)
