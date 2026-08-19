# Plan — dosya-arama-fuzzy-regex
_Reference: atdd.md_

## Files to Modify
| File | Why | Risk |
|------|-----|------|
| backend/file_search.py | `search_files()`'a `fuzzy_name: str \| None`, `name_pattern: str \| None` parametreleri + Levenshtein mesafesi hesaplayan bir yardımcı fonksiyon (`_levenshtein_distance`) eklenir (AC-1, AC-5, AC-7) | medium |
| backend/models.py | `SearchRequest`'e `fuzzyName: str \| None`, `namePattern: str \| None` alanları eklenir (AC-1, AC-2) | low |
| backend/main.py | `search_endpoint()`'te: (1) `fuzzyName`+`namePattern` birlikte verilirse 422 (AC-4), (2) `namePattern` geçersiz regex ise `re.compile()` `re.error` yakalayıp 422 (AC-3) | low |

## New Files
Yok.

## Dependencies
- Levenshtein mesafesi: stdlib'de hazır fonksiyon YOK (kullanıcı bağımlılık istemedi) — `_levenshtein_distance(a: str, b: str) -> int` klasik dinamik programlama ile `file_search.py` içinde yazılacak (O(n·m), kısa dosya adları için sorun değil).
- `re` modülü (stdlib) — `name_pattern` için `re.search(pattern, entry.name, re.IGNORECASE)` kullanılacak (case-insensitive, mevcut `name_contains`/`extension` davranışıyla tutarlı).
- Mevcut AND filtre zincirine (`backend/file_search.py::search_files()`'ın `filtered_files` döngüsü) `fuzzy_name`/`name_pattern` filtreleri eklenir — content_contains'in AYRI (ikinci) döngüsüne DEĞİL, ilk filtre döngüsüne (AC-6: diğer filtrelerle AND).
- Testler mevcut `backend/tests/test_file_search.py` ve `backend/tests/test_main_integration.py`'ye eklenir.

## Migration Required?
Hayır.

## Risks
- (atdd.md'den taşındı) ReDoS kabul edilen risk — gerçek bir mitigasyon (timeout) bu task'ta uygulanmıyor.
- `fuzzy_name` eşleşmesinin TAM olarak neyle karşılaştırılacağı netleştirilmeli: dosya adının TAMAMI mı (uzantı dahil/hariç) yoksa bir SUBSTRING penceresi mi? atdd.md'nin AC-1 örneği ("fatuura_2024" ile "fatura_2024.pdf") TAM DOSYA ADI (uzantısız gövde, `entry.stem`) karşılaştırmasını ima ediyor — code-copilot'a NOT: `entry.stem` (uzantısız) ile `fuzzy_name` karşılaştırılmalı, `entry.name` (uzantılı) değil, aksi halde ".pdf" gibi sabit bir son ek her zaman mesafeyi bozar.

## Open Questions
Yok — Levenshtein karşılaştırma hedefi (stem vs tam ad) plan aşamasında netleştirildi (yukarıdaki Risks notu code-copilot'a doğrudan talimat).
