# Plan — dosya-arama-ilerleme-gostergesi
_Reference: atdd.md_

## Files to Modify
| File | Why | Risk |
|------|-----|------|
| backend/main.py | `POST /api/search/scan`, `GET /api/search/scan/{scan_id}` yeni endpoint'ler + bellek-içi `_scans` dict + `threading.Lock` + arka plan thread başlatma mantığı eklenir | high |
| backend/models.py | `ScanStartResponse` (scanId), `ScanStatusResponse` (status, scannedCount, results, partial) yeni Pydantic şemaları eklenir | low |

## New Files
Yok.

## Dependencies
- `backend/file_search.py::search_files()` — DOKUNULMAZ, arka plan thread'inden `return_partial=True` ile çağrılır (mevcut `/api/search` endpoint'iyle aynı çağrı şekli).
- `uuid` modülü zaten `backend/main.py`'de import edilmiş (satır 4, `uuid.uuid4()` başka bir yerde kullanılıyor) — `scan_id` üretimi için AYNI import kullanılır, threat-model AC-S1 (tahmin edilemez id) bunu doğrudan karşılar.
- **Arka plan çalıştırma mekanizması kararı (atdd.md Unknowns'ı burada çözüldü):** `backend/main.py`'deki TÜM endpoint'ler `def` (senkron) — FastAPI bunları otomatik olarak bir threadpool'da çalıştırıyor (async değil). Bu nedenle scan işini `threading.Thread(target=_run_scan, args=(...), daemon=True).start()` ile ayrı bir thread'de başlatmak, mevcut FastAPI çalışma modeliyle tutarlı ve event loop'u BLOKE ETMEZ (zaten sync endpoint'ler kendi threadpool'unda çalışıyor, ek bir thread bunun üstüne minimal maliyetle biner).
- **Thread-safety:** `_scans: dict[str, ScanState]` mevcut `_sessions` dict'iyle AYNI seviyede bir modül-düzeyi state, ama `_sessions`'ın aksine BİRDEN FAZLA thread (ana istek thread'i + arka plan scan thread'i) eşzamanlı okur/yazar — bu yüzden `_sessions`'dan farklı olarak `_scans` erişimi bir `threading.Lock()` ile korunmalı (atdd.md Risks'te işaretlenen boşluk, burada netleştirildi).
- Testler mevcut `backend/tests/test_main_integration.py`'ye eklenir.

## Migration Required?
Hayır.

## Risks
- (atdd.md'den taşındı, burada çözüldü) Arka plan mekanizması: `threading.Thread` + `threading.Lock`. Alternatif (`asyncio.to_thread`) burada kullanılmadı çünkü endpoint'ler zaten `async def` değil — `threading.Thread` mevcut kod tabanının senkron doğasıyla daha tutarlı.
- 5 dakikalık temizlik: Ayrı bir zamanlanmış görev (cron/scheduler) YERİNE, her yeni `GET /api/search/scan/{scan_id}` çağrısında "lazy cleanup" (süresi dolmuş kayıtları o an sil) yaklaşımı önerilir — ekstra bir background scheduler/thread'e gerek kalmaz, mevcut kod tabanında böyle bir altyapı zaten yok. code-copilot'a NOT: `_scans` dict'ine her erişimde (okuma/yazma öncesi) süresi dolmuş kayıtları temizleyen küçük bir yardımcı çağrılabilir.
- Test edilmesi zor bir alan: AC-1 (10ms altı yanıt) gerçek zamanlama testi kırılgan olabilir — test-copilot'a NOT: gerçek süre yerine "yanıt döndüğünde `search_files()` henüz TAMAMLANMAMIŞ olmalı" (örn. `search_files`'ı yavaşlatan bir mock ile, yanıtın mock tamamlanmadan geldiğini doğrulayan) bir test tercih edilmeli, ham milisaniye ölçümü değil.

## Open Questions
Yok — atdd.md'nin Unknowns'ı (arka plan mekanizması) bu plan turunda koda bakılarak çözüldü.
