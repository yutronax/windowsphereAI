# Green Step — code_diff.md (Saga #316: dosya-arama-fuzzy-regex)

## Değişen dosyalar

### `backend/file_search.py`
- `import re` eklendi.
- `_levenshtein_distance(a: str, b: str) -> int`: stdlib bağımlılığı olmadan
  klasik DP ile Levenshtein mesafesi hesaplayan yardımcı fonksiyon.
- `_FUZZY_NAME_MAX_DISTANCE = 2` sabiti eklendi.
- `search_files()` imzasına `fuzzy_name: str | None = None` ve
  `name_pattern: str | None = None` parametreleri eklendi.
- AC-7 (non-recursive kapsam): `fuzzy_name` veya `name_pattern`
  verildiğinde, recursive taramadan gelen dosya listesi
  `entry.parent == folder` ile SADECE kök dizine daraltılıyor.
- `name_pattern` verilirse `re.compile(name_pattern, re.IGNORECASE)`
  `search_files()` içinde `try/except re.error` ile derleniyor; geçersiz
  regex durumunda sessizce hiçbir dosya eşleşmiyor (erken/asıl validasyon
  main.py'de, AC-3).
- Filtre döngüsüne (content_contains'ten ÖNCE, name_contains/extension'ın
  hemen ardından) iki yeni filtre eklendi:
  - `fuzzy_name`: `entry.stem.lower()` (plan.md notu gereği `entry.name`
    DEĞİL) ile `fuzzy_name.lower()` arasındaki Levenshtein mesafesi
    `_FUZZY_NAME_MAX_DISTANCE` (2) üzerindeyse dosya elenir.
  - `name_pattern`: derlenmiş pattern `entry.name`'e `re.search` ile
    uygulanır, eşleşmezse (veya pattern geçersizse) dosya elenir.

### `backend/models.py`
- `SearchRequest`e `fuzzyName: str | None = None` ve
  `namePattern: str | None = None` alanları eklendi.

### `backend/main.py`
- `import re` eklendi.
- `search_endpoint()`'te modifiedAfter/modifiedBefore parse'ından sonra:
  - `payload.fuzzyName is not None and payload.namePattern is not None`
    ise 422 ("fuzzyName ve namePattern aynı anda kullanılamaz", AC-4).
  - `payload.namePattern is not None` ise `re.compile(...)` denenir,
    `re.error` yakalanırsa 422 ("namePattern geçersiz regex: '...'", AC-3).
  - `search_files()` çağrısına `fuzzy_name=payload.fuzzyName,
    name_pattern=payload.namePattern` eklendi.
- `/api/search/scan` (start_search_scan) ve `TestSearchFilesFuzzy*` dışı
  hiçbir davranışa dokunulmadı — kapsam tam olarak atdd.md AC-1,2,4,5,6,7'yi
  hedefliyor.

## Dokunulmayan dosyalar
- `backend/security.py` — talimat gereği dokunulmadı.
- Test dosyaları — dokunulmadı.

## Final pytest sonucu

```
.venv/Scripts/python.exe -m pytest backend/tests/ -v
...
367 passed, 4 skipped, 7 warnings in 21.59s
```

0 FAILED. 4 skip, hepsi Windows-only bilinen semboller (`os.symlink`
admin/dev-mode yetkisi ve `os.chmod` POSIX izin semantiği gerektiren
testler — `pytest.mark.skipif(os.name == "nt", ...)` ile zaten işaretli,
bu görevden bağımsız, önceden var olan davranış).

## Red-team follow-up düzeltmeleri (bağımsız red-team incelemesi, iki medium bulgu)

### `backend/file_search.py` — Bulgu 1 (performans)
- `search_files()` artık `fuzzy_name is not None or name_pattern is not None`
  durumunda `_iter_files_recursive()`'i HİÇ ÇAĞIRMIYOR. Bunun yerine
  doğrudan `folder.iterdir()` ile (gizli-dosya-atlama kuralı korunarak,
  sadece dosyalar) kök dizindeki dosyalar toplanıyor. Önceden TÜM alt ağaç
  derinlik 3'e kadar recursive gezilip sonra `entry.parent == folder` ile
  filtreleniyordu — bu, atdd.md'nin "non-recursive, sığ tarama" gerekçesine
  aykırı bir israftı. `fuzzy_name`/`name_pattern` verilmediğinde mevcut
  recursive davranış (Saga #336) AYNEN korunuyor.

### `backend/models.py` — Bulgu 2 (güvenlik / ReDoS mitigasyonu)
- `SearchRequest.fuzzyName`: `Field(default=None, max_length=100)` eklendi.
- `SearchRequest.namePattern`: `Field(default=None, max_length=200)` eklendi.
- `contentContains` ile aynı desen — üçüncü parti kütüphane gerektirmeyen
  ucuz bir ReDoS mitigasyonu (aşırı uzun/karmaşık pattern'leri Pydantic
  seviyesinde en baştan 422 ile reddetmek).

### Final doğrulama
```
.venv/Scripts/python.exe -m pytest backend/tests/ -v
...
367 passed, 4 skipped, 7 warnings in 22.11s
```
0 FAILED. Mevcut fuzzy/regex testleri (AC-7 dahil) yeni non-recursive
`iterdir()` implementasyonuyla da değişmeden geçti — davranış sözleşmesi
korundu, sadece gezinme maliyeti düştü. Temizlik kontrolü: `entry.parent ==
folder` deseni için tüm proje genelinde grep yapıldı, kod tarafında kalıntı
YOK (sadece açıklayıcı yorumda eski davranışa referans var, işlevsel değil).
