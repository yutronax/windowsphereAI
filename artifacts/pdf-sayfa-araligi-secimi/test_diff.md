# Test Diff — pdf-sayfa-araligi-secimi

Yazım motoru: bağımsız `efektor` subagent (Codex kotası dolu; bu görevde
kullanıcı isteğiyle Codex yerine bir alt ajan test/kod yazımını üstlendi,
Claude sadece orkestre etti/denetledi).

## backend/tests/test_pdf_pages.py (yeni, 16 test)
`parse_page_spec`/`extract_pdf_pages`/`delete_pdf_pages` unit testleri
(test_excel_filter.py ile aynı desen):
- `test_parse_page_spec_returns_mixed_discrete_and_range_pages_in_order` — AC-1/AC-2 girdisi
- `test_parse_page_spec_trims_whitespace_and_matches_unspaced_equivalent` — AC-6
- `test_parse_page_spec_raises_value_error_for_reversed_range` — AC-3
- `test_parse_page_spec_raises_value_error_for_page_number_beyond_document` — AC-4
- `test_parse_page_spec_deduplicates_repeated_pages_preserving_order` — AC-7
- `test_parse_page_spec_raises_value_error_for_empty_string` / `_blank_string` — girdi doğrulama
- `test_extract_pdf_pages_writes_selected_pages_in_original_order` — AC-1
- `test_extract_pdf_pages_does_not_modify_the_source_file` — Davranış Sözleşmesi
- `test_extract_pdf_pages_writes_no_file_when_page_spec_is_invalid` — AC-3
- `test_extract_pdf_pages_writes_no_file_when_page_spec_is_out_of_document_range` — AC-4
- `test_delete_pdf_pages_writes_remaining_pages_in_original_order` — AC-2
- `test_delete_pdf_pages_does_not_modify_the_source_file` — Davranış Sözleşmesi
- `test_delete_pdf_pages_raises_value_error_when_all_pages_are_deleted` — AC-5
- `test_delete_pdf_pages_writes_no_file_when_page_spec_is_invalid` — AC-3
- `test_delete_pdf_pages_writes_no_file_when_page_spec_is_out_of_document_range` — AC-4

## backend/tests/test_orchestrator.py (ekleme, dosya sonuna, 9 test)
`OperationType.PDF_EXTRACT_PAGES`/`PDF_DELETE_PAGES` orchestrator
entegrasyon testleri:
- `test_apply_plan_extracts_pdf_pages_happy_path` — AC-1
- `test_apply_plan_deletes_pdf_pages_happy_path` — AC-2
- `test_apply_plan_rejects_pdf_extract_pages_with_reversed_range` — AC-3
- `test_apply_plan_rejects_pdf_extract_pages_with_out_of_document_page_number` — AC-4
- `test_apply_plan_rejects_pdf_delete_pages_with_reversed_range` — AC-3
- `test_apply_plan_rejects_pdf_delete_pages_with_out_of_document_page_number` — AC-4
- `test_apply_plan_rejects_pdf_delete_pages_when_all_pages_are_deleted` — AC-5
- `test_apply_plan_rejects_pdf_extract_pages_of_a_path_outside_allowed_root` — path-whitelist (EXCEL_FILTER deseni)
- `test_apply_plan_rejects_pdf_delete_pages_of_a_path_outside_allowed_root` — path-whitelist (EXCEL_FILTER deseni)

## Bilinen kapsam sınırı
Testler sayfa SAYISINI doğruluyor (blank pypdf sayfaları birbirinden ayırt
edilemediği için içerik-bazlı sıra doğrulaması yapılmıyor) — count-based
assertion, EXCEL_FILTER'daki değer-bazlı assertion'dan daha zayıf bir
kanıt. code-copilot/red-team'e bu sınırlama açıkça bildirildi.

## Durum
Kırmızı (doğrulandı):
- `test_pdf_pages.py` → `ModuleNotFoundError: No module named 'backend.pdf_pages'`
- `test_orchestrator.py -k "PDF_EXTRACT or PDF_DELETE"` → 7 test `AttributeError` (enum henüz yok)

code-copilot implementasyonu (backend/pdf_pages.py + models.py + orchestrator.py)
yazınca yeşile dönmesi bekleniyor.
