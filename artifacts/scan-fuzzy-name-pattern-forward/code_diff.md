# code_diff.md — scan-fuzzy-name-pattern-forward (GREEN step)

Değiştirilen tek dosya: `backend/main.py`

## Değişiklikler

1. Yeni ortak yardımcı fonksiyon `_validate_fuzzy_regex_or_422(payload: SearchRequest) -> None`
   eklendi (`_parse_search_date`'in hemen altına). `search_endpoint`'teki eski
   satır içi fuzzyName/namePattern doğrulama mantığı (birlikte verilirse 422,
   geçersiz regex ise 422) davranış/mesaj değişmeden buraya taşındı.
2. `search_endpoint()` artık eski satır içi kodu değil
   `_validate_fuzzy_regex_or_422(payload)` çağrısını kullanıyor.
3. `start_search_scan()`'e allowed_root/410 kontrolünden sonra, scan_id
   üretiminden önce aynı `_validate_fuzzy_regex_or_422(payload)` çağrısı eklendi
   — geçersiz fuzzyName/namePattern kombinasyonunda tarama hiç başlamıyor
   (AC-3/AC-4).
4. `start_search_scan()`'in `_run_scan`'e geçirdiği `kwargs` sözlüğüne
   `"fuzzy_name": payload.fuzzyName` ve `"name_pattern": payload.namePattern`
   eklendi.
5. `_run_scan()` imzasına `fuzzy_name: str | None = None,
   name_pattern: str | None = None` parametreleri eklendi ve bunlar
   `search_files()` çağrısına `fuzzy_name=fuzzy_name, name_pattern=name_pattern`
   olarak forward edildi.

`backend/tests/test_search_scan.py` ve `backend/file_search.py`'ye dokunulmadı.

## Final pytest sonucu

```
.venv/Scripts/python.exe -m pytest backend/tests/ -v
...
================= 371 passed, 4 skipped, 9 warnings in 23.89s =================
```

Tüm 4 yeni AC-1..4 testi dahil TÜM proje testleri YEŞİL, 0 FAILED. Skip edilen
4 test Windows-only skip'ler (mevcut davranış, bu görevle ilgisiz).
