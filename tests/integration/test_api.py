def test_read_root_spec(client):
    """
    Test root path returns expected message
    """
    response = client.get("/")
    assert response.status_code == 200
    json_data = response.json()
    assert "Welcome to IUNA API" in json_data["message"]
    assert json_data["docs_url"] == "/docs"

def test_health_check_spec(client):
    """
    Test health check API endpoint
    """
    response = client.get("/api/v1/health-check")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "ok"
    assert "running smoothly" in json_data["message"]

def test_info_spec(client):
    """
    Test info API endpoint
    """
    response = client.get("/api/v1/info")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["name"] == "IUNA API"
    assert "version" in json_data
