# Plan — orchestrator-test-helper-wiring
_Reference: atdd.md_

## Files to Modify
| File | Why | Risk |
|------|-----|------|
| backend/tests/test_orchestrator.py | AC-1: yeni `assert_apply_plan_wiring_pairs` (veya benzeri) local helper eklenir (satır ~502 civarına, `_merge_step` yardımcı fonksiyonlarının yanına). AC-2: satır 504-528 (`test_apply_plan_rename_output_filename_changes_when_new_file_names_changes`) ve satır 634-663 (`test_apply_plan_merge_output_filename_changes_when_merged_file_name_changes`) helper'ı kullanacak şekilde yeniden yazılır. | low |

## New Files
Yok — kullanıcı onayı: local helper, ayrı conftest.py fixture'ı değil.

## Dependencies
- Helper, `apply_plan(session, plan, pdf_files, tmp_path)` imzasını (mevcut testlerdeki gibi) çağıracak — `backend.orchestrator.apply_plan`'a bağımlı, import zaten dosyanın üstünde mevcut (satır 27).
- rename testi `_plan`/`_step` (satır 45-63), merge testi `_merge_step` (satır 601-609) yardımcılarını kullanıyor — helper bu üçünü değil, çağıranın kendi `build_plan_fn`'ini kabul edecek şekilde tasarlanacak (rename kendi `_step`'ini, merge kendi `_merge_step`'ini helper'a closure/callable olarak geçirir).
- Onaylanan desen (merge-tarzı): helper her `(field_value, expected_output_check)` çifti için **kendi izole tmp alt-klasöründe ayrı bir `apply_plan` çağrısı** yapar. Bu, rename testinin mevcut "tek çağrıda 3 adım" yapısını "3 ayrı çağrı, 3 ayrı alt-klasör" yapısına dönüştürür — davranışsal kapsam aynı kalır (her ad soyad çifti eski dosya yok/yeni dosya var), ama test artık merge testiyle aynı izolasyon şeklini paylaşır.

## Migration Required?
Hayır — sadece test dosyası değişiyor, şema/veri değişikliği yok.

## Risks
- (atdd.md'den taşındı) Helper imzası ileride 3. bir field-wiring testi (örn. excel_sort, satır 1708) için yetersiz kalabilir — kullanıcı bu görevi bilinçli olarak rename+merge ile sınırladı.
- rename testinin "tek plan, 3 adım" yapısı "3 ayrı apply_plan çağrısı" yapısına dönüşünce, orijinal testin auto-arttırılan step `order` (0,1,2) tek transaction içinde davranışını dolaylı da olsa doğrulayan bir yönü kayboluyor (üç adımın AYNI transaction'da birlikte işlenmesi artık test edilmiyor). Bu bilinçli bir trade-off — kullanıcı merge deseni ile helper birleşimini onayladı; "tek transaction'da çoklu adım" davranışı zaten `test_apply_plan_moves_files_into_target_folder_and_records_completed_operations` ve rollback testleri (satır 236, 266) tarafından ayrıca kapsanıyor, bu yüzden coverage kaybı yok.

## Open Questions
Yok — helper deseni (merge-tarzı, ayrı apply_plan çağrıları) kullanıcı tarafından onaylandı.
