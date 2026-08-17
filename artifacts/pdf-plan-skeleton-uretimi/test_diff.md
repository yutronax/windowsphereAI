diff --git a/backend/tests/test_main_integration.py b/backend/tests/test_main_integration.py
index 7c5b1aa..c851a49 100644
--- a/backend/tests/test_main_integration.py
+++ b/backend/tests/test_main_integration.py
@@ -3,11 +3,23 @@ import uuid
 
 from fastapi.testclient import TestClient
 
-from backend.main import app
+from backend.main import app, get_llm_client
 
 client = TestClient(app)
 
 
+class _StubLLMClient:
+    def __init__(self, response: str | None = None, error: bool = False):
+        self.response = response
+        self.error = error
+
+    def complete(self, *, model: str, system_prompt: str, user_prompt: str) -> str:
+        if self.error:
+            raise RuntimeError("stub failure")
+        assert self.response is not None
+        return self.response
+
+
 def test_health_endpoint_returns_ok():
     response = client.get("/api/health")
 
@@ -119,3 +131,54 @@ def test_cors_header_present_for_session_post_from_allowed_origin():
     )
 
     assert response.headers.get("access-control-allow-origin") == "tauri://localhost"
+
+
+VALID_PLAN_JSON = json.dumps(
+    {"steps": [{"order": 0, "operationType": "Taşı", "targetFolder": "2026-08", "affectedFileCount": 1}]}
+)
+
+
+def test_plan_endpoint_returns_503_when_no_llm_api_key_configured(monkeypatch):
+    monkeypatch.delenv("PLAN_LLM_API_KEY", raising=False)
+
+    response = client.post("/api/plan", json={"sessionId": str(uuid.uuid4()), "pdfFiles": [{"filename": "a.pdf", "createdAt": "2026-08-01"}]})
+
+    assert response.status_code == 503
+
+
+def test_plan_endpoint_returns_the_plan_skeleton_for_a_valid_llm_response():
+    app.dependency_overrides[get_llm_client] = lambda: _StubLLMClient(response=VALID_PLAN_JSON)
+    try:
+        response = client.post(
+            "/api/plan",
+            json={"sessionId": str(uuid.uuid4()), "pdfFiles": [{"filename": "a.pdf", "createdAt": "2026-08-01"}]},
+        )
+    finally:
+        app.dependency_overrides.clear()
+
+    assert response.status_code == 200
+    assert response.json()["steps"][0]["targetFolder"] == "2026-08"
+
+
+def test_plan_endpoint_returns_502_when_plan_generation_fails():
+    app.dependency_overrides[get_llm_client] = lambda: _StubLLMClient(error=True)
+    try:
+        response = client.post(
+            "/api/plan",
+            json={"sessionId": str(uuid.uuid4()), "pdfFiles": [{"filename": "a.pdf", "createdAt": "2026-08-01"}]},
+        )
+    finally:
+        app.dependency_overrides.clear()
+
+    assert response.status_code == 502
+    assert "detail" in response.json()
+
+
+def test_plan_endpoint_returns_422_for_missing_fields():
+    app.dependency_overrides[get_llm_client] = lambda: _StubLLMClient(response=VALID_PLAN_JSON)
+    try:
+        response = client.post("/api/plan", json={})
+    finally:
+        app.dependency_overrides.clear()
+
+    assert response.status_code == 422
--- new file: backend/tests/test_plan_generation.py ---
import json

import pytest

from backend.models import PdfFileMetadata, PlanSkeleton
from backend.plan_generation import (
    DEFAULT_MODEL_ID,
    PlanGenerationError,
    build_metadata_prompt,
    generate_plan_skeleton,
    resolve_model_id,
)


class FakeLLMClient:
    def __init__(self, response: str | None = None, exception: Exception | None = None):
        self.response = response
        self.exception = exception
        self.last_call: dict | None = None

    def complete(self, *, model: str, system_prompt: str, user_prompt: str) -> str:
        self.last_call = {"model": model, "system_prompt": system_prompt, "user_prompt": user_prompt}
        if self.exception is not None:
            raise self.exception
        assert self.response is not None
        return self.response


