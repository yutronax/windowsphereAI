# Test Diff — excel-satir-filtreleme

Yazım motoru: Claude (istisna — Codex kotası 2026-09-15'e kadar dolu,
kullanıcı onayıyla; red-team adımı bağımsız subagent ile doğrulanacak).

## backend/tests/test_excel_filter.py (yeni)
`filter_excel_sheet`/`ExcelFilterFormulaGuardError` üzerinde unit testler
(test_excel_sort.py ile aynı desen):
- `test_filter_excel_sheet_matches_by_header_text_and_keeps_matching_rows` — AC-1
- `test_filter_excel_sheet_prefers_header_text_over_bare_letter_interpretation` — AC-2
- `test_filter_excel_sheet_supports_bare_column_letter_when_no_header_matches` — AC-2 (fallback yolu)
- `test_filter_excel_sheet_raises_value_error_for_unknown_column` — AC-3
- `test_filter_excel_sheet_does_not_modify_the_source_file` — Davranış Sözleşmesi #1
- `test_filter_excel_sheet_writes_header_only_file_when_no_row_matches` — AC-4 / Davranış Sözleşmesi #8
- `test_filter_excel_sheet_raises_formula_guard_error_when_a_data_cell_is_a_real_formula` — AC-5
- `test_filter_excel_sheet_leaves_source_untouched_when_formula_guard_triggers` — AC-5
- `test_filter_excel_sheet_is_a_no_op_copy_when_only_header_row_exists` — AC-6
- `test_filter_excel_sheet_is_a_no_op_copy_for_a_completely_empty_sheet` — AC-6

## backend/tests/test_orchestrator.py (ekleme, EXCEL_SORT bloğunun hemen ardına)
`OperationType.EXCEL_FILTER` + `PlanStep.filterColumn/filterValue/filteredFileName`
üzerinde orchestrator entegrasyon testleri:
- `test_apply_plan_rejects_excel_filter_when_a_data_row_contains_a_formula` — AC-5
- `test_apply_plan_filters_excel_rows_when_there_are_no_formulas` — AC-1
- `test_apply_plan_excel_filter_prefers_header_text_over_bare_letter_interpretation` — AC-2
- `test_apply_plan_excel_filter_resolves_bare_letter_column_when_no_header_matches` — AC-2 (fallback)
- `test_apply_plan_rejects_excel_filter_with_unknown_column` — AC-3
- `test_apply_plan_excel_filter_writes_header_only_file_when_no_row_matches` — AC-4 / Davranış Sözleşmesi #8
- `test_apply_plan_rejects_excel_filter_of_a_path_outside_allowed_root` — mevcut path-whitelist altyapısı (REDACT/EXCEL_SORT ile aynı desen)

## Durum
Kırmızı (doğrulandı): `test_excel_filter.py` `ImportError` ile collection'da
başarısız oluyor (`ExcelFilterFormulaGuardError`/`filter_excel_sheet` henüz
`backend/excel_sort.py`'de yok) — beklenen red durum. `test_orchestrator.py`
eklentisi de aynı nedenle (`OperationType.EXCEL_FILTER` henüz `models.py`'de
yok) `AttributeError`/`ValidationError` ile kırmızı olacak, code-copilot
implementasyonu yazınca yeşile dönmesi bekleniyor.
