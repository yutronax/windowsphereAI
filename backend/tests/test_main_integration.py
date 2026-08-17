import json
import uuid

from fastapi.testclient import TestClient

from backend.main import app, get_llm_client

client = TestClient(app)


class _StubLLMClient:
    def __init__(self, response: str | None = None, error: bool = False):
        self.response = response
        self.error = error

    def complete(self, *, model: str, system_prompt: str, user_prompt: str) -> str:
        if self.error:
            raise RuntimeError("stub failure")
        assert self.response is not None
        return self.response


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


def test_session_endpoint_trims_leading_and_trailing_whitespace_from_request_text():
    response = client.post(
        "/api/session",
        json={"selectedFolder": r"C:\Users\Yusuf\Documents", "requestText": "  PDF'leri tarihe göre sırala  "},
    )

    assert response.status_code == 201
    assert response.json()["requestText"] == "PDF'leri tarihe göre sırala"


def test_session_endpoint_trims_leading_and_trailing_whitespace_from_selected_folder():
    response = client.post(
        "/api/session",
        json={"selectedFolder": r"  C:\Users\Yusuf\Documents  ", "requestText": "bir istek"},
    )

    assert response.status_code == 201
    assert response.json()["selectedFolder"] == r"C:\Users\Yusuf\Documents"


def test_cors_header_present_for_session_post_from_allowed_origin():
    response = client.post(
        "/api/session",
        json={"selectedFolder": r"C:\Users\Yusuf\Documents", "requestText": "bir istek"},
        headers={"Origin": "tauri://localhost"},
    )

    assert response.headers.get("access-control-allow-origin") == "tauri://localhost"


VALID_PLAN_JSON = json.dumps(
    {
        "dateSource": "created_at",
        "sortOrder": "ascending",
        "steps": [{"order": 0, "operationType": "Taşı", "targetFolder": "2026-08", "affectedFileCount": 1}],
    }
)


def _create_session(selected_folder: str = r"C:\Users\Yusuf\Documents") -> str:
    response = client.post(
        "/api/session",
        json={"selectedFolder": selected_folder, "requestText": "bir istek"},
    )
    return response.json()["sessionId"]


def test_plan_endpoint_returns_503_when_no_llm_api_key_configured(monkeypatch):
    monkeypatch.delenv("PLAN_LLM_API_KEY", raising=False)
    session_id = _create_session()

    response = client.post("/api/plan", json={"sessionId": session_id, "pdfFiles": [{"filename": "a.pdf", "createdAt": "2026-08-01"}]})

    assert response.status_code == 503


def test_plan_endpoint_returns_404_when_session_does_not_exist():
    app.dependency_overrides[get_llm_client] = lambda: _StubLLMClient(response=VALID_PLAN_JSON)
    try:
        response = client.post(
            "/api/plan",
            json={"sessionId": str(uuid.uuid4()), "pdfFiles": [{"filename": "a.pdf", "createdAt": "2026-08-01"}]},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404


def test_plan_endpoint_returns_the_plan_skeleton_for_a_valid_llm_response():
    session_id = _create_session()
    app.dependency_overrides[get_llm_client] = lambda: _StubLLMClient(response=VALID_PLAN_JSON)
    try:
        response = client.post(
            "/api/plan",
            json={"sessionId": session_id, "pdfFiles": [{"filename": "a.pdf", "createdAt": "2026-08-01"}]},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["steps"][0]["targetFolder"] == "2026-08"


def test_plan_endpoint_returns_502_when_plan_generation_fails():
    session_id = _create_session()
    app.dependency_overrides[get_llm_client] = lambda: _StubLLMClient(error=True)
    try:
        response = client.post(
            "/api/plan",
            json={"sessionId": session_id, "pdfFiles": [{"filename": "a.pdf", "createdAt": "2026-08-01"}]},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 502
    assert "detail" in response.json()


def test_plan_endpoint_returns_422_for_missing_fields():
    app.dependency_overrides[get_llm_client] = lambda: _StubLLMClient(response=VALID_PLAN_JSON)
    try:
        response = client.post("/api/plan", json={})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422


def test_plan_endpoint_returns_422_when_filename_contains_path_separators():
    # Saga #272: PdfFileMetadata.filename artık şema seviyesinde ayraç
    # içeremiyor — bu, çok-segmentli traversal/derinlik denemelerini
    # runtime whitelist'e (403) hiç ulaşmadan erkenden reddediyor.
    session_id = _create_session()
    app.dependency_overrides[get_llm_client] = lambda: _StubLLMClient(response=VALID_PLAN_JSON)
    try:
        response = client.post(
            "/api/plan",
            json={
                "sessionId": session_id,
                "pdfFiles": [{"filename": r"..\..\Windows\evil.pdf", "createdAt": "2026-08-01"}],
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422


def test_plan_endpoint_returns_403_when_source_filename_escapes_allowed_root():
    # Ayraçsız tek segment (".."), şema doğrulamasından geçer ama whitelist
    # tarafından runtime'da reddedilir.
    session_id = _create_session()
    app.dependency_overrides[get_llm_client] = lambda: _StubLLMClient(response=VALID_PLAN_JSON)
    try:
        response = client.post(
            "/api/plan",
            json={
                "sessionId": session_id,
                "pdfFiles": [{"filename": "..", "createdAt": "2026-08-01"}],
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
