# Plan — scan-fuzzy-name-pattern-forward
_Reference: atdd.md_

## Files to Modify
| File | Why | Risk |
|------|-----|------|
| backend/main.py | `_validate_fuzzy_regex_or_422(payload)` ortak yardımcı fonksiyonu eklenir (satır 520-536'daki mevcut mantık `_parse_search_date` deseniyle aynı şekilde çıkarılır), `search_endpoint()` bunu çağıracak şekilde güncellenir, `start_search_scan()`'e de aynı çağrı + `_run_scan`'e `fuzzy_name`/`name_pattern` parametreleri eklenir | low |

## New Files
Yok.

## Dependencies
- `backend/file_search.py::search_files()` — DEĞİŞMİYOR, zaten `fuzzy_name`/`name_pattern` kabul ediyor (Saga #316).
- Testler mevcut `backend/tests/test_search_scan.py`'ye eklenir.

## Migration Required?
Hayır.

## Risks
Yok — atdd.md'nin kendi Risks bölümü de boş, kapsam dar ve mevcut davranışın kopyalanması.

## Open Questions
Yok — atdd.md'nin Assumptions'ı (ortak yardımcı fonksiyon) burada netleştirildi: `_parse_search_date` ile AYNI desen (satır 485'teki mevcut refaktör örneği) izlenerek `_validate_fuzzy_regex_or_422` eklenecek.
