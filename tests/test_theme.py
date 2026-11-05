import os
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_theme_config_default():
    res = client.get("/api/theme/config")
    assert res.status_code == 200
    data = res.json()
    assert "logo_url" in data
    assert "footer_text" in data
    assert "CDIF4EOSC" in data["footer_text"]
    assert "101292473" in data["footer_text"]

def test_theme_config_env_override(monkeypatch):
    test_logo = "https://example.org/custom-logo.png"
    monkeypatch.setenv("LOGO_URL", test_logo)
    res = client.get("/api/theme/config")
    assert res.status_code == 200
    data = res.json()
    assert data["logo_url"] == test_logo
