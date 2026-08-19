# Code Diff — orchestrator-test-helper-wiring

Codex kotası dolu (15 Eylül 2026'ya kadar) olduğu için bu dar kapsamlı
test-refactor işi kullanıcı onayıyla Claude alt ajanı (Haiku modeli,
`efektor` subagent) tarafından yazıldı — plan.md'nin Files to Modify
listesindeki tek dosyayla sınırlı.

## Değiştirilen dosya
- `backend/tests/test_orchestrator.py`

## Değişiklik özeti
1. **Yeni helper**: `_assert_apply_plan_wiring_pairs(session, tmp_path, pairs)`
   (satır ~601-626, `_merge_step`'in üstüne eklendi). `pairs` listesindeki
   her `(setup_fn, build_plan_fn, pdf_files, check_fn)` dörtlüsü için
   `tmp_path` altında izole bir alt-klasör (`pair_0`, `pair_1`, ...)
   oluşturur, `apply_plan`'ı bir kez çağırır, `check_fn` ile doğrular.
   Try/except sarmalaması yok — assert/exception olduğu gibi yükselir.
2. **`test_apply_plan_rename_output_filename_changes_when_new_file_names_changes`**
   (satır 504-527): tek apply_plan çağrısındaki 3-adımlı yapıdan, helper
   aracılığıyla 3 ayrı izole apply_plan çağrısına dönüştürüldü (plan.md'de
   onaylanan merge-deseni). Davranışsal kapsam korundu: her (eski, yeni)
   isim çifti için eski dosya yok + yeni dosya var.
3. **`test_apply_plan_merge_output_filename_changes_when_merged_file_name_changes`**
   (satır 658-680): manuel run1/run2 alt-klasörlerinden helper'ın
   pair_0/pair_1 desenine taşındı.
4. `backend/orchestrator.py` (production kod) **değişmedi**.

## Doğrulama
```
cd backend/.. && python -m pytest backend/tests/test_orchestrator.py -v
141 passed, 1 skipped in 18.36s
```
0 FAIL — regresyon yok.
