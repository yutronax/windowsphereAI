# Plan — tz-naive-tarih-500-fix
_Reference: atdd.md_

## Files to Modify
| File | Why | Risk |
|------|-----|------|
| backend/main.py | `search_endpoint()`'te satır ~403 ve ~412: `dt.datetime.fromisoformat(...)` sonrası `.tzinfo is None` ise `.replace(tzinfo=dt.timezone.utc)` uygulanır (AC-1, AC-2, AC-3) | low |

## New Files
Yok.

## Dependencies
- `backend/file_search.py::search_files()` değişmiyor — zaten tz-aware `modified_after`/`modified_before` bekliyor (`st_mtime`'ı UTC ile karşılaştırıyor), main.py'nin artık her zaman tz-aware geçirmesi yeterli.
- Testler mevcut `backend/tests/test_main_integration.py` dosyasına eklenir (yeni dosya açılmıyor).

## Migration Required?
Hayır.

## Risks
Yok — kapsam tek fonksiyonun 4 satırıyla sınırlı, atdd.md'nin kendi Risks bölümü de boş.

## Open Questions
Yok.
