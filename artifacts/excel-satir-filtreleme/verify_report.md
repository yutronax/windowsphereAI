# Verify Report — excel-satir-filtreleme
_Reference: atdd.md, plan.md, test_diff.md, code_diff.md_

## Verification Gates
| # | Gate | Result | Evidence / Reason |
|---|------|--------|--------------------|
| 1 | Dosya konumu | PASS | `git status --short` ile 3 değiştirilmiş (`backend/excel_sort.py`, `backend/models.py`, `backend/orchestrator.py`) + 2 test dosyası (`backend/tests/test_excel_filter.py` yeni, `backend/tests/test_orchestrator.py` değişiklik) doğrulandı, `Read` ile içerikleri kontrol edildi |
| 2 | Build/derleme | PASS | `.venv/Scripts/python -c "import backend.excel_sort, backend.models, backend.orchestrator"` → "import OK" |
| 3 | Supabase şema/canlı doğrulama | N/A | Değişen dosyalarda Supabase çağrısı/migration yok (`grep -il supabase backend/` sıfır sonuç); proje SQLite/SQLAlchemy kullanıyor |
| 4 | Lint | N/A | Proje backend için ruff/eslint benzeri bir linter tanımlamıyor (`requirements-dev.txt` sadece pytest/pytest-mock içeriyor, kök dizinde ruff.toml/pyproject.toml yok) |
| 5 | Type check | N/A | Proje backend için pyright/mypy tanımlamıyor (aynı gerekçe) |
| 6 | Unit testler | PASS | `pytest backend/tests -q` → **393 passed, 5 skipped (pre-existing), 0 failed**, 30.10s. Yeni testler dahil: `test_excel_filter.py` (10 test) + `test_orchestrator.py`'ye eklenen 7 EXCEL_FILTER entegrasyon testi, hepsi yeşil |
| 7 | E2E testler | N/A | `playwright.config.ts` mevcut ama frontend UI için — bu görev sadece backend Python değişikliği, EXCEL_FILTER'a ulaşan bir e2e senaryo yok (plan_generation.py/LLM tarafı bilinçli olarak kapsam dışı) |
| 8 | Lighthouse (performans) | N/A | Rendered web UI dokunulmadı |
| 9 | Erişilebilirlik | N/A | Aynı gerekçe (gate 8) |
| 10 | Güvenlik taraması | PASS | `security-scan` runner, 5 değişen dosya kapsamında: `secrets: PASS`, `python_sast: PASS`, `python_deps: PASS`, `node_deps: PASS`, verdict `PASS` |
| 11 | AI code review | PENDING (red-team) | Sonraki pipeline adımına bırakıldı |
| 12 | Görsel regresyon | N/A | Rendered web UI dokunulmadı |
| 13 | İnsan onayı | PENDING | Kullanıcı henüz onaylamadı |

## AC -> Test Mapping
1. [Critical] Happy path (başlık eşleşmesiyle filtrele) -> `test_filter_excel_sheet_matches_by_header_text_and_keeps_matching_rows`, `test_apply_plan_filters_excel_rows_when_there_are_no_formulas` -> PASS
2. [Critical] "Ad" gibi kısa başlık harfle karışmasın -> `test_filter_excel_sheet_prefers_header_text_over_bare_letter_interpretation`, `test_apply_plan_excel_filter_prefers_header_text_over_bare_letter_interpretation` -> PASS
3. [High] Sütun çözülemiyor -> `PlanApplicationError` -> `test_filter_excel_sheet_raises_value_error_for_unknown_column`, `test_apply_plan_rejects_excel_filter_with_unknown_column` -> PASS
4. [High] 0 satır eşleşti -> header-only dosya, hata yok -> `test_filter_excel_sheet_writes_header_only_file_when_no_row_matches`, `test_apply_plan_excel_filter_writes_header_only_file_when_no_row_matches` -> PASS
5. [High] Formül guard -> `test_filter_excel_sheet_raises_formula_guard_error_when_a_data_cell_is_a_real_formula`, `test_filter_excel_sheet_leaves_source_untouched_when_formula_guard_triggers`, `test_apply_plan_rejects_excel_filter_when_a_data_row_contains_a_formula` -> PASS
6. [Medium] Boş sayfa no-op -> `test_filter_excel_sheet_is_a_no_op_copy_when_only_header_row_exists`, `test_filter_excel_sheet_is_a_no_op_copy_for_a_completely_empty_sheet` -> PASS
- (ekstra) Kaynak dosya asla değişmez -> `test_filter_excel_sheet_does_not_modify_the_source_file` -> PASS
- (ekstra) Path whitelist ihlali reddedilir -> `test_apply_plan_rejects_excel_filter_of_a_path_outside_allowed_root` -> PASS
- (ekstra) Bare-letter fallback -> `test_filter_excel_sheet_supports_bare_column_letter_when_no_header_matches`, `test_apply_plan_excel_filter_resolves_bare_letter_column_when_no_header_matches` -> PASS

## Coverage / Quality Notes
- Tüm Acceptance Criteria (AC-1..AC-6) en az bir unit + bir entegrasyon testiyle kaplı; test_strategy hedefine (75/20/5) yakın bir dağılım (17 yeni test, 15'i unit/entegrasyon backend, e2e yok — atdd.md'nin kararıyla tutarlı).
- Boş sonuç (AC-4) ile sütun-çözülemedi hatası (AC-3) ayrı testlerle ayrı ayrı doğrulandı — davranış sözleşmesindeki "aynı dönüşe indirgenmesin" gereksinimi karşılandı.
- Gate 4/5 N/A olması projenin genel durumu — EXCEL_SORT (Saga #324) görevinde de aynı N/A gerekçesi geçerliydi, bu görevle ilgisiz bir eksiklik değil.
