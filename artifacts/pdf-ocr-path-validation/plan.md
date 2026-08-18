# Plan — Saga #307

## Dosya Değişiklikleri

### backend/models.py
- `OperationType` enum'una `OCR = "OCR"` üyesi eklenir (diğerleriyle aynı yerde, SPLIT'ten sonra).
- `PlanStep`e yeni bir `@model_validator(mode="after")`: `file_names_length_exactly_one_for_ocr`
  — `operationType == OCR` iken `len(fileNames) != 1` ise `ValueError`. SPLIT'in
  `file_names_length_exactly_one_for_split` validator'üyle birebir aynı desen, ayrı fonksiyon
  (SPLIT'inkini bozmadan).

### backend/orchestrator.py
- `from backend.pdf_ocr import ocr_pdf_file` importu eklenir.
- `_SUPPORTED_OPERATION_TYPES` set'ine `OperationType.OCR` eklenir.
- `apply_plan` döngüsünde, `MERGE`/`SPLIT` bloklarıyla aynı hizada yeni bir `if step.operationType == OperationType.OCR:` bloğu:
  - `source_path = allowed_root / files[0].filename`
  - `is_path_allowed(source_path, allowed_root)` kontrolü (zaten `security.py`'den import edilmiş) — False ise `PlanApplicationError` fırlatır, `ocr_pdf_file` ÇAĞRILMAZ.
  - True ise `ocr_pdf_file(source_path)` çağrılır (sonuç bu task kapsamında kullanılmaz/atılır).
  - `continue` (LIST gibi inert — `FileOperation` kaydı YOK, `applied` listesine eklenmez, rollback'e girmez).
- Not: `validate_plan_paths` zaten `apply_plan`'ın en başında TÜM `pdf_files` için `allowed_root` kontrolü yapıyor — OCR'ın kaynak dosyası da `pdf_files` listesinde olduğu için bu ilk savunma katmanından zaten geçer. Adımdaki ekstra `is_path_allowed` çağrısı, MERGE/SPLIT'in kendi hedef-spesifik ekstra kontrolleriyle TUTARLI bir ikinci savunma katmanı (defense-in-depth) — red-team'in "ocr_pdf_file'a asla ham path geçirilmesin" gerekliliğini `apply_plan` içinde AÇIKÇA görünür kılar.

### backend/pdf_ocr.py
- DEĞİŞTİRİLMEZ.

### backend/tests/test_orchestrator.py
- Yeni testler (test-copilot/subagent tarafından yazılacak, kırmızı-yeşil):
  1. `test_apply_plan_runs_ocr_on_a_pdf_inside_allowed_root_without_moving_it` — `ocr_pdf_file` monkeypatch'lenir, doğru `Path` ile çağrıldığı ve dosyanın YERİNDE kaldığı doğrulanır, `transaction.status == "committed"`.
  2. `test_apply_plan_rejects_ocr_of_a_path_outside_allowed_root` — MERGE/SPLIT'in "dışarı çıkan path reddedilir" testleriyle aynı desen (bkz. `test_revert_transaction_ignores_operations_outside_the_allowed_root` ve `validate_plan_paths`'ı zaten kapsayan mevcut testler) — `ocr_pdf_file` monkeypatch'i HİÇ ÇAĞRILMADIĞINI doğrular.
  3. `test_plan_step_rejects_ocr_with_more_than_one_file_name` (models.py validator testi, muhtemelen `backend/tests/test_models.py`'de).

## Bağımlılıklar
Yeni bağımlılık yok — `ocr_pdf_file` zaten Saga #306'da eklendi.

## Migration
Yok.

## Riskler
- `pdf2image`/Tesseract test ortamında kurulu olmayabilir → testler `ocr_pdf_file`'ı monkeypatch ile stub'lar, gerçek OCR motorunu test etmez (bu zaten Saga #306'nın sorumluluğu).
