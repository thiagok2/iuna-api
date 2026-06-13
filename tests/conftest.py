import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture(scope="module")
def client():
    """
    Test client fixture that can be used across integration/request tests.
    """
    with TestClient(app) as c:
        yield c
