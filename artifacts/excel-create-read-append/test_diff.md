# Test Diff — excel-create-read-append

Yazım motoru: bağımsız `efektor` subagent (Codex kotası dolu; kullanıcı
isteğiyle bu görevde test/kod yazımı alt ajanlara devredildi).

## backend/tests/test_excel_rows.py (yeni, 12 test)
`create_excel_file`/`append_excel_rows`/`read_excel_range` unit testleri:
- CREATE: happy (AC-1), hedef zaten var + dokunulmama (AC-2), düz liste
  sarma (AC-3).
- APPEND: happy (AC-6), kaynak yok (AC-7), kaynak bozuk (AC-7), backup'ın
  yazmadan ÖNCE alındığı doğrulaması.
- READ: range'siz tüm alan (AC-5), range'li (AC-4), geçersiz range →
  `ValueError`.

## backend/tests/test_orchestrator.py (ekleme, 7 test)
`OperationType.EXCEL_CREATE`/`EXCEL_APPEND` orchestrator entegrasyon
testleri — happy path, hata yolları, path whitelist ihlali (PDF APPEND/
EXCEL_FILTER desenleriyle aynı).

## backend/tests/test_main_integration.py (ekleme, 6 test)
`/api/excel/read` endpoint testleri — 404/410 (session/klasör), 200 (range
ile/sız), 422 (geçersiz range), dosya-yok hatası.

## Bilinçli esnek bırakılan
`/api/excel/read`'in dosya-yok durumundaki TAM HTTP kodu plan.md'de
kesinleşmemişti — ilgili test sadece `>=400` ile esnek yazıldı, code-copilot
adımında kesin kod (muhtemelen 404) belirlenip test buna göre sıkılaştırılabilir.

## Durum
Kırmızı (doğrulandı):
- `test_excel_rows.py` → `ModuleNotFoundError: No module named 'backend.excel_rows'`
- `test_orchestrator.py -k "excel_create or excel_append"` → 4 failed, `AttributeError`
- `test_main_integration.py -k excel_read` → 4 failed (route yok), 2 passed
  (tesadüfen — zaten ≥400 bekleyen testler 404 ile geçiyor)

code-copilot implementasyonu yazınca yeşile dönmesi bekleniyor.
