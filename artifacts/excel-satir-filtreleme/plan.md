# Plan — excel-satir-filtreleme
_Reference: atdd.md_

## Files to Modify
| File | Why | Risk |
|------|-----|------|
| backend/excel_sort.py | `resolve_sort_column` header-önce/harf-sonra sütun çözümlemesini AC-1/AC-2 gereği filtre için de kullan; `filter_excel_sheet()` + `ExcelFilterFormulaGuardError` ekle (aynı tempfile+atomik-replace deseni, `sort_excel_sheet` satır 43-114 birebir referans) | medium — paylaşılan fonksiyon isim değişikliği (aşağıda not) mevcut testleri kırabilir |
| backend/models.py | `OperationType.EXCEL_FILTER` enum değeri (satır 37-58 civarı); `PlanStep`'e `filterColumn`/`filterValue`/`filteredFileName` alanları + `excel_filter_fields_only_for_excel_filter` validator — `excel_sort_fields_only_for_excel_sort` (satır 326-355) ile BİREBİR aynı desen (zorunlu-sadece-bu-tipte, fileNames==1, output-kaynakla-çakışmaz) | low — mevcut desenin kopyası |
| backend/orchestrator.py | `_SUPPORTED_OPERATION_TYPES`e ekle (satır 47-59); `_ROLLBACK_HANDLERS`e `OperationType.EXCEL_FILTER: _rollback_copy` ekle (satır 321-341 civarı); `EXCEL_SORT` step-uygulama bloğunu (satır 681-707) birebir örnek alan yeni `if step.operationType == OperationType.EXCEL_FILTER:` bloğu; satır 745-752'deki "hedef klasör oluşturma" hariç-tutma listesine `OperationType.EXCEL_FILTER` ekle | low — mevcut EXCEL_SORT bloğunun kopyası |

## New Files
| File | Purpose |
|------|---------|
| backend/tests/test_excel_filter.py | `filter_excel_sheet`/`resolve_sort_column` (veya yeniden adlandırılmışsa `resolve_column`) için unit testler — test_excel_sort.py (satır 1-80+) ile aynı desen: header-eşleşmesi, harf-fallback, formül-guard, 0-satır no-op |
| backend/tests/test_orchestrator.py içine yeni testler (dosya yeni değil, mevcut dosyaya ekleme) | EXCEL_FILTER step uygulaması + rollback entegrasyon testleri |

## Dependencies
- `resolve_sort_column(header_row, column_spec) -> int` (backend/excel_sort.py:18) — filtre için YENİDEN KULLANILACAK. İsim hâlâ "sort" içeriyor; iki seçenek var, **kod yazım adımında (code-copilot) karar verilmeli**:
  (a) fonksiyonu olduğu gibi bırak, filter tarafında da çağır (isim yanıltıcı ama risk sıfır — test_excel_sort.py kırılmaz),
  (b) `resolve_column` olarak yeniden adlandır + `resolve_sort_column` alias bırak (isim daha doğru ama ekstra dokunuş).
  Ponytail ilkesiyle **(a) önerilir** — iş bu görüşmede netleşmedi, atdd.md'nin Risks bölümünde de işaretliydi.
- `openpyxl.utils.column_index_from_string` (zaten import edilmiş, excel_sort.py:6).
- `_rollback_copy(destination_path, backup_path)` (orchestrator.py:304) — değişiklik gerekmiyor, sadece haritaya yeni giriş.
- `record_file_operation(...)` — EXCEL_SORT ile aynı çağrı imzası.

## Migration Required?
No — DB şeması dokunulmuyor (Transaction/FileOperation tabloları operationType'ı string olarak tutuyor, yeni enum değeri şema değişikliği gerektirmiyor).

## Risks
- (atdd.md'den taşındı) `resolve_sort_column` paylaşımı için isim kararı — yukarıda Dependencies'te çözüldü: (a) yeniden adlandırma yapma.
- (atdd.md'den taşındı) Üçüncü parametre-ekleme noktası doğrulandı: proje hafızasındaki "capabilities.json" bu projede karşılığı **`orchestrator._SUPPORTED_OPERATION_TYPES`** (satır 47-59) — bu görüşmede kesinleşti, Unknowns'tan çıkarıldı. `plan_generation.py`/LLM prompt tarafı (dördüncü nokta, doğal dilden filterColumn çıkarma) kapsam dışı bırakıldığı için BURADA değiştirilmiyor — yani EXCEL_FILTER, LLM planı hiç üretmeyeceği için bu ATDD sonunda yalnızca API/unit-test seviyesinde çalışır hale gelecek, uçtan uca kullanıcı komutu ile TETİKLENEMEZ. Bu bilinçli bir sınırlama (ATDD Kapsam Dışı ile tutarlı) ama code-copilot ve red-team'in "neden çalışmıyor" diye şaşırmaması için burada açıkça not edildi.
- `filterValue` tip karşılaştırması (`str(hücre) == str(değer)`) atdd.md'de varsayım olarak işaretliydi — code-copilot bunu `_sort_key`'deki None-güvenli karşılaştırmadan FARKLI, basit string-eşitliği olarak uygulamalı (filtrede sıralama yok, tip karşılaştırma sorunu yok).

## Open Questions
Yok — atdd.md'deki tüm Unknowns bu plan sırasında koddan doğrulanarak çözüldü (üçüncü parametre noktası = `_SUPPORTED_OPERATION_TYPES`, tespit edildi).
