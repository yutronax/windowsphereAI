diff --git a/backend/main.py b/backend/main.py
index 0d43fd7..82631dd 100644
--- a/backend/main.py
+++ b/backend/main.py
@@ -1,10 +1,17 @@
+import os
 import uuid
 
-from fastapi import FastAPI, HTTPException, status
+from fastapi import Depends, FastAPI, HTTPException, status
 from fastapi.middleware.cors import CORSMiddleware
 
 from backend.config import load_setup_config
-from backend.models import SessionContext, SessionRequest
+from backend.models import PlanRequest, PlanSkeleton, SessionContext, SessionRequest
+from backend.plan_generation import (
+    LLMClient,
+    OpenAICompatibleLLMClient,
+    PlanGenerationError,
+    generate_plan_skeleton,
+)
 
 app = FastAPI()
 
@@ -44,3 +51,19 @@ def create_session(payload: SessionRequest) -> SessionContext:
     )
     _sessions[session.sessionId] = session
     return session
+
+
+def get_llm_client() -> LLMClient:
+    api_key = os.environ.get("PLAN_LLM_API_KEY")
+    if not api_key:
+        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="LLM API anahtarı yapılandırılmamış")
+    base_url = os.environ.get("PLAN_LLM_BASE_URL")
+    return OpenAICompatibleLLMClient(api_key=api_key, base_url=base_url)
+
+
+@app.post("/api/plan")
+def create_plan(payload: PlanRequest, client: LLMClient = Depends(get_llm_client)) -> PlanSkeleton:
+    try:
+        return generate_plan_skeleton(payload.pdfFiles, client)
+    except PlanGenerationError as exc:
+        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
diff --git a/backend/models.py b/backend/models.py
index 8322673..a5ab275 100644
--- a/backend/models.py
+++ b/backend/models.py
@@ -1,3 +1,5 @@
+from enum import Enum
+
 from pydantic import BaseModel, field_validator
 
 from backend.request_normalization import normalize_request_text, normalize_selected_folder
@@ -22,3 +24,68 @@ class SessionContext(BaseModel):
     sessionId: str
     selectedFolder: str
     requestText: str
+
+
+class OperationType(str, Enum):
+    MOVE = "Taşı"
+    COPY = "Kopyala"
+    DELETE = "Sil"
+    RENAME = "Yeniden Adlandır"
+    LIST = "Listele"
+
+
+class PlanStep(BaseModel):
+    order: int
+    operationType: OperationType
+    targetFolder: str
+    affectedFileCount: int
+
+    @field_validator("order", "affectedFileCount")
+    @classmethod
+    def non_negative(cls, value: int) -> int:
+        if value < 0:
+            raise ValueError("must be a non-negative integer")
+        return value
+
+    @field_validator("targetFolder")
+    @classmethod
+    def target_folder_not_blank(cls, value: str) -> str:
+        if value.strip() == "":
+            raise ValueError("must not be empty or whitespace-only")
+        return value
+
+
+class PlanSkeleton(BaseModel):
+    steps: list[PlanStep]
+
+    @field_validator("steps")
+    @classmethod
+    def unique_orders(cls, value: list[PlanStep]) -> list[PlanStep]:
+        orders = [step.order for step in value]
+        if len(orders) != len(set(orders)):
+            raise ValueError("step order values must be unique")
+        return value
+
+
+class PdfFileMetadata(BaseModel):
+    filename: str
+    createdAt: str
+
+    @field_validator("filename", "createdAt")
+    @classmethod
+    def not_blank(cls, value: str) -> str:
+        if value.strip() == "":
+            raise ValueError("must not be empty or whitespace-only")
+        return value
+
+
+class PlanRequest(BaseModel):
+    sessionId: str
+    pdfFiles: list[PdfFileMetadata]
+
+    @field_validator("sessionId")
+    @classmethod
+    def session_id_not_blank(cls, value: str) -> str:
+        if value.strip() == "":
+            raise ValueError("must not be empty or whitespace-only")
+        return value
--- new file: backend/plan_generation.py ---
import json
import os
from typing import Protocol

from pydantic import ValidationError

from backend.models import PdfFileMetadata, PlanSkeleton

DEFAULT_MODEL_ID = "gpt-4o-mini"
MODEL_ID_ENV_VAR = "PLAN_LLM_MODEL_ID"

PLAN_SYSTEM_PROMPT = (
    "Sen bir dosya organizasyon asistanısın. Sana verilen PDF dosya adı ve "
    "oluşturulma tarihi metadata'sından, dosyaları tarihe göre YYYY-MM "
    "klasörlerine taşıyacak bir plan üret. Sadece şu JSON şemasında yanıt "
    'ver: {"steps": [{"order": <negatif olmayan tamsayı>, "operationType": '
    '"Taşı"|"Kopyala"|"Sil"|"Yeniden Adlandır"|"Listele", "targetFolder": '
    '<string>, "affectedFileCount": <negatif olmayan tamsayı>}]}. '
    "Başka hiçbir metin ekleme, sadece bu JSON'u döndür."
)


class PlanGenerationError(Exception):
    """Raised when a plan-skeleton cannot be produced from the LLM response."""


class LLMClient(Protocol):
    def complete(self, *, model: str, system_prompt: str, user_prompt: str) -> str: ...


def resolve_model_id() -> str:
    return os.environ.get(MODEL_ID_ENV_VAR, DEFAULT_MODEL_ID)


def build_metadata_prompt(pdf_files: list[PdfFileMetadata]) -> str:
    lines = [f"- {file.filename} (oluşturulma tarihi: {file.createdAt})" for file in pdf_files]
    return "Aşağıdaki PDF dosyaları için bir plan üret:\n\n" + "\n".join(lines)


def generate_plan_skeleton(
    pdf_files: list[PdfFileMetadata],
    client: LLMClient,
    model: str | None = None,
) -> PlanSkeleton:
    if not pdf_files:
        return PlanSkeleton(steps=[])

    resolved_model = model or resolve_model_id()
    prompt = build_metadata_prompt(pdf_files)

    try:
        raw_response = client.complete(
            model=resolved_model,
            system_prompt=PLAN_SYSTEM_PROMPT,
            user_prompt=prompt,
        )
    except Exception as exc:
        raise PlanGenerationError("Plan üretilemedi: LLM isteği başarısız oldu.") from exc

    try:
        parsed = json.loads(raw_response)
    except json.JSONDecodeError as exc:
        raise PlanGenerationError("Plan üretilemedi: LLM yanıtı geçerli JSON değil.") from exc

    try:
        return PlanSkeleton.model_validate(parsed)
    except ValidationError as exc:
        raise PlanGenerationError("Plan üretilemedi: LLM yanıtı beklenen şemaya uymuyor.") from exc


class OpenAICompatibleLLMClient:
    """BYOK LLM istemcisi — openai SDK, base_url override ile OpenAI-uyumlu
    sağlayıcılara (ör. DeepSeek) bağlanabilir."""

    def __init__(self, api_key: str, base_url: str | None = None) -> None:
        from openai import OpenAI

        self._client = OpenAI(api_key=api_key, base_url=base_url)

    def complete(self, *, model: str, system_prompt: str, user_prompt: str) -> str:
        response = self._client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content or ""
