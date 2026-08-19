# Test Diff — dosya-arama-ilerleme-gostergesi (RED STEP)

_Reference: atdd.md, plan.md_

## Eklenen Dosya
`backend/tests/test_search_scan.py` (yeni — mevcut `test_main_integration.py`'ye
karıştırılmadı, arama-scan'e özel testler ayrı tutuldu).

Henüz implementasyon YOK (`POST /api/search/scan`, `GET /api/search/scan/{scan_id}`
route'ları `backend/main.py`'de tanımlı değil) — bu bilinçli olarak RED step,
implementasyon adımı `code-copilot`'a devredilecek.

## Kapsanan AC'ler ve Testler

| AC | Test | Strateji |
|---|---|---|
| AC-1 [Critical] | `test_scan_start_returns_202_and_scan_id_before_search_files_completes` | `search_files`'ı `time.sleep(0.3)` ile yavaşlatan mock; yanıt 202 + dolu `scanId` döner mü (plan.md'nin önerdiği "henüz tamamlanmamış" stratejisi, ham ms ölçümü değil) |
| AC-2 [Critical] | `test_scan_status_is_running_immediately_after_start` | Aynı yavaş mock içinde, `search_files` daha bitmeden `GET` çağrılır, `status: "running"` beklenir |
| AC-3 [Critical] | `test_scan_status_is_done_with_results_after_search_files_completes` | Anında dönen mock + kısa polling döngüsü (thread join yerine, 2sn deadline) ile senkronize edilip `status: "done"` + `results` listesi doğrulanır |
| AC-4 [High] | `test_scan_status_returns_404_not_found_for_unknown_scan_id` | Rastgele `uuid4()` ile `GET` → 404 + `{"status": "not_found"}` |
| AC-5 [High] | `test_two_scans_get_independent_scan_ids_and_can_both_be_queried` | İki ardışık `POST` → farklı `scanId`, ikisi de bağımsız `GET` ile sorgulanabilir |
| AC-6 [High] | `test_scan_start_returns_404_for_unknown_session_id_same_as_sync_search` + `test_scan_start_returns_410_when_selected_folder_no_longer_exists_same_as_sync_search` | Mevcut `/api/search` üzerindeki `test_search_endpoint_returns_404_for_unknown_session_id` / `...returns_410_when_selected_folder_no_longer_exists` testlerinin `/api/search/scan` için birebir tekrarı |
| AC-7 [Medium] | `test_scan_status_returns_not_found_for_an_expired_record` | Gerçek 5dk beklemeden, `backend.main._scans` dict'ine doğrudan erişip bir kaydın `completed_at`'ini geçmişe çekerek lazy-cleanup simüle edilir (plan.md önerisi) |
| AC-S1 [High] | `test_scan_ids_are_uuid_formatted_not_sequential` | İki `scanId`'nin `uuid4` regex'ine uyduğu, "1"/"2" gibi sıralı OLMADIĞI doğrulanır |

## Pytest Sonucu

```
.venv/Scripts/python.exe -m pytest backend/tests/test_search_scan.py -v
...
8 failed, 1 passed, 1 warning in 1.90s
```

- 8 test **beklenen şekilde KIRMIZI**: route (`/api/search/scan`, `/api/search/scan/{scan_id}`)
  henüz mevcut olmadığı için FastAPI eşleşmeyen path'e 404 dönüyor, ama gövdede
  `scanId`/`status` alanları YOK — testler `KeyError` (`response.json()["scanId"]` /
  `["status"]`) veya yanlış status code (`test_..._410_..._same_as_sync_search` → 404 != 410)
  ile assertion seviyesinde kırmızı. `test_scan_status_returns_not_found_for_an_expired_record`
  de aynı sebeple (`scanId` alınamadığı için) `KeyError` ile kırmızı — henüz
  `backend.main._scans`'e erişemeden başarısız oluyor (o kontrol implementasyon
  sonrası devreye girecek).
- 1 test **beklenen şekilde YEŞİL**: `test_scan_start_returns_404_for_unknown_session_id_same_as_sync_search`
  — eşleşmeyen route zaten 404 döndürdüğü için bu, mevcut `/api/search`'ün
  404 sözleşmesiyle tesadüfen aynı sonucu veriyor; bu davranış implementasyon
  sonrasında da (gerçek session-not-found kontrolüyle) geçerli kalacağından
  test bilinçli olarak dokunulmadan bırakıldı.

## Sonraki Adım
`code-copilot`: `backend/main.py`'ye `POST /api/search/scan` + `GET /api/search/scan/{scan_id}`
ve `backend/models.py`'ye `ScanStartResponse`/`ScanStatusResponse` eklenmesi
(plan.md: `threading.Thread` + `threading.Lock` + lazy cleanup ile).
