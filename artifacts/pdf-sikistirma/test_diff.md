# Test Diff — pdf-sikistirma

Yazım motoru: bağımsız `efektor` subagent (Codex kotası dolu; kullanıcı
isteğiyle bu görevde test/kod yazımı alt ajanlara devredildi).

## backend/tests/test_pdf_compress.py (yeni, 6 test)
`compress_pdf` unit testleri:
- Happy path (AC-1): sıkıştırılabilir içerik → `True` döner, çıktı
  kaynaktan küçük, kaynak değişmez.
- Büyüme koruması (AC-2/AC-5): zaten minimal PDF → `False` döner, çıktı
  dosyası HİÇ oluşmaz, kaynak değişmez.
- Bozuk kaynak (AC-3): dosya yok + geçersiz PDF içeriği → exception.

## backend/tests/test_orchestrator.py (ekleme, 4 test)
`OperationType.PDF_COMPRESS` orchestrator entegrasyon testleri:
- Happy path — `FileOperation` kaydı oluşur, committed.
- Büyüme koruması — **HİÇBİR** `FileOperation` kaydı oluşmaz (LIST
  deseni doğrulaması, `len(transaction.operations) == 0`).
- Bozuk kaynak → `PlanApplicationError`.
- Path whitelist ihlali (`..` tekniği, EXCEL_FILTER deseni).

## backend/tests/test_main_integration.py (ekleme, 2 test)
`/api/transactions/apply` uçtan uca — `warnings` listesinin PDF_COMPRESS
için doğru davranışı: happy path'te boş, büyüme korumasında uyarı içerir.
main.py'nin henüz yazılmamış warnings-branch'ine bağlı, plan.md'nin
tasarladığı mekanizmayı doğrudan test ediyor.

## Bilinçli atlanan
AC-4 (validator collision) için `test_models.py`'ye paralel test
EKLENMEDİ — mevcut EXCEL_FILTER'ın `filteredFileName` validator'ı için
`test_models.py`'de zaten hiç test yok (grep sıfır sonuç), bu yüzden
PDF_COMPRESS için de proje konvansiyonuyla tutarlı şekilde atlandı (bu
kapsam `test_orchestrator.py`'nin entegrasyon testlerinde dolaylı olarak
zaten kapsanıyor — geçersiz plan zaten `apply_plan` çağrılmadan Pydantic
validator'da patlar).

## Durum
Kırmızı (doğrulandı):
- `test_pdf_compress.py` → `ModuleNotFoundError: No module named 'backend.pdf_compress'`
- `test_orchestrator.py -k compress` → 4 failed, `AttributeError: PDF_COMPRESS`
- `test_main_integration.py -k compress` → 2 failed, `assert 422 == 200`

code-copilot implementasyonu (backend/pdf_compress.py + models.py +
orchestrator.py + main.py) yazınca yeşile dönmesi bekleniyor.

## Bilinmeyen (implementasyon sonrası doğrulanmalı)
`test_pdf_compress.py`'deki "sıkıştırılabilir PDF" fixture'ının gerçekten
`compress_content_streams()`/`compress_identical_objects()` ile ölçülebilir
küçülme sağlayıp sağlamadığı implementasyon yazılana kadar test edilemedi
— code-copilot subagent'ı bunu doğrulayıp gerekirse fixture'ı ayarlamalı.
