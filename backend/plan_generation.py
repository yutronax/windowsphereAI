import json
import os
from typing import Protocol

from pydantic import ValidationError

from backend.models import DateSource, PdfFileMetadata, PlanSkeleton, SortOrder

DEFAULT_MODEL_ID = "gpt-4o-mini"
MODEL_ID_ENV_VAR = "PLAN_LLM_MODEL_ID"

PLAN_SYSTEM_PROMPT = (
    "Sen bir dosya organizasyon asistanısın. Sana kullanıcının doğal dil "
    "isteği ile birlikte PDF dosya adı ve oluşturulma tarihi metadata'sı "
    "verilecek. Kullanıcının isteğine göre DOĞRU operationType'ı seç:\n"
    '- "taşı", "sırala", "organize et", "düzenle" → "Taşı" (varsayılan, '
    "istek belirsizse bunu kullan)\n"
    '- "kopyala", "yedekle", "çoğalt" → "Kopyala"\n'
    '- "sil", "temizle", "kaldır" → "Sil"\n'
    '- "yeniden adlandır", "ismini değiştir" → "Yeniden Adlandır"\n'
    '- "listele", "göster", "say" → "Listele"\n'
    '- "birleştir", "tek dosya yap" → "Birleştir"\n'
    '- "böl", "sayfalara ayır" → "Böl" (fileNames bu step için TAM OLARAK '
    "1 dosya içermeli — Böl tek bir kaynağı böler, birden fazla dosyayı "
    "aynı step'te bölmek desteklenmez)\n"
    '- "ekle", "not ekle", "sayfa ekle", "sonuna ekle" → "Ekle" (fileNames '
    "bu step için TAM OLARAK 1 dosya içermeli — Ekle tek bir kaynağın "
    "SONUNA yeni bir metin sayfası ekler)\n\n"
    "Sadece şu JSON şemasında yanıt ver: "
    '{"dateSource": "created_at", "sortOrder": "ascending"|"descending", '
    '"steps": [{"order": <negatif olmayan tamsayı>, "operationType": '
    '"Taşı"|"Kopyala"|"Sil"|"Yeniden Adlandır"|"Listele"|"Birleştir"|"Böl"|"Ekle", "targetFolder": '
    '<"YYYY-MM" formatında string>, "affectedFileCount": <negatif olmayan '
    'tamsayı>, "fileNames": [<bu step\'e ait TAM dosya adlarının listesi>], '
    '"newFileNames": [<SADECE operationType "Yeniden Adlandır" ise, '
    "fileNames ile AYNI sırada ve uzunlukta yeni dosya adları listesi; "
    "başka HERHANGİ bir operationType'ta bu alanı TAMAMEN ATLA, JSON'a "
    'hiç koyma>], "mergedFileName": <SADECE operationType "Birleştir" ise, '
    "bu step'teki fileNames'in birleştirileceği TEK yeni dosya adı (path "
    "ayracı OLMAYAN bir bare dosya adı, ör. \"birlesik.pdf\"); başka "
    "HERHANGİ bir operationType'ta bu alanı TAMAMEN ATLA, JSON'a hiç "
    'koyma>], "appendText": <SADECE operationType "Ekle" ise, bu step\'teki '
    "tek kaynağın sonuna eklenecek KISA metin (birkaç cümle/paragraf, en "
    "fazla 5000 karakter, boş/whitespace-only OLAMAZ); başka HERHANGİ bir "
    "operationType'ta bu alanı TAMAMEN ATLA, JSON'a hiç koyma>}]}. "
    "dateSource ve sortOrder alanları AÇIKÇA belirtilmeli, "
    "her targetFolder kesinlikle YYYY-MM formatında olmalı — 'Sil'/'Yeniden "
    "Adlandır'/'Listele' için targetFolder GERÇEKTEN KULLANILMAZ ama şema "
    "gereği yine de geçerli bir YYYY-MM string'i olmalı (ör. o step'teki "
    "dosyaların oluşturulma ayı). `fileNames`, sana verilen PDF dosya "
    "adları listesinden BİREBİR alınmalı (yeni bir isim uydurma, hiçbirini "
    "atlamama, hiçbirini birden fazla step'e koyma); her step'in "
    "`affectedFileCount`'u o step'in `fileNames` listesinin uzunluğuna "
    "EŞİT olmalı. Başka hiçbir metin ekleme, sadece bu JSON'u döndür."
)


class PlanGenerationError(Exception):
    """Raised when a plan-skeleton cannot be produced from the LLM response."""


class LLMClient(Protocol):
    def complete(self, *, model: str, system_prompt: str, user_prompt: str) -> str: ...


def resolve_model_id() -> str:
    return os.environ.get(MODEL_ID_ENV_VAR, DEFAULT_MODEL_ID)


def build_metadata_prompt(pdf_files: list[PdfFileMetadata], request_text: str) -> str:
    lines = [f"- {file.filename} (oluşturulma tarihi: {file.createdAt})" for file in pdf_files]
    return (
        f"Kullanıcının isteği: {request_text}\n\n"
        "Aşağıdaki PDF dosyaları için bu isteğe uygun bir plan üret:\n\n" + "\n".join(lines)
    )


def generate_plan_skeleton(
    pdf_files: list[PdfFileMetadata],
    client: LLMClient,
    request_text: str = "",
    model: str | None = None,
) -> PlanSkeleton:
    # Saga #292: `request_text` olmadan LLM'in COPY/DELETE/RENAME/LIST
    # (Saga #288-#291) arasından doğru operationType'ı seçmesi mümkün
    # değildi — sadece dosya adı/tarih görüyordu, kullanıcının "sırala mı
    # yedekle mi sil mi" istediğini bilemiyordu. Varsayılan boş string
    # geriye dönük uyumluluk için (çağıran hiç geçmezse LLM "Taşı"
    # varsayılanına düşer, prompt'taki eşleme rehberi gereği).
    if not pdf_files:
        # Taşınacak dosya yoksa LLM'e hiç istek atılmaz; dateSource/sortOrder
        # yine de şema tutarlılığı için sağlanır (fiilen kullanılmaz).
        return PlanSkeleton(steps=[], dateSource=DateSource.CREATED_AT, sortOrder=SortOrder.ASCENDING)

    resolved_model = model or resolve_model_id()
    prompt = build_metadata_prompt(pdf_files, request_text)

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
