# Code Diff — tz-naive-tarih-500-fix (green adımı)

## Değişen dosya
- `backend/main.py` (tek dosya, `search_endpoint()` içinde, satır ~397-420 civarı)

## Ne değişti
`payload.modifiedAfter` ve `payload.modifiedBefore` için `dt.datetime.fromisoformat(...)`
çağrısından sonra, üretilen `datetime` nesnesi naive ise (`tzinfo is None`)
`dt.timezone.utc` atandı (`.replace(tzinfo=dt.timezone.utc)`). Zaten tz-aware olan
değerlere dokunulmadı — mevcut offset korunur. İki alan birbirinden bağımsız
kontrol edildi (AC-3: karışık senaryo desteği — biri naive biri aware olabilir).

```python
if payload.modifiedAfter is not None:
    try:
        modified_after = dt.datetime.fromisoformat(payload.modifiedAfter)
    except ValueError:
        raise HTTPException(status_code=422, detail=...)
    if modified_after.tzinfo is None:
        modified_after = modified_after.replace(tzinfo=dt.timezone.utc)

if payload.modifiedBefore is not None:
    try:
        modified_before = dt.datetime.fromisoformat(payload.modifiedBefore)
    except ValueError:
        raise HTTPException(status_code=422, detail=...)
    if modified_before.tzinfo is None:
        modified_before = modified_before.replace(tzinfo=dt.timezone.utc)
```

`backend/file_search.py` ve test dosyaları değiştirilmedi (kapsam dışı / dokunma kuralı).
Mevcut 422 davranışı (geçersiz ISO 8601 string) korundu, dokunulmadı.

## Final pytest sonucu
Komut:
```
.venv/Scripts/python.exe -m pytest backend/tests/test_main_integration.py backend/tests/test_file_search.py -v
```
Sonuç:
```
113 passed, 2 skipped, 5 warnings in 3.65s
```
3 hedef test dahil (`test_search_endpoint_filters_by_naive_modified_after_defaults_to_utc`,
`test_search_endpoint_filters_by_naive_modified_before_defaults_to_utc`,
`test_search_endpoint_combines_naive_modified_after_with_aware_modified_before`)
ve önceki tüm testler (regresyon yok) YEŞİL. 2 skip Windows-only olmayan
platform-bağımlı testler (symlink/permission), beklenen.

## Temizlik kontrolü
Bu değişiklik bir şey KALDIRMADI (yalnızca eksik normalizasyon eklendi), bu yüzden
proje geneli kalıntı taraması gerekmedi, kalıntı bulunmadı, ek saga temizlik görevi açılmadı.
