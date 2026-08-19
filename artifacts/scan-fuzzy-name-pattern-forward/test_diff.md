# test_diff.md — scan-fuzzy-name-pattern-forward (RED STEP)

## Değiştirilen dosya
`backend/tests/test_search_scan.py` — mevcut 10 test AYNEN korundu, sona 4 yeni test eklendi. `backend/main.py` DEĞİŞTİRİLMEDİ (bu adım sadece red step).

## Eklenen testler

| Test | AC | Kapsam |
|---|---|---|
| `test_scan_with_fuzzy_name_finds_typo_matched_file_after_completion` | AC-1 [Critical] | `fuzzyName="fatuura"` ile `/api/search/scan` başlatılır, `fatura.pdf` (Levenshtein mesafesi=1) + alakasız `alakasiz.txt` fixture'ı oluşturulur. Tarama `done` olana kadar poll edilir (mevcut testlerdeki desen). `fatura.pdf` sonuçta bulunmalı VE `alakasiz.txt` bulunMAmalı (filtrenin gerçekten uygulandığını ayırt etmek için — aksi halde `_run_scan`'in filtresiz tüm dosyaları döndürmesi testi yanlışlıkla yeşil geçirir). |
| `test_scan_with_name_pattern_finds_regex_matched_file_after_completion` | AC-2 [Critical] | `namePattern="fat.*"` ile aynı desen — `fatura.pdf` bulunmalı, `alakasiz.txt` bulunMAmalı. |
| `test_scan_start_returns_422_for_invalid_name_pattern_regex_same_as_sync_search` | AC-3 [High] | `namePattern="("` (bozuk regex) ile `/api/search/scan` çağrısı — `test_main_integration.py::test_search_endpoint_returns_422_for_invalid_name_pattern_regex`'in `/api/search/scan` karşılığı. 422 bekleniyor. |
| `test_scan_start_returns_422_when_fuzzy_name_and_name_pattern_together` | AC-4 [High] | `fuzzyName` VE `namePattern` aynı istekte — `/api/search`'teki AC-4 testinin `/api/search/scan` karşılığı. 422 bekleniyor. |

Ayrıca yardımcı fonksiyon eklendi: `_wait_for_scan_done(scan_id, deadline_seconds=2.0)` — mevcut testlerdeki polling deseninin (deadline + `time.sleep(0.02)`) tekrar kullanılabilir hale getirilmiş hali, kod tekrarını azaltmak için.

## Pytest sonucu (gerçek çalıştırma)

```
.venv/Scripts/python.exe -m pytest backend/tests/test_search_scan.py -v
```

**4 failed, 10 passed, 1 warning in 1.24s**

Mevcut 10 test (Saga #337 kapsamı) değişmeden PASSED kaldı:
- test_scan_start_returns_202_and_scan_id_before_search_files_completes
- test_scan_status_is_running_immediately_after_start
- test_scan_status_is_done_with_results_after_search_files_completes
- test_scan_status_returns_404_not_found_for_unknown_scan_id
- test_two_scans_get_independent_scan_ids_and_can_both_be_queried
- test_scan_start_returns_404_for_unknown_session_id_same_as_sync_search
- test_scan_start_returns_410_when_selected_folder_no_longer_exists_same_as_sync_search
- test_scan_status_returns_not_found_for_an_expired_record
- test_scan_status_is_done_not_stuck_running_when_search_files_raises
- test_scan_ids_are_uuid_formatted_not_sequential

Yeni eklenen 4 test **assertion seviyesinde** KIRMIZI (beklenen RED step davranışı):

1. `test_scan_with_fuzzy_name_finds_typo_matched_file_after_completion` — FAILED:
   `AssertionError: fuzzyName filtre olarak uygulanmamis, alakasiz.txt de sonuclarda (results=['alakasiz.txt', 'fatura.pdf'])`
   — `_run_scan`'in `fuzzy_name`'i `search_files()`'a hiç forward etmediğini kanıtlıyor (tüm dosyalar filtresiz dönüyor).

2. `test_scan_with_name_pattern_finds_regex_matched_file_after_completion` — FAILED:
   `AssertionError: namePattern filtre olarak uygulanmamis, alakasiz.txt de sonuclarda (results=['alakasiz.txt', 'fatura.pdf'])`
   — aynı sebep, `name_pattern` forward edilmiyor.

3. `test_scan_start_returns_422_for_invalid_name_pattern_regex_same_as_sync_search` — FAILED:
   `assert 202 == 422` — `start_search_scan`'de bozuk regex validasyonu yok, tarama sessizce başlatılıyor.

4. `test_scan_start_returns_422_when_fuzzy_name_and_name_pattern_together` — FAILED:
   `assert 202 == 422` — `start_search_scan`'de çelişen mod (`fuzzyName`+`namePattern`) validasyonu yok.

## Not — ilk deneme tuzağı
AC-1/AC-2 testleri ilk yazımda **yanlışlıkla YEŞİL geçti**: `_run_scan` filtreleri hiç uygulamadığı için TÜM dosyalar (hem `fatura.pdf` hem alakasız `alakasiz.txt`) sonuçta dönüyordu, "fatura.pdf sonuçta var mı" tek başına yeterli bir assertion değildi — yanlış-pozitif üretiyordu. Testler, filtrelenmemiş dosyanın (`alakasiz.txt`) sonuçta OLMAMASI gerektiğini de kontrol edecek şekilde güçlendirildi; bu ikinci assertion olmadan red step'in gerçek nedeni (forward eksikliği) yakalanamıyordu.

## Referans
- `artifacts/scan-fuzzy-name-pattern-forward/atdd.md` (AC-1..4, Davranış Sözleşmesi tablosu)
- `artifacts/scan-fuzzy-name-pattern-forward/plan.md`
- `backend/tests/test_main_integration.py` satır 1402-1429 (senkron `/api/search` için aynı AC-3/AC-4 testlerinin orijinali, buradan pattern alındı)
