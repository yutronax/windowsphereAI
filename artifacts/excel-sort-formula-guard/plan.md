# Plan — excel-sort-formula-guard (Saga #324)

## 1. requirements.txt
Add `openpyxl==3.1.5`. Install into `.venv`.

## 2. backend/models.py
- `OperationType.EXCEL_SORT = "Excel Sırala"` (Türkçe değer, diğer enum
  girdileriyle tutarlı).
- `PlanStep` yeni alanlar: `sortColumn: str | None = None`,
  `sortAscending: bool | None = None`, `sortedFileName: str | None = None`.
- `sortedFileName` için `mergedFileName`/`redactedFileName` ile AYNI
  path-separator field_validator.
- Yeni `model_validator(mode="after")` `excel_sort_fields_only_for_excel_sort`:
  EXCEL_SORT ise sortColumn/sortAscending/sortedFileName zorunlu dolu,
  fileNames tam 1 eleman, sortedFileName kaynakla çakışamaz; değilse
  üçü de None olmalı.

## 3. backend/security.py
- `validate_plan_paths` içine EXCEL_SORT için `sortedFileName` hedef
  path kontrolü eklenir (REDACT ile aynı satır deseni).
- Yeni `validate_excel_sort_destinations` fonksiyonu —
  `validate_redact_destinations` ile BİREBİR aynı iskelet (bilinmeyen
  var olan dosyayla çakışma + plan-geneli zincirleme hedef çakışması,
  artık redact/merge/rename hedefleriyle de karşılaştırılır).
- `validate_plan_paths` sonunda `validate_excel_sort_destinations` çağrılır.

## 4. backend/excel_sort.py (yeni modül)
- `resolve_sort_column(header_row: tuple, column_spec: str) -> int` —
  önce header text eşleşmesi (case-insensitive, strip), sonra bare
  column-letter fallback (`openpyxl.utils.column_index_from_string`,
  ValueError yakalanır). Bulunamazsa `ValueError`.
- `class ExcelSortFormulaGuardError(Exception)`.
- `sort_excel_sheet(source_path: Path, sort_column: str, ascending: bool,
  destination_path: Path) -> None`:
  - openpyxl `load_workbook(source_path)`, aktif sheet.
  - header = ilk satır; veri satırları = 2..max_row.
  - 0 veri satırı → workbook'u OLDUĞU GİBİ `destination_path`'e kopyala
    (no-op, ATDD AC6), return.
  - `resolve_sort_column` ile hedef sütun index'i bul (ValueError →
    yeniden fırlat, orchestrator çevirir).
  - TÜM veri satır aralığını tara: herhangi bir hücre `cell.data_type
    == "f"` ise `ExcelSortFormulaGuardError` fırlat, dosyaya dokunma.
  - Formül yoksa: her satırın hücre değerlerini listeye oku, sıralama
    anahtarına göre `sorted(..., key=..., reverse=not ascending)`
    (stabil sort), sıralanmış değerleri sheet'e geri yaz.
  - Geçici dosya + `Path.replace` atomik-taşı deseni (`_forward_merge`
    ile AYNI, `tempfile.mkstemp` aynı klasörde).

## 5. backend/orchestrator.py
- `_SUPPORTED_OPERATION_TYPES`'a `OperationType.EXCEL_SORT` ekle.
- `_ROLLBACK_OPERATIONS[OperationType.EXCEL_SORT] = _rollback_copy`
  (REDACT/MERGE ile aynı — kaynak değişmez, rollback sadece hedefi siler).
- `apply_plan` içinde REDACT bloğunun yanına EXCEL_SORT dalı: source_path
  = tek dosya, destination_path = `allowed_root / step.sortedFileName`,
  `record_file_operation` sonra `excel_sort.sort_excel_sheet(...)` çağır;
  `ExcelSortFormulaGuardError`/`ValueError` yakalanıp `PlanApplicationError`
  olarak yeniden fırlatılır (hiçbir FileOperation "completed" işaretlenmez,
  dışarıdaki except-bloğu zaten rollback'i tetikler).
- `target_dir` oluşturma istisnası listesine EXCEL_SORT eklenir (REDACT
  gibi kök seviyeye yazıyor).

## 6. Tests
- `backend/tests/test_models.py`: EXCEL_SORT alan zorunluluğu +
  diğer operationType'larda yasak (negatif test, Saga #319 madde 3).
- `backend/tests/test_orchestrator.py`: gerçek openpyxl fixture'ları
  (`tmp_path`'te oluşturulan .xlsx) ile:
  - formül varsa reddedilir, 0 satır değişir, dosya oluşmaz.
  - formül yoksa gerçek sıralama + wiring testi (2 farklı sortColumn/
    sortAscending → 2 farklı gözlemlenebilir sonuç).
  - header text çözümleme.
  - bare-letter çözümleme.
  - bilinmeyen sütun → hata.
  - path-outside-allowed_root reddi (REDACT'in eşdeğer testiyle aynı desen).
- `backend/tests/test_excel_sort.py` (yeni, birim seviyesi): resolve_sort_column
  ve sort_excel_sheet'in doğrudan testleri.

## Dependencies / migrations
Yok (DB şeması değişmiyor, sadece Pydantic modeli).