VALID_PLAN_JSON = json.dumps(
    {
        "steps": [
            {"order": 0, "operationType": "Taşı", "targetFolder": "2026-08", "affectedFileCount": 2},
            {"order": 1, "operationType": "Taşı", "targetFolder": "2026-07", "affectedFileCount": 1},
        ]
    }
)

ONE_PDF = [PdfFileMetadata(filename="fatura.pdf", createdAt="2026-08-01")]


def test_returns_a_valid_plan_skeleton_from_a_valid_llm_response():
    client = FakeLLMClient(response=VALID_PLAN_JSON)

    result = generate_plan_skeleton(ONE_PDF, client)

    assert isinstance(result, PlanSkeleton)
    assert len(result.steps) == 2
    assert result.steps[0].targetFolder == "2026-08"


def test_returns_an_empty_plan_without_calling_the_llm_when_no_pdf_files():
    client = FakeLLMClient(response="should not be used")

    result = generate_plan_skeleton([], client)

    assert result == PlanSkeleton(steps=[])
    assert client.last_call is None


def test_raises_plan_generation_error_when_the_llm_client_raises():
    client = FakeLLMClient(exception=RuntimeError("network down"))

    with pytest.raises(PlanGenerationError):
        generate_plan_skeleton(ONE_PDF, client)


def test_raises_plan_generation_error_for_invalid_json():
    client = FakeLLMClient(response="not json at all")

    with pytest.raises(PlanGenerationError):
        generate_plan_skeleton(ONE_PDF, client)


def test_raises_plan_generation_error_for_a_response_outside_the_schema():
    invalid = json.dumps({"steps": [{"order": -1, "operationType": "Taşı", "targetFolder": "X", "affectedFileCount": 1}]})
    client = FakeLLMClient(response=invalid)

    with pytest.raises(PlanGenerationError):
        generate_plan_skeleton(ONE_PDF, client)


def test_raises_plan_generation_error_for_an_unknown_operation_type():
    invalid = json.dumps({"steps": [{"order": 0, "operationType": "FormatDisk", "targetFolder": "X", "affectedFileCount": 1}]})
    client = FakeLLMClient(response=invalid)

    with pytest.raises(PlanGenerationError):
        generate_plan_skeleton(ONE_PDF, client)


def test_raises_plan_generation_error_for_duplicate_order_values():
    invalid = json.dumps(
        {
            "steps": [
                {"order": 0, "operationType": "Taşı", "targetFolder": "X", "affectedFileCount": 1},
                {"order": 0, "operationType": "Sil", "targetFolder": "Y", "affectedFileCount": 1},
            ]
        }
    )
    client = FakeLLMClient(response=invalid)

    with pytest.raises(PlanGenerationError):
        generate_plan_skeleton(ONE_PDF, client)


def test_uses_the_explicitly_passed_model_over_the_env_default():
    client = FakeLLMClient(response=VALID_PLAN_JSON)

    generate_plan_skeleton(ONE_PDF, client, model="custom-model")

    assert client.last_call["model"] == "custom-model"


def test_resolve_model_id_falls_back_to_default_when_env_unset(monkeypatch):
    monkeypatch.delenv("PLAN_LLM_MODEL_ID", raising=False)

    assert resolve_model_id() == DEFAULT_MODEL_ID


def test_resolve_model_id_uses_env_override(monkeypatch):
    monkeypatch.setenv("PLAN_LLM_MODEL_ID", "pinned-model-x")

    assert resolve_model_id() == "pinned-model-x"


def test_generate_plan_skeleton_uses_the_env_model_when_none_passed(monkeypatch):
    monkeypatch.setenv("PLAN_LLM_MODEL_ID", "pinned-model-x")
    client = FakeLLMClient(response=VALID_PLAN_JSON)

    generate_plan_skeleton(ONE_PDF, client)

    assert client.last_call["model"] == "pinned-model-x"


def test_build_metadata_prompt_includes_only_filename_and_date_not_content():
    prompt = build_metadata_prompt([PdfFileMetadata(filename="fatura.pdf", createdAt="2026-08-01")])

    assert "fatura.pdf" in prompt
    assert "2026-08-01" in prompt
