# Code Diff — pdf-sayfa-araligi-secimi

Yazım motoru: bağımsız `efektor` subagent (Codex kotası dolu; kullanıcı
isteğiyle bu görevde test/kod yazımı alt ajanlara devredildi — biri test
[red], biri implementasyon [green] için ayrı ayrı çalıştırıldı).

## Files Modified
- `backend/models.py` — `OperationType.PDF_EXTRACT_PAGES`/`PDF_DELETE_PAGES`
  eklendi; `PlanStep`e `pageSpec`/`extractedFileName`/`remainingFileName`
  alanları, path-separator validator'ları ve
  `pdf_extract_pages_fields_only_for_pdf_extract_pages`/
  `pdf_delete_pages_fields_only_for_pdf_delete_pages` model_validator'ları
  eklendi (`excel_filter_fields_only_for_excel_filter` ile birebir aynı
  desen).
- `backend/orchestrator.py` — `pdf_pages` import; `_SUPPORTED_OPERATION_TYPES`,
  `_ROLLBACK_OPERATIONS` (`_rollback_copy`, 2 giriş), hedef-klasör-oluşturma
  hariç-tutma listesi güncellendi; iki yeni step-uygulama bloğu
  (EXCEL_FILTER bloğunun kopyası, `ValueError` → `PlanApplicationError`).
- `backend/tests/test_orchestrator.py` — test-yazım subagent'ı tarafından
  dosya sonuna 9 entegrasyon testi eklendi (red step'te yazıldı).

## New Files
- `backend/pdf_pages.py` — `parse_page_spec`, `extract_pdf_pages`,
  `delete_pdf_pages` + paylaşılan `_write_pages` yardımcısı (extract/delete
  arasındaki tempfile+PdfWriter tekrarını önlemek için — CAVEMAN Review'da
  gerekçelendirildi, EXCEL_SORT/EXCEL_FILTER'ın AYRI ayrı yazdığı deseni
  BİLEREK izlemedi çünkü iki fonksiyon aynı dosyada ve mantık gerçekten
  birebir aynı).
- `backend/tests/test_pdf_pages.py` — 16 unit test (red step'te yazıldı).

## Acceptance Criteria Coverage
AC-1 (extract happy path), AC-2 (delete happy path), AC-3 (ters aralık),
AC-4 (belge-dışı sayfa), AC-5 (tüm sayfalar silinirse), AC-6 (boşluk trim),
AC-7 (tekrar tekilleştirme) — hepsi hem `test_pdf_pages.py` hem
`test_orchestrator.py` seviyesinde yeşil.

## Test Evidence
- Hedeflenen testler: `25 passed, 94 deselected` (`test_pdf_pages.py` +
  `test_orchestrator.py -k "pdf_pages or PDF_EXTRACT or PDF_DELETE or page_spec"`)
- Tüm backend suite: `418 passed, 5 skipped, 9 warnings` — regresyon yok
  (EXCEL_FILTER görevinden sonraki 393'ten +25).

## Remaining Limitations
- `plan_generation.py`/LLM prompt tarafı bu ATDD'nin kapsamı DIŞINDA
  bırakıldı (atdd.md'de zaten işaretli) — PDF_EXTRACT_PAGES/PDF_DELETE_PAGES
  şu an sadece API/orchestrator seviyesinde çalışıyor, doğal dil komutuyla
  henüz tetiklenemiyor.

## Red-team Sonrası Düzeltmeler (ayrı bir subagent turu)
Bağımsız red-team incelemesi iki bulgu buldu, ayrı bir subagent turu ikisini
de kapattı (bkz. red_team.json):
1. Test paketi sayfa SAYISINI doğruluyor, KİMLİĞİNİ doğrulamıyordu (medium) —
   fixture'lar sayfa-başına ayırt edici boyut alacak şekilde güçlendirildi,
   düzeltme off-by-one'ı gerçekten enjekte edip testin kırıldığı gösterilerek
   doğrulandı.
2. "Tüm sayfalar silinemez" hata mesajı atdd.md'nin Davranış Sözleşmesi
   tablosuyla uyuşmuyordu (low) — orchestrator.py'de ayrı bir mesaj dalı
   eklendi.
Sonrasında tüm suite yeniden bağımsız doğrulandı: 418 passed, 5 skipped.

## CAVEMAN Review
- Files added: 2 (`pdf_pages.py` implementasyon, `test_pdf_pages.py` test)
  — plan.md'de zaten öngörülmüştü.
- New abstractions: `_write_pages` paylaşılan yardımcı — gerekçe: extract/
  delete AYNI dosyada, AYNI tempfile+PdfWriter iskeletini kullanıyor,
  sadece hangi sayfa indekslerinin seçildiği farklı; EXCEL_SORT/FILTER'ın
  ayrı yazdığı durumdan farklı olarak burada iki fonksiyon zaten aynı
  modülde olduğu için paylaşım doğal, ekstra dolaylılık katmanı değil.
- New public APIs: `parse_page_spec`, `extract_pdf_pages`,
  `delete_pdf_pages` — plan.md'nin doğrudan gereksinimi.
- Complexity justification: yok — tüm eklemeler EXCEL_FILTER'ın kanıtlanmış
  mimari desenini izliyor.

## Definition of Done
- Her AC implementeli, kısmi implementasyon yok, kapsam dışı işlevsellik yok.
- TODO/FIXME/placeholder/dead code yok.
- Proje konvansiyonları (EXCEL_FILTER'ın mimari deseni) takip edildi.
- `pytest backend/tests` — 418 passed, 5 skipped, 0 failed.
