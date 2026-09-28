"""Shared fixtures for the API tests.

main.py imports its siblings as top-level modules (``from simulator import
...``), so apps/api has to be on sys.path before it is imported.
"""
import os
import sys

import pytest

API_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if API_DIR not in sys.path:
    sys.path.insert(0, API_DIR)

import main  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from simulator import Fleet  # noqa: E402


@pytest.fixture
def fleet(monkeypatch):
    """A fresh, seeded fleet per test so state changes never leak."""
    f = Fleet()
    monkeypatch.setattr(main, "FLEET", f)
    return f


@pytest.fixture
def client(fleet):
    # Not used as a context manager on purpose: that would run the lifespan
    # and its background tick loop, making readings change under the tests.
    return TestClient(main.app)
