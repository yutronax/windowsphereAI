# Test Diff — dosya-icerik-arama-encoding-timeout (RED step)

_Reference: atdd.md, plan.md_

## Ne yapıldı
İki mevcut test dosyasına yeni test sınıfları/fonksiyonları EKLENDİ. Hiçbir
implementasyon dosyası (`backend/file_search.py`, `backend/models.py`,
`backend/main.py`) değiştirilmedi. Testler `content_contains` parametresi ve
`contentContains`/`partial` alanları henüz mevcut olmadığı için KIRMIZI —
bu beklenen ve doğru red-step davranışı.

## backend/tests/test_file_search.py — eklenen sınıflar

| Sınıf | Test(ler) | Kapsadığı AC |
|---|---|---|
| `TestSearchFilesContentContainsEncoding` | utf-8/latin-1/cp1254 tekil eşleşme, üç encoding birlikte, eşleşme yok → `[]`, case-insensitive eşleşme | AC-1, Davranış tablosu satır 8 |
| `TestSearchFilesContentContainsSkipsUnreadable` | binary (.exe) dosya atlanır, 10MB+ dosya atlanır, permission-denied dosya atlanır | AC-3, AC-5 |
| `TestSearchFilesContentContainsTimeout` | `time.monotonic` monkeypatch ile 10sn timeout tetiklenir, `return_partial=True` ile `(sonuçlar, partial)` tuple beklenir | AC-2 |
| `TestSearchFilesContentContainsAndOtherFilters` | `content_contains` + `name_contains` + `extension` AND mantığı | AC-6 |
| `TestSearchFilesContentContainsNonRecursive` | alt klasördeki eşleşen dosya sonuca girmez | AC-7 |
| `TestSearchFilesContentContainsSymlinkEscape` | `allowed_root` dışına işaret eden symlink taranmaz (Windows'ta `pytest.mark.skipif` ile atlanır — `os.symlink` admin/developer-mode gerektirir) | AC-8 |

## backend/tests/test_main_integration.py — eklenen fonksiyonlar

| Test | Kapsadığı AC |
|---|---|
| `test_search_endpoint_content_contains_matches_utf8_and_latin1_and_cp1254` | AC-1 |
| `test_search_endpoint_content_contains_returns_422_for_empty_string` | AC-4 |
| `test_search_endpoint_content_contains_returns_422_for_whitespace_only` | AC-4 |
| `test_search_endpoint_content_contains_returns_422_when_over_500_chars` | AC-9 |
| `test_search_endpoint_content_contains_combines_with_other_filters` | AC-6 |
| `test_search_endpoint_content_contains_binary_and_large_files_are_skipped` | AC-3 |
| `test_search_endpoint_content_contains_no_match_returns_empty_results` | Davranış tablosu satır 8 (AC-1 negatif) |
| `test_search_endpoint_content_contains_timeout_returns_partial_true` | AC-2, Davranış tablosu satır 6/7 |

## Pytest çalıştırma sonucu

Komut:
```
.venv/Scripts/python.exe -m pytest backend/tests/test_file_search.py backend/tests/test_main_integration.py -k "content or Content or symlink or Symlink or partial or Partial" -v
```

Sonuç: **18 failed, 2 passed, 1 skipped, 91 deselected** (toplam 21 seçilen testten).

- 18 test, beklenen şekilde **kırmızı**: `TypeError: search_files() got an unexpected keyword argument 'content_contains'` (file_search.py testleri) veya assertion/`KeyError: 'partial'` hataları (main_integration.py testleri — `contentContains` şu an Pydantic tarafından sessizce yok sayılıyor, filtre uygulanmadığı için beklenen 422/boş-sonuç/partial davranışları gerçekleşmiyor).
- 2 test **geçti** ama bu YANILTICI DEĞİL, beklenen bir yan etki: `test_content_contains_all_three_encodings_together`'ın entegrasyon eşdeğeri ve encoding eşleşme testi, `contentContains` alanı şu an hiçbir filtre uygulamadığı (extra alan yok sayılıyor) için klasördeki TÜM dosyalar zaten döndüğünden tesadüfen assertion'ı sağlıyor — bu, `content_contains` implemente edildiğinde davranışın gerçekten doğrulanmasını sağlayan ayrı, daha kesin testlerle (`TestSearchFilesContentContainsEncoding` sınıfındaki `search_files()` seviyesi testler) zaten kapatılmış durumda (onlar TypeError ile kırmızı).
- 1 test **skip** edildi: `test_symlink_pointing_outside_allowed_root_is_not_searched` — Windows'ta `os.symlink()` admin/developer-mode yetkisi gerektirdiği için `pytest.mark.skipif(os.name == "nt", ...)` ile atlandı. Test kodu yazıldı, Unix ortamında çalışacak.
- Hiçbir test **import/collection hatası** vermedi — tüm kırmızılar gerçek assertion/TypeError/KeyError seviyesinde, bu red step için doğru.

## Kapsanmayan / not
- `content_contains`'in dönüş tipi konusunda bir varsayım yapıldı: timeout senaryosunda `search_files(..., return_partial=True)` çağrıldığında `(list, bool)` tuple döneceği varsayıldı (mevcut imzada `partial` sinyali için ne bir parametre ne dönüş tipi var). Bu, code-copilot'un plan.md'deki timeout riskini nasıl çözdüğüne göre `green` adımında ayarlanması gerekebilir — bu bir `open_question` değil, red-step'te test yazarken yapılması gereken bir tasarım varsayımıdır ve plan.md'de netleştirilmemiş.
