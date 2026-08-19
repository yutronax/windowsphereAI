# Plan — pdf-sayfa-araligi-secimi
_Reference: atdd.md_

## Files to Modify
| File | Why | Risk |
|------|-----|------|
| backend/models.py | `OperationType.PDF_EXTRACT_PAGES`/`OperationType.PDF_DELETE_PAGES` enum değerleri (satır 37-58 civarı, EXCEL_FILTER'ın hemen ardına); `PlanStep`e `pageSpec` + `extractedFileName`/`remainingFileName` alanları + iki ayrı `model_validator` (`excel_filter_fields_only_for_excel_filter`, satır 326-355, birebir örnek) | low — mevcut desenin kopyası |
| backend/orchestrator.py | `_SUPPORTED_OPERATION_TYPES`e ekle (satır 47-60); `_ROLLBACK_OPERATIONS`e `_rollback_copy` ile iki giriş (satır 320-348 civarı); hedef-klasör-oluşturma hariç-tutma listesine ekle (SPLIT/REDACT/EXCEL_SORT/EXCEL_FILTER'ın yanına, ~satır 782); iki yeni step-uygulama bloğu — EXCEL_FILTER bloğu (satır 708-734) birebir örnek alınır, sadece `excel_sort.filter_excel_sheet` çağrısı yerine `pdf_pages.extract_pdf_pages`/`pdf_pages.delete_pdf_pages` çağrılır | low — mevcut EXCEL_FILTER bloğunun kopyası |

## New Files
| File | Purpose |
|------|---------|
| backend/pdf_pages.py | `parse_page_spec(page_spec: str, page_count: int) -> list[int]` (0-indexed, sıralı, tekilleştirilmiş, ValueError: ters aralık/belge-dışı/boş), `extract_pdf_pages(source_path, page_spec, destination_path)`, `delete_pdf_pages(source_path, page_spec, destination_path)` — EXCEL_SORT/EXCEL_FILTER'ın (excel_sort.py) self-contained tempfile+atomik-replace deseni izlenir (SPLIT/REDACT'ın orchestrator-owned tempfile deseni DEĞİL — bu iki en yeni operasyon aynı desende, tutarlılık için tercih edildi) |
| backend/tests/test_pdf_pages.py | `parse_page_spec`/`extract_pdf_pages`/`delete_pdf_pages` unit testleri — test_excel_filter.py ile aynı desen |

## Dependencies
- `pypdf.PdfReader`/`PdfWriter` (zaten proje genelinde kullanılıyor — SPLIT/REDACT/MERGE'de).
- `_rollback_copy(destination_path, backup_path)` (orchestrator.py:305) — değişiklik gerekmiyor, sadece haritaya 2 yeni giriş.
- `record_file_operation(...)` — EXCEL_FILTER ile aynı çağrı imzası, her operasyon için TEK kayıt (SPLIT'in N-kayıt döngüsü DEĞİL — extract/delete tek çıktı dosyası üretiyor).
- `PlanApplicationError` — `pdf_pages.py`'nin `ValueError`/(gerekirse özel bir `PdfPageSpecError` — plan aşamasında karar: EXCEL_SORT/EXCEL_FILTER'da özel guard sınıfı vardı ama bu operasyonlarda "formül guard" muadili yok, düz `ValueError` yeterli, code-copilot'a bu şekilde talimat verilecek) → orchestrator'da `PlanApplicationError`'a çevrilir.

## Migration Required?
No — DB şeması dokunulmuyor (aynı EXCEL_FILTER gerekçesi: operationType string olarak tutuluyor).

## Risks
- (atdd.md'den taşındı) `parse_page_spec`'in extract/delete arasında paylaşımı — EXCEL_SORT/EXCEL_FILTER'ın `resolve_sort_column` paylaşımıyla AYNI gerilim, ama BURADA iki ayrı fonksiyon (extract/delete) aynı MODÜLDE olduğu için isimlendirme sorunu yok (ikisi de zaten aynı dosyada, "sort" gibi yanıltıcı bir geçmiş isim taşımıyorlar).
- pypdf 0-indexed API — `parse_page_spec` 1-indexed girdiyi ALDIKTAN SONRA döndürdüğü liste 0-indexed mi 1-indexed mi olacağı code-copilot'a AÇIKÇA belirtilmeli (öneri: fonksiyon 1-indexed DÖNDÜRSÜN, çağıran taraf `- 1` yapsın — `_forward_split_page`'in `page_index + 1` dönüşümüyle TUTARLI yön, kod okuyanın "1-indexed mi 0 mı" diye excel_sort.py'ye bakmasına gerek kalmaz).
- `extractedFileName`/`remainingFileName` alanlarının fileNames ile çakışma kontrolü (EXCEL_FILTER'daki `filteredFileName` collision check ile birebir aynı) unutulursa kaynak dosya üzerine yazma riski — validator'da MUTLAKA yer almalı.

## Open Questions
Yok — atdd.md'nin Unknowns bölümündeki tek soru (yeni modül mü gerekir) bu planla çözüldü: evet, `backend/pdf_pages.py`.
