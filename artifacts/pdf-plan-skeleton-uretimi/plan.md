# Plan — Plan-skeleton üretimi (Saga #269)

## Değiştirilecek dosya
- `backend/models.py`
  - `OperationType(str, Enum)`: Taşı/Kopyala/Sil/Yeniden Adlandır/Listele
    (frontend `KNOWN_OPERATION_TYPES` ile aynı — ui/src/components/chat/planValidation.ts).
  - `PlanStep(BaseModel)`: order (ge=0), operationType (OperationType),
    targetFolder (non-blank str), affectedFileCount (ge=0).
  - `PlanSkeleton(BaseModel)`: steps (list[PlanStep]), order tekilliği
    validator'ı.
  - `PdfFileMetadata(BaseModel)`: filename (non-blank), createdAt (str,
    ISO tarih; dar kapsam — gerçek date-format doğrulaması bu task'ta
    yapılmıyor, string olarak taşınıyor).
  - `PlanRequest(BaseModel)`: sessionId (non-blank), pdfFiles (list[PdfFileMetadata]).

## Yeni dosya
- `backend/plan_generation.py`
  - `DEFAULT_MODEL_ID`, `MODEL_ID_ENV_VAR = "PLAN_LLM_MODEL_ID"`.
  - `PlanGenerationError(Exception)`.
  - `LLMClient(Protocol)`: `complete(*, model, system_prompt, user_prompt) -> str`.
  - `resolve_model_id() -> str`.
  - `build_metadata_prompt(pdf_files) -> str` — sadece filename+createdAt.
  - `generate_plan_skeleton(pdf_files, client, model=None) -> PlanSkeleton`
    — boş liste kısayolu, LLM çağrısı (exception → PlanGenerationError),
    JSON parse (hata → PlanGenerationError), Pydantic validate (hata →
    PlanGenerationError).
  - `OpenAICompatibleLLMClient`: openai SDK ile gerçek istemci (api_key,
    base_url opsiyonel — BYOK).

## `backend/main.py`
- `get_llm_client()` dependency: `PLAN_LLM_API_KEY` yoksa `HTTPException(503)`.
- `POST /api/plan`: `PlanRequest` alır, `generate_plan_skeleton` çağırır,
  `PlanGenerationError` → `HTTPException(502, detail=str(exc))`.

## Yeni test dosyaları
- `backend/tests/test_plan_generation.py`
- `backend/tests/test_main_integration.py`'e `/api/plan` testleri eklenir
  (dependency_overrides ile FakeLLMClient).

## Yeni bağımlılık
`openai` paketi zaten kurulu (proje ortamında mevcut) — `requirements.txt`
yoksa bu task'ta eklenmiyor (proje henüz bağımlılık dosyası kullanmıyor,
mevcut backend/*.py dosyaları da hiçbir requirements dosyasına
kaydedilmemiş — dar kapsam, mevcut konvansiyon korunuyor).
