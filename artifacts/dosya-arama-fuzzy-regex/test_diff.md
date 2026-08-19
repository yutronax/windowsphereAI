# Test Diff — dosya-arama-fuzzy-regex (RED step)

## Eklenen Testler

### `backend/tests/test_file_search.py`

- `TestSearchFilesFuzzyName::test_fuzzy_name_finds_file_within_levenshtein_distance_two` — AC-1 [Critical]. `fatura_2024.pdf` varken `fuzzy_name="fatuura_2024"` (entry.stem ile mesafe 1) dosyayı bulur.
- `TestSearchFilesFuzzyName::test_fuzzy_name_beyond_threshold_returns_empty` — AC-5 [High]. `fuzzy_name="invoice"` ile `fatura.pdf` (mesafe >2) bulunamaz, boş sonuç.
- `TestSearchFilesNamePattern::test_name_pattern_matches_only_matching_files` — AC-2 [Critical]. `name_pattern="2024-.*-fatura"` sadece `2024-01-fatura.pdf`'i bulur, `rapor.pdf`'i bulmaz.
- `TestSearchFilesFuzzyOrPatternAndOtherFilters::test_fuzzy_name_and_extension_combine_with_and_logic` — AC-6 [Medium]. `fuzzy_name` + `extension="pdf"` AND mantığı; aynı gövdeli `.docx` sonuca girmez.
- `TestSearchFilesFuzzyNonRecursive::test_fuzzy_name_does_not_find_file_in_subfolder` — AC-7 [Medium]. `allowed_root/alt/fatura_2024.pdf` (2. seviye) `fuzzy_name` ile bulunmaz (non-recursive, bilinçli kapsam kararı).

### `backend/tests/test_main_integration.py`

- `test_search_endpoint_returns_422_for_invalid_name_pattern_regex` — AC-3 [Critical]. `namePattern="("` (geçersiz regex) → 422.
- `test_search_endpoint_returns_422_when_fuzzy_name_and_name_pattern_together` — AC-4 [High]. `fuzzyName` + `namePattern` aynı istekte → 422.

## Pytest Sonucu (red step doğrulaması)

Komut:
```
.venv/Scripts/python.exe -m pytest backend/tests/test_file_search.py backend/tests/test_main_integration.py -v -k "fuzzy or Fuzzy or pattern or Pattern or regex or Regex"
```

Sonuç: **7 failed, 125 deselected** (toplam 132 test collected, import/collection hatası YOK).

Kırmızı olma nedenleri (beklenen/doğru):
- 5 test (`test_file_search.py`) → `TypeError: search_files() got an unexpected keyword argument 'fuzzy_name'` / `'name_pattern'` — fonksiyon imzasında parametreler henüz yok.
- 2 test (`test_main_integration.py`) → `assert 200 == 422` — `SearchRequest`'te `namePattern`/`fuzzyName` alanları henüz yok, Pydantic'in varsayılan `extra="ignore"` davranışı bu alanları sessizce yok sayıyor, endpoint hiç validasyon yapmadan 200 dönüyor.

Tüm kırmızılar assertion/TypeError seviyesinde — collection error veya beklenmeyen bir hata (ör. import error) yok, red step doğru şekilde tamamlandı.

## Kapsam Dışı (bu adımda yapılmadı, plan.md gereği)

- `backend/file_search.py`, `backend/models.py`, `backend/main.py` implementasyonu — sonraki (green) adımda yapılacak.
- AC-S1 (ReDoS) için ayrı bir performans testi bu red step'te eklenmedi — atdd.md'nin kendisi bunun "kabul edilen risk" olduğunu, gerçek bir timeout garantisi olmadığını belirtiyor; test stratejisi (unit 80/integration 15/e2e 5) zaten AC-1..7'yi kapsıyor.
