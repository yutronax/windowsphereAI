# Test Diff — zip-temel-operasyonlar

Yazım motoru: bağımsız `efektor` subagent (`.venv/Scripts/python.exe`
ile çalıştı, önceki görevin ortam dersi uygulandı).

## backend/tests/test_zip_ops.py (yeni, 25 test)
`create_zip`/`add_to_zip`/`extract_zip`/`merge_zips`/`list_zip_entries`
unit testleri — ÖZELLİKLE `extract_zip` için 3 ayrı zip-slip senaryosu
(POSIX göreli `../`, mutlak Windows path, UNC path), her biri "meşru
dosya bile diske çıkmadı" ön-tarama garantisiyle test edildi.

## backend/tests/test_orchestrator.py (ekleme, 15 test)
ZIP_CREATE/ZIP_ADD/ZIP_EXTRACT/ZIP_MERGE orchestrator entegrasyon
testleri — happy path, hata yolu, path whitelist ihlali, zip-slip reddi,
ZIP_EXTRACT rollback (klasör önceden var/yok senaryoları ayrı ayrı).

## backend/tests/test_main_integration.py (ekleme, 5 test)
`/api/zip/list` endpoint testleri.

## Durum
Kırmızı (`.venv` ile doğrulandı):
- `test_zip_ops.py` → `ModuleNotFoundError: No module named 'backend.zip_ops'`
- `test_orchestrator.py -k zip` → 15/15 `AttributeError` (enum yok)
- `test_main_integration.py -k zip` → 3/5 failed (route yok), 2 tesadüfen
  geçiyor (zaten 4xx bekleyen testler)

code-copilot implementasyonu yazınca yeşile dönmesi bekleniyor.
