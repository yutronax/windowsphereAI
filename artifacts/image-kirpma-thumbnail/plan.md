# Plan — image-kirpma-thumbnail
_Reference: atdd.md_

## Unknowns'ın Çözümü (kod incelemesiyle netleşti)

**Pillow API'si (gerçek kurulumla doğrulandı, `.venv` zaten Pillow'a
sahip, yeni kurulum GEREKMEDİ):**
- `Image.crop(box: tuple[float,float,float,float]) -> Image` — YENİ bir
  `Image` nesnesi DÖNDÜRÜR, kaynağı DEĞİŞTİRMEZ (`img.crop((x0,y0,x1,y1))`).
- `Image.thumbnail(size: tuple[float,float], ...) -> None` — **in-place**,
  HİÇBİR ŞEY DÖNDÜRMEZ, `img`'in KENDİSİNİ değiştirir (`img.thumbnail((w,h))`
  sonra `img.save(...)` çağrılmalı — `new_img = img.thumbnail(...)`
  YAZILIRSA `new_img` `None` olur, bu code-copilot'a AÇIKÇA uyarılmalı).

**`cropBox` şeması:** `RedactionRegion` (models.py) EMSAL alınacak ama
BİREBİR AYNI DEĞİL — `RedactionRegion` PDF-nokta-uzayında (`page` alanı
dahil), IMAGE_CROP ise PİKSEL uzayında ve tek-görsel (sayfa kavramı yok).
Yeni, AYRI bir `CropBox` modeli (`x0: float, y0: float, x1: float,
y1: float`) — `RedactionRegion`'ın `x1_greater_than_x0_and_y1_greater_than_y0`
model_validator'ı BİREBİR kopyalanacak (AC-3'ün "geçersiz geometri" kontrolü).

## Files to Modify
| File | Why | Risk |
|------|-----|------|
| backend/models.py | YENİ `CropBox` modeli (`RedactionRegion`'ın x1>x0/y1>y0 validator deseninin kopyası, page alanı OLMADAN); `OperationType.IMAGE_CROP/IMAGE_THUMBNAIL`; `PlanStep`e `cropBox: CropBox \| None`, `croppedFileName`, `maxWidth: int \| None`, `maxHeight: int \| None`, `thumbnailFileName`; ilgili model_validator'lar (EXCEL_FILTER'ın "==1 kaynak" deseni, `maxWidth`/`maxHeight` için pozitif-tamsayı kontrolü) | low — mevcut desenlerin kopyası |
| backend/orchestrator.py | `from backend import image_ops` import; `_SUPPORTED_OPERATION_TYPES`e ekle; `_ROLLBACK_OPERATIONS`e `IMAGE_CROP/IMAGE_THUMBNAIL: _rollback_copy`; hedef-klasör-oluşturma hariç-tutma listesine ekle; 2 yeni step-uygulama bloğu (EXCEL_FILTER'ın record+completed deseni) | low — mevcut desenin kopyası |

## New Files
| File | Purpose |
|------|---------|
| backend/image_ops.py | `crop_image(source_path: Path, box: tuple[float,float,float,float], destination_path: Path) -> None` (kaynağın GERÇEK piksel sınırlarını (`img.size`) aşan bir `box` için `ValueError` — `pdf_redact.py`'nin sınır kontrolü EMSAL, epsilon toleransı GEREKMİYOR çünkü burada rasterize/ölçek dönüşümü yok, doğrudan piksel karşılaştırması), `create_thumbnail(source_path: Path, max_width: int, max_height: int, destination_path: Path) -> None` (`img.thumbnail((max_width, max_height))` in-place, SONRA `img.save(destination_path)` — plan.md'de doğrulanan API şekli) |
| backend/tests/test_image_ops.py | `crop_image`/`create_thumbnail` unit testleri |

## Dependencies
- `PIL.Image` (Pillow, ZATEN kurulu — `pdf_redact.py`'de zaten kullanılıyor).
- `_rollback_copy` — değişiklik gerekmiyor.
- `RedactionRegion`'ın `x1_greater_than_x0_and_y1_greater_than_y0`
  model_validator deseni — `CropBox`'a KOPYALANACAK (paylaşılmayacak,
  proje konvansiyonu: her model kendi validator'ını taşır).

## Migration Required?
No — DB şeması dokunulmuyor.

## Risks
- (atdd.md'den taşındı, ÇÖZÜLDÜ) Pillow API'si gerçek kurulumla
  doğrulandı — `thumbnail()`'ın in-place/None-dönüş davranışı code-copilot'a
  AÇIKÇA aktarılmalı (yanlış kullanımda `None.save()` gibi bariz bir
  hataya yol açar, ama testler bunu HEMEN yakalar).
- `crop_image`'in sınır kontrolü: `box`'un `img.size`'ı (width, height)
  aşıp aşmadığı kontrolü code-copilot'ta dikkatli yazılmalı — `img.crop()`
  kendisi sınır dışı bir `box` için HATA VERMEZ (siyah/boş alanla
  doldurur, sessizce) — bu yüzden AC-3'ün "kaynak sınırlarını aşan alan"
  kontrolü `crop_image` İÇİNDE, `img.crop()` ÇAĞRILMADAN ÖNCE elle
  yapılmalı, Pillow'un kendi (sessiz) toleransına GÜVENİLMEMELİ.

## Open Questions
Yok — atdd.md'nin iki Unknown'ı da bu planla kod incelemesiyle çözüldü.
