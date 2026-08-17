# Plan — Tarih kaynağı + klasör yapısı doğrulaması (Saga #270)

## Değiştirilecek dosya
- `backend/models.py`
  - `DateSource(str, Enum)`: `CREATED_AT = "created_at"` (tek üye, genişleyebilir).
  - `SortOrder(str, Enum)`: `ASCENDING = "ascending"`, `DESCENDING = "descending"`.
  - `PlanStep.targetFolder` validator'ı güncellenir: boş-kontrolüne EK
    olarak `^\d{4}-\d{2}$` regex kontrolü eklenir.
  - `PlanSkeleton`'a `dateSource: DateSource` ve `sortOrder: SortOrder`
    zorunlu alanları eklenir (Pydantic zaten eksik/geçersiz değerde
    `ValidationError` fırlatır — ekstra validator gerekmez, Enum tipi
    yeterli).
- `backend/plan_generation.py`
  - `PLAN_SYSTEM_PROMPT` güncellenir: LLM'e artık `dateSource`/`sortOrder`
    alanlarını da JSON şemasında döndürmesi gerektiği açıkça söylenir.

## Güncellenecek test dosyaları
- `backend/tests/test_plan_generation.py` — `VALID_PLAN_JSON` sabiti
  `dateSource`/`sortOrder` içerecek şekilde güncellenir; yeni testler:
  eksik/geçersiz `dateSource`/`sortOrder`, geçersiz `targetFolder` formatı.
- `backend/tests/test_main_integration.py` — `VALID_PLAN_JSON` sabiti
  aynı şekilde güncellenir.

## Yeni bağımlılık yok
