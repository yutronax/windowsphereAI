# Code Diff — excel-satir-filtreleme

Yazım motoru: Claude (istisna — Codex kotası 2026-09-15'e kadar dolu,
kullanıcı onayıyla).

## Files Modified
- `backend/excel_sort.py` — `ExcelFilterFormulaGuardError` sınıfı ve
  `filter_excel_sheet(source_path, filter_column, filter_value,
  destination_path)` fonksiyonu eklendi. `resolve_sort_column` DEĞİŞMEDEN
  yeniden kullanıldı (plan.md'nin (a) seçeneği — isim değiştirilmedi,
  `test_excel_sort.py` etkilenmedi).
- `backend/models.py` — `OperationType.EXCEL_FILTER` eklendi; `PlanStep`e
  `filterColumn`/`filterValue`/`filteredFileName` alanları,
  `filteredFileName` için path-separator validator'ı, ve
  `excel_filter_fields_only_for_excel_filter` model_validator'ı eklendi
  (`excel_sort_fields_only_for_excel_sort` ile birebir aynı desen).
- `backend/orchestrator.py` — `_SUPPORTED_OPERATION_TYPES`,
  `_ROLLBACK_OPERATIONS` (`_rollback_copy`), hedef-klasör-oluşturma
  hariç-tutma listesine `OperationType.EXCEL_FILTER` eklendi; EXCEL_SORT
  step-uygulama bloğunun birebir kopyası olan yeni bir `if
  step.operationType == OperationType.EXCEL_FILTER:` bloğu eklendi
  (`filter_excel_sheet` çağrısı, `ExcelFilterFormulaGuardError`/`ValueError`
  → `PlanApplicationError` çevrimi).

## New Files
Yok — plan.md'de öngörülen tek yeni dosya (`test_excel_filter.py`)
test-copilot adımında zaten yazılmıştı.

## Acceptance Criteria Coverage
- AC-1 (happy path, tam eşitlik) — `filter_excel_sheet` + orchestrator testi.
- AC-2 (başlık-önce/harf-sonra çözümleme) — `resolve_sort_column` paylaşılan
  fonksiyon üzerinden, hem "Ad" gibi kısa başlıkla hem bare-letter fallback
  ile test edildi.
- AC-3 (sütun çözülemiyor) — `ValueError` → `PlanApplicationError`.
- AC-4 (0 satır eşleşti, header-only dosya) — sessiz başarı DEĞİL, dosya
  oluşuyor, hata fırlatılmıyor.
- AC-5 (formül guard) — `ExcelFilterFormulaGuardError`, sıfır satır işlenir.
- AC-6 (boş sayfa no-op) — `data_row_count <= 0` erken dönüş.

## Remaining Limitations
- `plan_generation.py`/LLM prompt tarafı bu ATDD'nin kapsamı DIŞINDA
  bırakıldı (kullanıcı kararı) — EXCEL_FILTER şu an sadece API/orchestrator
  seviyesinde çalışıyor, doğal dil komutuyla LLM tarafından ÜRETİLEMİYOR.
  Ayrı bir Saga task gerekiyor.

## Assumptions
- `filterValue` karşılaştırması `str(hücre) == str(filterValue)` — atdd.md'de
  varsayım olarak işaretlenmişti, plan.md'de netleştirildi (basit string
  eşitliği, `_sort_key`'in None-güvenli sıralama mantığı KULLANILMADI çünkü
  filtrede sıralama yok).

## CAVEMAN Review
- Files added: 0 implementasyon dosyası (sadece 3 mevcut dosyaya ekleme).
- New abstractions: yok — `filter_excel_sheet`, `sort_excel_sheet` ile
  birebir aynı iskeleti (tempfile+atomik-replace, formula-guard, no-op)
  kopyalıyor, ortak bir yardımcıya çıkarılmadı çünkü tek çağıran var ve
  ikisi arasında (satır sıralama vs. satır filtreleme) davranış farkı var.
- New helper functions: 0 (mevcut `resolve_sort_column` yeniden kullanıldı).
- New public APIs: `filter_excel_sheet`, `ExcelFilterFormulaGuardError` —
  gerekçe: ATDD AC-1/AC-5'in doğrudan gereksinimi, EXCEL_SORT'un genel
  kabul görmüş mimari desenini takip ediyor.
- Complexity justification: yok — tüm eklemeler var olan EXCEL_SORT
  desenini birebir izliyor, yeni bir soyutlama/konfigürasyon eklenmedi.

## Definition of Done
- Her AC implementeli, kısmi implementasyon yok, kapsam dışı işlevsellik yok.
- TODO/FIXME/placeholder/dead code/unused helper yok.
- Proje konvansiyonları (EXCEL_SORT'un mimari deseni) birebir takip edildi.
- `pytest backend/tests` — 393 passed, 5 skipped (pre-existing), 0 failed.
