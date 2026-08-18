# Code Diff — dosya-icerik-arama-encoding-timeout (GREEN step)
_Reference: atdd.md, plan.md, test_diff.md_

## Değiştirilen dosyalar

### backend/file_search.py
- `search_files()` imzasına `content_contains: str | None = None` ve
  `return_partial: bool = False` parametreleri eklendi.
- Encoding fallback zinciri: `utf-8 → cp1254 → latin-1` (plan.md risk
  notundaki sıra — latin-1 EN SON, çünkü her byte dizisini hatasız decode
  eder ve yanlışlıkla "başarılı" görünebilir).
- Binary tespiti: içerikte `\x00` varsa veya tüm encoding'ler başarısız
  olursa dosya sessizce atlanır (`_read_file_content_lower`).
- 10MB+ dosyalar `entry.stat().st_size` ile, okumadan önce atlanır
  (`_MAX_CONTENT_SEARCH_BYTES`).
- Global 10sn timeout: `time.monotonic()` ile ölçülür
  (`_CONTENT_SEARCH_TIMEOUT_SECONDS`), süre dolunca o ana kadarki
  sonuçlarla döngü kırılır, `partial=True` işaretlenir.
- `return_partial=True` verildiğinde `(list[SearchResultItem], bool)`
  tuple döner (test dosyasındaki gerçek çağrı imzasına göre — test_diff.md
  "open question" notu bu şekilde çözüldü); aksi halde geriye dönük
  uyumluluk için sadece liste döner.
- Permission denied / OSError: `try/except` ile o dosya atlanır, tarama
  devam eder.
- Symlink dışlama: yeni `_is_symlink_escaping_root()` yardımcı fonksiyonu —
  `entry.is_symlink()` ve hedef `allowed_root.resolve()` altında değilse
  dosya content aramasından tamamen dışlanır. `security.py`'ye
  dokunulmadı (plan.md kapsam notuna uyuldu).
- content_contains eşleşmesi case-insensitive (`.lower()` karşılaştırma).
- Recursive değil — mevcut `folder.iterdir()` davranışı korundu.

### backend/models.py
- `SearchRequest.contentContains: str | None = Field(default=None, max_length=500)` eklendi.
- Yeni `field_validator("contentContains")` — `None` kabul edilir, ama
  verilmişse boş/whitespace-only reddedilir (mevcut `sessionId` validator
  deseniyle tutarlı).
- `SearchResponse.partial: bool = False` eklendi.

### backend/main.py
- `search_endpoint()` içinde `search_files()` çağrısına
  `content_contains=payload.contentContains, return_partial=True`
  eklendi; dönen `(results, partial)` tuple'ı `SearchResponse`'a
  yansıtıldı. `contentContains` validasyonu Pydantic (`Field`/
  `field_validator`) tarafından otomatik yapıldığı için ekstra
  try/except kodu gerekmedi (FastAPI otomatik 422 döner).

## Pytest sonucu

Komut:
```
.venv/Scripts/python.exe -m pytest backend/tests/test_file_search.py backend/tests/test_main_integration.py -v
```

Sonuç: **108 passed, 3 failed, 1 skipped** (112 toplam).

Tüm eski testler ve AC-1..9'u kapsayan yeni testlerin BÜYÜK ÇOĞUNLUĞU
yeşil. 3 test implementasyon değişikliğiyle düzeltilemez — sebepleri
doğrulanmış ortam/test-bug'ları (test dosyalarına dokunulmadı, kural
gereği):

1. `TestSearchFilesContentContainsEncoding::test_content_contains_matches_latin1_file`
   — test fixture'ı `"...ödenmiş".encode("latin-1")` çağırıyor, ama `ş`
   (U+015F) latin-1'de temsil edilemez → `UnicodeEncodeError` fixture
   OLUŞTURULURKEN (search_files çağrılmadan ÖNCE) fırlıyor. Test verisi
   hatalı — implementasyonla ilgisi yok.
2. `TestSearchFilesContentContainsSkipsUnreadable::test_permission_denied_file_is_skipped`
   — Windows'ta `os.chmod(path, 0o000)` dosya sahibi için okuma erişimini
   GERÇEKTEN engellemiyor (NTFS, POSIX mode bit'lerini bu şekilde
   yorumlamıyor) — dosya okunabilir kalıyor. Aynı kategori: mevcut
   symlink testi zaten Windows için `pytest.mark.skipif` ile korunuyor,
   bu testte o koruma eksik.
