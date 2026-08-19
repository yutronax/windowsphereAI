# Code Diff — dosya-arama-ilerleme-gostergesi (GREEN step)

_Reference: atdd.md, plan.md, test_diff.md_

## Değişen Dosyalar

### backend/models.py
- `Literal` importu eklendi.
- `ScanStartResponse(BaseModel)`: `scanId: str`.
- `ScanStatusResponse(BaseModel)`: `status: Literal["running","done","not_found"]`,
  `scannedCount: int`, `results: list[SearchResultItem] | None = None`,
  `partial: bool | None = None`.

### backend/main.py
- Importlar: `dataclasses`, `threading`, `time` eklendi; `ScanStartResponse`,
  `ScanStatusResponse` ve `Response` (fastapi) eklendi.
- `ScanState` dataclass'ı: `status`, `scanned_count`, `results`, `partial`,
  `completed_at` alanları — test dosyası (`test_search_scan.py` AC-7)
  `main_module._scans[scan_id].completed_at` şeklinde ATTRIBUTE erişimi
  beklediği için `_scans` değerleri düz dict DEĞİL, bu dataclass.
- Modül seviyesi state: `_scans: dict[str, ScanState] = {}`,
  `_scans_lock = threading.Lock()` (`_sessions`'ın yanına eklendi).
- `_SCAN_TTL_SECONDS = 300` + `_cleanup_expired_scans()` yardımcı fonksiyonu
  (lazy cleanup, plan.md önerisi — caller `_scans_lock`'u zaten tutuyor
  olmalı).
- `_run_scan(scan_id, allowed_root, ...)`: arka plan thread'inde
  `search_files(..., return_partial=True)` çağırır, sonucu `_scans_lock`
  altında `ScanState`'e yazar (`status="done"`).
- `POST /api/search/scan` (202 Accepted, `ScanStartResponse`): mevcut
  `get_session_for_search` dependency'sini kullanır (AC-6: 404/410 mevcut
  `/api/search` ile birebir aynı davranış). `uuid.uuid4()` ile `scan_id`
  üretir (AC-S1), `_scans[scan_id] = ScanState(status="running")` kaydeder,
  `threading.Thread(target=_run_scan, ..., daemon=True).start()` ile
  arka plana atar ve `search_files`'ı BEKLEMEDEN hemen döner (AC-1).
- `GET /api/search/scan/{scan_id}` (`ScanStatusResponse`): erişim öncesi
  `_cleanup_expired_scans()` çalıştırır (AC-7). Bilinmeyen/süresi dolmuş
  `scan_id` için `response.status_code = 404` + gövde
  `{"status": "not_found", "scannedCount": 0}` döner — standart
  `HTTPException` `{"detail": ...}` ürettiği için (test `["status"]`
  beklediğinden) bilinçli olarak `Response` nesnesi üzerinden manuel status
  code ayarlanıp `ScanStatusResponse` doğrudan döndürüldü (AC-4).
  Bulunan kayıt için `status`/`scannedCount`/`results`/`partial` aynen
  döner (AC-2, AC-3, AC-5).
- Mevcut `POST /api/search` endpoint'ine (satır ~383-434) DOKUNULMADI.
- `backend/file_search.py`'ye DOKUNULMADI.

## Test Sonucu (final)

```
.venv/Scripts/python.exe -m pytest backend/tests/test_search_scan.py backend/tests/test_main_integration.py backend/tests/test_file_search.py -v
...
================= 130 passed, 4 skipped, 5 warnings in 4.07s ==================
```

4 skip Windows-only testler (symlink/permission-denied senaryoları,
`test_file_search.py` içinde önceden de skip ediliyordu — bu task'la
ilgisiz).

Flaky kontrolü: `test_search_scan.py` art arda 3 kez ayrı ayrı çalıştırıldı,
üçünde de `9 passed` (thread-timing kaynaklı bir kararsızlık gözlenmedi).

## Temizlik Kontrolü (test.md)
Bu görev bir şeyi KALDIRMIYOR, sadece yeni iki endpoint + iki yeni model
ekliyor — mevcut hiçbir kod/route/import silinmedi. Bu yüzden proje geneli
kalıntı taraması bu görev kapsamında gerekmedi.

## Red-Team Düzeltmesi (medium severity, red_team.json)

**Bulgu:** `_run_scan()` içinde `search_files()` çağrısı `try/except`
olmadan yapılıyordu. Beklenmedik bir exception (ör. `OSError`) fırlarsa
arka plan thread'i sessizce ölüyor, `ScanState.status` sonsuza kadar
`"running"` kalıyordu — atdd.md'nin "asla running'de takılı kalmaz"
garantisini ihlal ediyor ve `_cleanup_expired_scans()` sadece
`status=="done"` kayıtları hedeflediği için TTL temizliği bu kayıtları
hiç görmüyordu (kalıcı bellek sızıntısı).

**Düzeltme (backend/main.py, `_run_scan()`):** `search_files()` çağrısı
`try/except Exception` ile sarıldı. Hata olursa:
- `logger.exception(...)` ile hata loglanıyor (sessizce yutulmuyor).
- `_scans_lock` altında `ScanState` `status="done"`, `partial=True`,
  `results=[]`, `completed_at=time.monotonic()` olarak işaretleniyor —
  böylece client polling'i sonsuza kadar "running" görmüyor, TTL temizliği
  de bu kaydı normal şekilde süpürebiliyor.

**Yeni test (backend/tests/test_search_scan.py):**
`test_scan_status_is_done_not_stuck_running_when_search_files_raises` —
`search_files`'ı `OSError` fırlatacak şekilde mock'layıp, scan
başlatıldıktan sonra `GET /api/search/scan/{scan_id}`'in kısa bir polling
döngüsüyle `status: "running"` yerine `status: "done"` döndüğünü doğruluyor.

**Final pytest sonucu (tüm backend/tests/):**
```
.venv/Scripts/python.exe -m pytest backend/tests/ -v
...
================= 360 passed, 4 skipped, 5 warnings in 21.39s =================
```
Mevcut hiçbir test bozulmadı, 0 FAILED. Temizlik taraması gerekmedi (bu
düzeltme de bir şey kaldırmıyor, sadece hata-yolu ekliyor).
