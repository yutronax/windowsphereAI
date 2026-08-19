# Code Diff — zip-temel-operasyonlar

Yazım motoru: bağımsız `efektor` subagent'lar (biri test [red], biri
implementasyon [green], ikisi de `.venv` disiplinine uydu).

## Files Modified
- `backend/models.py` — `OperationType.ZIP_CREATE/ZIP_ADD/ZIP_EXTRACT/ZIP_MERGE`;
  `PlanStep`e `zippedFileName`, `destinationFolder` (YYYY-MM kısıtı YOK,
  serbest format), `filesToAdd`, `addedFileName`, `mergedZipFileName`; 4
  model_validator (ZIP_CREATE fileNames≥1, ZIP_ADD/ZIP_EXTRACT fileNames==1,
  ZIP_MERGE fileNames≥2); `ZipListRequest`/`ZipListResponse`.
- `backend/orchestrator.py` — `zip_ops` import; `_SUPPORTED_OPERATION_TYPES`,
  hedef-klasör hariç-tutma listesi; `_rollback_zip_extract` (YENİ fonksiyon)
  + `_ROLLBACK_OPERATIONS` kaydı; 4 yeni step bloğu.
- `backend/main.py` — yeni `POST /api/zip/list` endpoint'i,
  `/api/excel/read`'in birebir deseni.
- `backend/tests/test_orchestrator.py`, `backend/tests/test_main_integration.py`
  — test-yazım subagent'ı tarafından red step'te eklendi.

## New Files
- `backend/zip_ops.py` — `create_zip`, `add_to_zip`, `extract_zip`,
  `merge_zips`, `list_zip_entries`. **Zip-slip koruması gerçekten
  `security.py`'nin mevcut `_validate_single_path`'ini yeniden kullanıyor**
  (yeni bir güvenlik algoritması yazılmadı) — kod incelemesiyle doğrulandı.
- `backend/tests/test_zip_ops.py` — 25 unit test (red step'te yazıldı).

## ZIP_EXTRACT Rollback Mekanizması (kanıtlı)
`destination_folder.exists()` işlemden ÖNCE kontrol ediliyor: klasör
YOKSA `backup_path` bir sentinel (`str(destination_folder) + ".zip-extract-created"`)
olarak kaydediliyor, rollback `shutil.rmtree` ile TAMAMEN siliyor; klasör
ZATEN VARSA `backup_path == destination_path` (string-eşit), rollback
no-op (var olan içeriğe hiç dokunulmuyor). İki ayrı test bunu doğruluyor.

## Acceptance Criteria Coverage
AC-1 (CREATE), AC-2 (EXTRACT doğru hedef), AC-3/AC-S1 (zip-slip — 3
senaryo: POSIX göreli, mutlak Windows path, UNC path), AC-4 (ADD), AC-5
(MERGE), AC-5b (OPEN/list), AC-6 (kaynak yok/bozuk) — hepsi yeşil.

## Test Evidence
- Hedeflenen testler: `37 passed`
- Tüm backend suite: `500 passed, 5 skipped, 0 failed` — regresyon yok
  (Word tablo görevinden sonraki 463'ten +37).

## Remaining Limitations
- `plan_generation.py`/LLM prompt tarafı kapsam dışı.
- Klasör-rekursif zip'leme yok, sadece verilen dosya listesi.
- Şifreli/parola korumalı zip desteği yok.

## CAVEMAN Review
- Files added: 2 (`zip_ops.py`, `test_zip_ops.py`) — plan.md'de öngörülmüştü.
- New abstractions: `_rollback_zip_extract` — gerekçeli, ZIP_EXTRACT'in
  klasör-hedefli doğası mevcut dosya-hedefli `_rollback_copy`'ye uymuyor.
- Zip-slip: yeni algoritma YOK, mevcut whitelist mekanizması yeniden
  kullanıldı — en büyük CAVEMAN kazancı bu görevde.

## Definition of Done
- Her AC implementeli, kısmi implementasyon yok, kapsam dışı işlevsellik yok.
- TODO/FIXME/placeholder yok.
- Proje konvansiyonları (MERGE/EXCEL_FILTER/DELETE desenlerinin birleşimi) takip edildi.
- `pytest backend/tests` — 500 passed, 5 skipped, 0 failed.