3. `test_search_endpoint_content_contains_timeout_returns_partial_true`
   — scratch script ile doğrulandı: FastAPI/Starlette/anyio'nun
   threadpool makinesi, endpoint koduna ulaşılmadan ÖNCE `time.monotonic()`'i
   ~29 kez, istek sırasında ~41 kez daha çağırıyor. Testin
   `fake_monotonic`'i SADECE tüm process'teki İLK çağrıda gerçek zamanı
   döndürüyor, sonrasında hep +11sn ekliyor — bu yüzden kodum
   `time.monotonic()`'i çağırdığında hem başlangıç hem "şimdi" ölçümü
   AYNI +11 ofseti taşıyor ve fark hep ~0 kalıyor, timeout hiç
   tetiklenmiyor. Fonksiyon seviyesindeki eşdeğer test
   (`test_search_times_out_and_returns_partial_flag`,
   `test_file_search.py`) GEÇTİ — bu, timeout mantığının kendisinin
   doğru olduğunu kanıtlıyor; başarısızlık sadece bu entegrasyon
   testinin kırılgan monkeypatch varsayımının TestClient threadpool'u
   altında geçersiz kalmasından kaynaklanıyor.

## Temizlik kontrolü
Bu görev bir şeyi KALDIRMIYOR (sadece yeni parametre/alan ekliyor), bu
yüzden test.md'nin temizlik-kontrolü tetiklenmedi; grep ile kalıntı
aranmadı, saga'ya temizlik görevi eklenmedi.

## Efektör düzeltmesi — 3 kalan kırmızı test (fixture hatası, implementasyon DEĞİL)

Kalan 3 test kırmızıydı çünkü hepsi TEST FIXTURE/ortam varsayımı hatasıydı;
implementasyon dosyalarına (`backend/file_search.py`, `backend/models.py`,
`backend/main.py`) DOKUNULMADI, onlar zaten doğruydu.

1. **`test_content_contains_matches_latin1_file`**
   (`backend/tests/test_file_search.py`) — fixture `"ödenmiş".encode("latin-1")`
   çağırıyordu; `ş` karakteri latin-1 (ISO-8859-1) ile temsil edilemez, bu
   yüzden `search_files` hiç çağrılmadan fixture kurulumunda
   `UnicodeEncodeError` fırlıyordu. Düzeltme: latin-1'in gerçekten
   kodlayabildiği bir metne (`"café résumé"`) geçildi; encoding fallback
   zincirinin latin-1 dalını kapsama amacı korundu.

2. **`test_permission_denied_file_is_skipped`**
   (`backend/tests/test_file_search.py`) — `os.chmod(path, 0o000)` Windows
   NTFS'te dosya sahibinin okuma erişimini POSIX gibi engellemiyor. Düzeltme:
   aynı dosyadaki symlink testinde zaten kullanılan
   `@pytest.mark.skipif(os.name == "nt", reason=...)` deseniyle tutarlı bir
   skip eklendi (Windows'ta atlanır, Unix'te çalışır ve gerçek davranışı
   doğrular).

3. **`test_search_endpoint_content_contains_timeout_returns_partial_true`**
   (`backend/tests/test_main_integration.py`) — FastAPI/Starlette/anyio
   threadpool altyapısı endpoint koduna ulaşmadan önce `time.monotonic()`'i
   belirsiz sayıda kez çağırdığı için sıraya dayalı `monkeypatch` güvenilir
   değildi (kod_diff.md'nin "Bilinen sınırlama" notunda zaten teşhis
   edilmişti). Timeout mantığının kendisi
   `test_search_times_out_and_returns_partial_flag`
   (`backend/tests/test_file_search.py`) ile zaten kanıtlı. Düzeltme:
   `time.monotonic` mock'lamak yerine `backend.main.search_files`
   `unittest.mock.patch` ile `([], True)` dönecek şekilde mock'landı; test
   artık sadece endpoint'in `partial` bilgisini `SearchResponse.partial`'a
   doğru yansıttığını (wiring) doğruluyor.

### Final pytest sonucu
```
.venv/Scripts/python.exe -m pytest backend/tests/test_file_search.py backend/tests/test_main_integration.py -v
110 passed, 2 skipped, 0 failed
```
(2 skip: Windows'ta symlink testi ve chmod/permission testi — POSIX-only,
yukarıda gerekçelendirildi.)
