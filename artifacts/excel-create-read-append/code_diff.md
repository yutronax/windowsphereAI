# Code Diff — excel-create-read-append

Yazım motoru: bağımsız `efektor` subagent'lar (Codex kotası dolu; biri
test [red], biri implementasyon [green]).

## Files Modified
- `backend/models.py` — `OperationType.EXCEL_CREATE`/`EXCEL_APPEND`;
  `PlanStep.createRows/createdFileName/appendRows` (ayrı alanlar, "rows"
  ortak DEĞİL — plan.md kararı); `excel_create_fields_only_for_excel_create`
  (fileNames==0, İLK KEZ eklenen "kaynaksız" desen), `excel_append_fields_only_for_excel_append`
  (fileNames==1); `ExcelReadRequest`/`ExcelReadResponse`.
- `backend/orchestrator.py` — `excel_rows` import; `_SUPPORTED_OPERATION_TYPES`,
  `_ROLLBACK_OPERATIONS` (`EXCEL_CREATE→_rollback_copy`, `EXCEL_APPEND→_rollback_append`
  — PDF APPEND'in AYNI fonksiyonu, değişiklik gerekmedi), hedef-klasör
  hariç-tutma listesi; iki yeni step bloğu (CREATE: kaynaksız,
  `source_path=""`; APPEND: PDF `OperationType.APPEND` bloğunun birebir
  kopyası).
- `backend/main.py` — yeni `POST /api/excel/read` endpoint'i,
  `search_endpoint`'in deseniyle (404/410, `get_session_for_excel_read`
  dependency); `ValueError` (geçersiz range) → 422.
- **`backend/security.py` (plan.md'de ÖNGÖRÜLMEMİŞTİ, implementasyon
  sırasında gerekli olduğu tespit edildi):** `validate_plan_paths`e
  `OperationType.EXCEL_CREATE` için `createdFileName` whitelist kontrolü
  eklendi — EXCEL_CREATE kaynaksız (fileNames boş) olduğu için genel
  `pdf_files` döngüsü hedefi hiç göremiyordu, MERGE/REDACT/EXCEL_SORT ile
  AYNI desende (`_validate_single_path`) ayrıca eklendi. Path-whitelist
  red testinin geçmesi için ZORUNLUYDU.
- `backend/tests/test_orchestrator.py`, `backend/tests/test_main_integration.py`
  — test-yazım subagent'ı tarafından red step'te eklendi.

## New Files
- `backend/excel_rows.py` — `create_excel_file`, `append_excel_rows`,
  `read_excel_range` + paylaşılan `_normalize_rows` yardımcısı.
  **EXCEL_APPEND kesinlikle openpyxl'in "doğrudan üzerine yaz" kolaylığını
  KULLANMIYOR** — kaynak önce backup_path'e kopyalanıyor, SONRA
  tempfile+atomik-replace ile kaynağa yazılıyor (PDF `_forward_append`
  ile birebir aynı güvenlik garantisi, plan.md'nin Risks notunda talep
  edilen).
- `backend/tests/test_excel_rows.py` — 12 unit test (red step'te yazıldı).

## Gözlem (kapsam dışı, bu görevle ilgisiz, red-team'e not düşüldü)
`backend/security.py`'nin `validate_plan_paths` fonksiyonunda sadece
MERGE/REDACT/EXCEL_SORT/(şimdi)EXCEL_CREATE'in hedef dosya adları AÇIKÇA
whitelist kontrolünden geçiyor — EXCEL_FILTER/PDF_EXTRACT_PAGES/
PDF_DELETE_PAGES/PDF_COMPRESS'in hedef alanları (`filteredFileName`,
`extractedFileName`, `remainingFileName`, `compressedFileName`) bu
fonksiyonda AÇIKÇA yer ALMIYOR gibi görünüyor. Bu görevden ÖNCE var olan
bir durum, bu görevin kapsamı DIŞINDA — ama gerçek bir gap olup olmadığı
(belki başka bir mekanizma zaten kapsıyor) bağımsız red-team incelemesinde
doğrulanmalı, kendim düzeltmedim.

## Acceptance Criteria Coverage
AC-1 (CREATE happy), AC-2 (CREATE çakışma), AC-3 (satır sarma), AC-4
(READ range ile), AC-5 (READ range'siz), AC-6 (APPEND happy), AC-7
(APPEND kaynak yok/bozuk) — hepsi yeşil.

## Test Evidence
- Hedeflenen testler: `23 passed`
- Tüm backend suite: `452 passed, 5 skipped, 0 failed` — regresyon yok.

## Remaining Limitations
- `plan_generation.py`/LLM prompt tarafı kapsam dışı (atdd.md'de işaretli).
- EXCEL_READ'in sayfa (sheet) seçimi yok, sadece `workbook.active`.
- EXCEL_CREATE'te formül/biçimlendirme desteği yok, ham değerler.

## CAVEMAN Review
- Files added: 2 (`excel_rows.py`, `test_excel_rows.py`) — plan.md'de
  öngörülmüştü.
- New abstractions: `_normalize_rows` — CREATE ve APPEND arasında
  paylaşılan tek satırlık normalizasyon mantığı, gerekçeli (iki çağıran,
  birebir aynı davranış).
- `backend/security.py` değişikliği: yeni bir soyutlama değil, mevcut
  `_validate_single_path` deseninin dördüncü kullanımı.

## Definition of Done
- Her AC implementeli, kısmi implementasyon yok, kapsam dışı işlevsellik yok.
- TODO/FIXME/placeholder yok.
- Proje konvansiyonları (PDF APPEND, EXCEL_FILTER, search_endpoint desenleri) takip edildi.
- `pytest backend/tests` — 452 passed, 5 skipped, 0 failed.
