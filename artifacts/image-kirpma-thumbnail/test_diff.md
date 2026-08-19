# Test Diff — image-kirpma-thumbnail

Yazım motoru: bağımsız `efektor` subagent (`.venv/Scripts/python.exe`
ile çalıştı).

## backend/tests/test_image_ops.py (yeni, 12 test)
`crop_image`/`create_thumbnail` unit testleri — ÖZELLİKLE sınır-dışı
`box` testi, Pillow'un kendi (sessiz) toleransına GÜVENMEDİĞİNİ
doğruluyor (implementasyon elle kontrol etmek ZORUNDA).

## backend/tests/test_models.py (ekleme, 2 test)
AC-2/AC-5 — `cropBox`/`maxWidth`+`maxHeight` eksikse Pydantic
`ValidationError`, mevcut `newFileNames`/RENAME emsaliyle aynı desen.

## backend/tests/test_orchestrator.py (ekleme, 9 test)
IMAGE_CROP/IMAGE_THUMBNAIL orchestrator entegrasyon testleri — happy
path, geçersiz geometri/boyut, sınır-dışı crop, kaynak yok/bozuk, path
whitelist ihlali.

## Durum
Kırmızı (`.venv` ile doğrulandı):
- `test_image_ops.py` → `ModuleNotFoundError: No module named 'backend.image_ops'`
- `test_orchestrator.py -k "image_crop or image_thumbnail"` → 7 failed, `AttributeError`
- `test_models.py -k "crop_box or max_width"` → 2 failed, `AttributeError`

code-copilot implementasyonu yazınca yeşile dönmesi bekleniyor.
