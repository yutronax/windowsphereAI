# test_diff.md — tz-naive-tarih-500-fix (RED STEP)

Değiştirilen dosya: `backend/tests/test_main_integration.py` (sadece EKLEME, mevcut testler değiştirilmedi).
İmplementasyon kodu (`backend/main.py`, `backend/file_search.py`) HENÜZ DEĞİŞTİRİLMEDİ.

## Eklenen testler

1. `test_search_endpoint_filters_by_naive_modified_after_defaults_to_utc` — **AC-1 [Critical]**
   `modifiedAfter="2024-01-01T00:00:00"` tarzı offset'siz (naive) bir ISO 8601 string ile
   `/api/search` çağrılınca 500 yerine 200 dönmesi ve UTC varsayılarak dosyaların doğru
   filtrelenmesi bekleniyor. tmp_path'te mtime'ı 1 saat önceye alınmış bir dosya (`dosya1.txt`)
   ve yeni oluşturulmuş bir dosya (`dosya2.txt`) kullanılıyor.

2. `test_search_endpoint_filters_by_naive_modified_before_defaults_to_utc` — **AC-2 [Critical]**
   Aynı senaryonun `modifiedBefore` ile naive string kullanan karşılığı.

3. `test_search_endpoint_combines_naive_modified_after_with_aware_modified_before` — **AC-3 [High]**
   `modifiedAfter` naive + `modifiedBefore` tz-aware (`+03:00`) birlikte verildiğinde, üç dosyalık
   (çok eski / aralıkta / çok yeni) bir senaryoda her iki alanın bağımsız doğru normalize edilip
   AND mantığıyla birleştiğini doğruluyor.

## AC-4 ve AC-5 — regresyon (zaten mevcut, yeni ekleme yapılmadı)

- **AC-4 [High]**: `test_search_endpoint_returns_422_for_invalid_modified_after_format` ve
  `test_search_endpoint_returns_422_for_invalid_modified_before_format` zaten dosyada mevcut —
  tamamen bozuk (`"not-a-valid-iso-date"` / `"invalid-date"`) string için 422 davranışını
  kanıtlıyor. Bu task'ın kapsamına göre davranış değişmiyor, bu yüzden ek test eklenmedi.
- **AC-5 [Medium]**: `test_search_endpoint_filters_by_modified_after` ve
  `test_search_endpoint_filters_by_modified_before` zaten tz-aware (`+00:00`) string'lerle
  yazılmış ve 200 dönüşünü doğruluyor. Bu task'ın kapsamına göre davranış değişmiyor, bu yüzden
  ek test eklenmedi.

## Pytest sonucu (red step — beklenen)

Komut:
```
.venv/Scripts/python.exe -m pytest backend/tests/test_main_integration.py -v -k "naive or Naive or tz or timezone"
```

Sonuç: **3 failed, 61 deselected, 1 warning** (toplam 64 test dosyada, filtre 3 tanesini seçti; hepsi kırmızı).

Kırmızı olan 3 test de import/collection hatası DEĞİL, gerçek çalışma zamanı hatasıyla düşüyor:

```
backend\file_search.py:134: in search_files
    if file_mtime < modified_after:
TypeError: can't compare offset-naive and offset-aware datetimes
```

Bu, `backend/main.py::search_endpoint()`'in naive `modifiedAfter`/`modifiedBefore` string'ini
`dt.datetime.fromisoformat()` ile parse edip tzinfo eklemeden `search_files()`'a geçirmesi,
`search_files()`'ın ise dosya `st_mtime`'ını her zaman tz-aware (UTC) üretip karşılaştırmasından
kaynaklanan, ATDD'de tarif edilen TAM olarak beklenen hata — henüz düzeltme yapılmadığı için
bu davranış BEKLENEN (red step) sonuçtur.

Kırılan testler:
- `test_search_endpoint_filters_by_naive_modified_after_defaults_to_utc`
- `test_search_endpoint_filters_by_naive_modified_before_defaults_to_utc`
- `test_search_endpoint_combines_naive_modified_after_with_aware_modified_before`

Diğer 61 test (filtreye uymayan tüm dosya) deselected — dokunulmadı, mevcut davranışları etkilenmedi.
