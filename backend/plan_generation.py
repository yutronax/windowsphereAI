import json
import os
from typing import Protocol

from pydantic import ValidationError

from backend.models import DateSource, PdfFileMetadata, PlanSkeleton, SortOrder

DEFAULT_MODEL_ID = "gpt-4o-mini"
MODEL_ID_ENV_VAR = "PLAN_LLM_MODEL_ID"

PLAN_SYSTEM_PROMPT = (
    "Sen bir dosya organizasyon asistanısın. Sana verilen PDF dosya adı ve "
    "oluşturulma tarihi metadata'sından, dosyaları tarihe göre YYYY-MM "
    "klasörlerine taşıyacak bir plan üret. Sadece şu JSON şemasında yanıt "
    'ver: {"dateSource": "created_at", "sortOrder": "ascending"|"descending", '
    '"steps": [{"order": <negatif olmayan tamsayı>, "operationType": '
    '"Taşı"|"Kopyala"|"Sil"|"Yeniden Adlandır"|"Listele", "targetFolder": '
    '<"YYYY-MM" formatında string>, "affectedFileCount": <negatif olmayan '
    "tamsayı>}]}. dateSource ve sortOrder alanları AÇIKÇA belirtilmeli, "
    "her targetFolder kesinlikle YYYY-MM formatında olmalı. Başka hiçbir "
    "metin ekleme, sadece bu JSON'u döndür."
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
        # Taşınacak dosya yoksa LLM'e hiç istek atılmaz; dateSource/sortOrder
        # yine de şema tutarlılığı için sağlanır (fiilen kullanılmaz).
        return PlanSkeleton(steps=[], dateSource=DateSource.CREATED_AT, sortOrder=SortOrder.ASCENDING)

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
