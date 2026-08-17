import json
import uuid

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_health_endpoint_returns_ok():
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_config_endpoint_returns_404_when_no_config(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))

    response = client.get("/api/config")

    assert response.status_code == 404


def test_config_endpoint_returns_saved_config(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    config_dir = tmp_path / "windows-ai-files"
    config_dir.mkdir()
    (config_dir / "config.json").write_text(
        json.dumps({"selectedFolder": r"C:\Users\Yusuf\Documents"}), encoding="utf-8"
    )

    response = client.get("/api/config")

    assert response.status_code == 200
    assert response.json() == {"selectedFolder": r"C:\Users\Yusuf\Documents"}


def test_config_endpoint_returns_404_when_config_is_corrupted(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    config_dir = tmp_path / "windows-ai-files"
    config_dir.mkdir()
    (config_dir / "config.json").write_text("{not valid json", encoding="utf-8")

    response = client.get("/api/config")

    assert response.status_code == 404


def test_cors_header_present_for_allowed_origin():
    response = client.get("/api/health", headers={"Origin": "tauri://localhost"})

    assert response.headers.get("access-control-allow-origin") == "tauri://localhost"


def test_session_endpoint_creates_a_session_with_a_uuid_and_echoes_input():
    response = client.post(
        "/api/session",
        json={"selectedFolder": r"C:\Users\Yusuf\Documents", "requestText": "PDF'leri tarihe göre sırala"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["selectedFolder"] == r"C:\Users\Yusuf\Documents"
    assert body["requestText"] == "PDF'leri tarihe göre sırala"
    assert uuid.UUID(body["sessionId"])


def test_session_endpoint_returns_422_for_empty_selected_folder():
    response = client.post(
        "/api/session",
        json={"selectedFolder": "", "requestText": "PDF'leri tarihe göre sırala"},
    )

    assert response.status_code == 422


def test_session_endpoint_returns_422_for_whitespace_only_request_text():
    response = client.post(
        "/api/session",
        json={"selectedFolder": r"C:\Users\Yusuf\Documents", "requestText": "   "},
    )

    assert response.status_code == 422


def test_session_endpoint_returns_422_for_missing_fields():
    response = client.post("/api/session", json={})

    assert response.status_code == 422


def test_cors_header_present_for_session_post_from_allowed_origin():
    response = client.post(
        "/api/session",
        json={"selectedFolder": r"C:\Users\Yusuf\Documents", "requestText": "bir istek"},
        headers={"Origin": "tauri://localhost"},
    )

    assert response.headers.get("access-control-allow-origin") == "tauri://localhost"
