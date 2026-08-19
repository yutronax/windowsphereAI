# Code Diff — image-kirpma-thumbnail

Yazım motoru: bağımsız `efektor` subagent'lar (biri test [red], biri
implementasyon [green]).

## Files Modified
- `backend/models.py` — `CropBox` modeli (`RedactionRegion`'ın x1>x0/y1>y0
  validator deseninin kopyası, page alanı yok); `OperationType.IMAGE_CROP/
  IMAGE_THUMBNAIL`; `PlanStep`e `cropBox`, `croppedFileName`, `maxWidth`,
  `maxHeight`, `thumbnailFileName`; 2 model_validator. **Bilinçli tasarım
  kararı:** geometri/pozitiflik kontrolü Pydantic ŞEMA seviyesinde DEĞİL,
  ÇALIŞMA ZAMANINDA (`image_ops.py` içinde) yapılıyor — kırmızı testler
  `PlanApplicationError` (runtime) bekliyordu, `ValidationError` (şema)
  değil; atdd.md'nin AC-3/AC-6'sıyla tutarlı (sadece EKSİKLİK AC-2/AC-5
  şema seviyesinde, GEÇERSİZLİK AC-3/AC-6 çalışma zamanında).
- `backend/orchestrator.py` — `image_ops` import; `_SUPPORTED_OPERATION_TYPES`,
  `_ROLLBACK_OPERATIONS` (`_rollback_copy`), hedef-klasör hariç-tutma
  listesi; 2 yeni step bloğu.
- `backend/tests/test_models.py`, `backend/tests/test_orchestrator.py`
  — test-yazım subagent'ı tarafından red step'te eklendi.

## New Files
- `backend/image_ops.py` — `crop_image`, `create_thumbnail`. **KRİTİK
  kanıt:** `crop_image`, `img.crop(box)` ÇAĞRILMADAN ÖNCE `box`'ı
  `img.size` ile ELLE karşılaştırıyor (`x0<0 or y0<0 or x1>width or
  y1>height` → `ValueError`) — Pillow'un kendi (sessiz, sınır-dışını
  siyahla dolduran) toleransına ASLA güvenilmiyor, kod okunarak
  doğrulandı. `create_thumbnail`, `img.thumbnail()`'ın in-place/None-
  dönüş davranışını doğru kullanıyor (`img.thumbnail(...)` sonra
  `img.save(...)`, `None.save()` hatası YOK).
- `backend/tests/test_image_ops.py` — 12 unit test (red step'te yazıldı).

## Acceptance Criteria Coverage
AC-1 (CROP happy), AC-2 (cropBox eksik, şema), AC-3 (CROP geçersiz
geometri/sınır-dışı, runtime), AC-4 (THUMBNAIL happy, oran korunur),
AC-5 (boyut eksik, şema), AC-6 (THUMBNAIL geçersiz boyut, runtime), AC-7
(kaynak yok/bozuk) — hepsi yeşil.

## Test Evidence
- Hedeflenen testler: `20 passed`
- Tüm backend suite: `522 passed, 5 skipped, 0 failed` — regresyon yok
  (Zip görevinden sonraki 500'den +22, iki test_diff.md dışı test dahil).

## Remaining Limitations
- `plan_generation.py`/LLM prompt tarafı kapsam dışı (atdd.md'de işaretli).
- Görsel formatı dönüştürme, döndürme, filigran yok — sadece crop/thumbnail.
- Thumbnail tam-boyuta-zorlama yok, sadece oran-korumalı küçültme.

## CAVEMAN Review
- Files added: 2 (`image_ops.py`, `test_image_ops.py`) — plan.md'de öngörülmüştü.
- New abstractions: `CropBox` — gerekçeli, `RedactionRegion`'ın deseninin
  doğal bir uzantısı, yeni bir soyutlama katmanı değil.

## Definition of Done
- Her AC implementeli, kısmi implementasyon yok, kapsam dışı işlevsellik yok.
- TODO/FIXME/placeholder yok.
- Proje konvansiyonları (EXCEL_FILTER/RedactionRegion desenleri) takip edildi.
- `pytest backend/tests` — 522 passed, 5 skipped, 0 failed.
