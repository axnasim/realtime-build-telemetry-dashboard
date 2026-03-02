import os
import pytest


@pytest.fixture(scope="session", autouse=True)
def ensure_data_dir():
    """Ensure the data/ directory exists (MetricsStorage default path)."""
    os.makedirs("data", exist_ok=True)
