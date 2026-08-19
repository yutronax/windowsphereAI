# Code Diff — dosya-arama-recursive

## Değişen dosya
`backend/file_search.py` (SADECE bu dosya değişti; `backend/security.py` ve
`backend/main.py`'ye dokunulmadı, test dosyası değiştirilmedi.)

## Ne değişti
- Yeni bağımsız sabit `_MAX_RECURSIVE_DEPTH = 3` eklendi — değeri
  `security.py::MAX_PATH_DEPTH` ile aynı ama bağımsız, yorum satırıyla bu
  bağlantı belgelendi (plan.md kararı).
- Yeni yardımcı fonksiyon `_iter_files_recursive(root)` eklendi
  (plan.md önerisi: gezinme mantığı ayrı fonksiyona çıkarıldı,
  `search_files()`'ın ana gövdesi şişirilmedi):
  - `root` altını derinlik `_MAX_RECURSIVE_DEPTH`'e kadar recursive gezer.
  - Gizli (nokta ile başlayan) klasörlerin ALTINA hiç inilmiyor, gizli
    dosyalar atlanıyor (AC-7).
  - Ziyaret edilen klasörlerin `resolve()` edilmiş path'leri bir `set`'te
    tutuluyor; tekrar görülen (gerçek veya sahte-monkeypatch'lenmiş)
    döngüsel bir klasöre ikinci kez girilmiyor (AC-3).
  - `_is_symlink_escaping_root()` (Saga #314'ten, değiştirilmedi) her
    seviyede tekrar uygulanıyor — `allowed_root` dışına işaret eden
    symlink'ler recursive bağlamda da dışlanıyor (AC-6).
- `search_files()` içinde `folder.iterdir()` ile sınırlı doğrudan-alt
  toplama mantığı `list(_iter_files_recursive(folder))` ile değiştirildi.
  `content_contains`, timeout, encoding mantığı DEĞİŞMEDİ.

## Bulunan ve düzeltilen bug (implementasyon sırasında)
İlk yazımda `_walk` içindeki recursive çağrı `yield from` olmadan
(`_walk(entry, depth + 1)` şeklinde, sonucu atarak) yapılmıştı — generator
hiç tüketilmiyordu, bu yüzden TÜM recursive testler boş sonuç
döndürüyordu. `yield from _walk(entry, depth + 1)` olarak düzeltildi.

## Final pytest sonucu
```
.venv/Scripts/python.exe -m pytest backend/tests/test_file_search.py backend/tests/test_main_integration.py -v
...
FAILED backend/tests/test_file_search.py::TestSearchFilesContentContainsRecursive::test_content_search_finds_match_in_nested_folder
============ 1 failed, 119 passed, 4 skipped, 5 warnings in 4.08s =============
```

## Tam yeşil olamayan tek test — açık soru
`TestSearchFilesContentContainsRecursive::test_content_search_finds_match_in_nested_folder`
ile `TestSearchFilesDepthLimit::test_file_beyond_max_depth_is_excluded_without_error`
fixture'ları YAPISAL OLARAK BİREBİR AYNI derinlikte
(`root/a/b/c/dosya` — 3 iç içe klasör + dosya == `root/2024/Q1/Ocak/fatura.txt`
— 3 iç içe klasör + dosya) ama BEKLENEN SONUÇLARI TERS:
- Depth-limit testi (Critical, AC-2): bu derinlikteki dosyanın SONUÇTA
  GÖRÜNMEMESİNİ bekliyor (derinlik sınırı aşıldı).
- Content-recursive testi (High, AC-4, "AC-1 ile aynı derinlik kurallarına
  tabi" notuyla): AYNI derinlikteki dosyanın SONUÇTA GÖRÜNMESİNİ bekliyor.

Aynı derinlik formülüyle ikisi birden matematiksel olarak sağlanamaz —
implementasyon Critical öncelikli AC-2'yi (ve onunla tutarlı diğer tüm
derinlik/döngü testlerini) doğru uyguluyor, tek çelişen test bu. Muhtemelen
önceki (Ara Nöron/red-step) subagent content-recursive fixture'ını 2 seviyeli
(`a/b` gibi diğer AC-1 örnekleri) kurgulamak isterken yanlışlıkla 3 seviyeli
(`2024/Q1/Ocak`) yazmış bir fixture hatası. Test dosyasına dokunma kuralı
gereği bu düzeltilmedi — kullanıcı kararı gerekiyor: (a) test fixture'ı bir
seviye sığlaştırılsın mı, yoksa (b) `_MAX_RECURSIVE_DEPTH` 4 mü olmalı (bu

## Çözüm (efektör turu)

Kullanıcı kararı: (a) — test fixture'ı sığlaştırıldı, implementasyona
(`backend/file_search.py`, `_MAX_RECURSIVE_DEPTH = 3`) dokunulmadı.

`backend/tests/test_file_search.py::TestSearchFilesContentContainsRecursive::
test_content_search_finds_match_in_nested_folder` fixture'ı `tmp_path/2024/Q1/
Ocak/fatura.txt` (derinlik 4, AC-2/`MAX_PATH_DEPTH=3` ile çelişiyordu) →
`tmp_path/2024/Ocak/fatura.txt` (derinlik 3, sınıra tam uyar) olarak değiştirildi.
Testin amacı (content_contains'in nested klasörde çalıştığını doğrulamak)
korunuyor, sadece derinlik AC-2 ile artık tutarlı.

Doğrulama: `.venv/Scripts/python.exe -m pytest backend/tests/test_file_search.py
backend/tests/test_main_integration.py -v` → **120 passed, 4 skipped
(Windows'ta symlink admin-yetki gerektiren testler), 0 failed.**

Temizlik kontrolü: `Q1` deseni proje genelinde grep'lendi, kalıntı yok (tek
kalan `Q1` referansı ayrı ve ilgisiz bir testte / bu notun kendi metninde).
Saga'ya ek temizlik görevi açılmadı.
durumda AC-2/depth-limit testi kırılır, dolayısıyla bu seçenek önerilmez).

## Red-team follow-up düzeltmesi (efektör turu, medium bulgu)

Bağımsız red-team incelemesi (`red_team.json`) `_iter_files_recursive()`'in
(gezinme adımının) hiçbir zaman bütçesi olmadan çalıştığını, 10sn timeout'un
SADECE `search_files()`'ın `content_contains` döngüsünde kontrol edildiğini
buldu — yani `content_contains` VERİLMEDEN yapılan bir arama (sadece
`name_contains`/`extension`/`modified_after`/`modified_before`), büyük/yavaş
bir dizin ağacında `partial` fallback'i olmadan asılı kalabiliyordu.

Değişiklikler (`backend/file_search.py`):
- `_iter_files_recursive(root, timed_out=None)`: artık opsiyonel bir
  `timed_out` (mutable `list[bool]`) parametresi alıyor. Fonksiyon kendi
  `time.monotonic()` başlangıç zamanını tutuyor; her dizine inmeden ÖNCE
  (hem `_walk` girişinde hem her entry döngüsünde) geçen süre
  `_CONTENT_SEARCH_TIMEOUT_SECONDS` (10sn) ile karşılaştırılıyor. Aşılırsa
  gezinme o ana kadar keşfedilen dosyalarla durur ve `timed_out[0] = True`
  set edilir.
- `search_files()`: `discovery_timed_out = [False]` mutable sinyali
  oluşturup `_iter_files_recursive(folder, timed_out=discovery_timed_out)`
  şeklinde geçiyor. `partial` artık `discovery_timed_out[0]` ile
  başlıyor (yani discovery timeout'a uğradıysa `partial=True` zaten
  set edilmiş oluyor), `content_contains` döngüsündeki mevcut
  timeout mantığı (content-timeout) buna EK olarak `partial=True`
  yapmaya devam ediyor — ikisinden biri gerçekleşirse `partial=True`.

Yeni test (`backend/tests/test_file_search.py`):
`TestSearchFilesDiscoveryTimeoutWithoutContentContains::
test_discovery_times_out_without_content_contains_and_returns_partial` —
mevcut `TestSearchFilesRecursiveTimeout` ile AYNI `time.monotonic()`
monkeypatch desenini kullanıyor, ama `content_contains` VERMEDEN
(`name_contains="file"` ile) çağırıyor ve `partial is True` olduğunu
doğruluyor.

Temizlik kontrolü: bu bir kaldırma/silme değişikliği değil, geriye dönük
uyumlu (opsiyonel parametre) bir ekleme — proje genelinde kalıntı arama
gerektirmiyor. `_iter_files_recursive` ve `discovery_timed_out`
referansları grep'lendi, sadece `backend/file_search.py` içinde (ve
derlenmiş `.pyc` içinde) bulundu, kalıntı yok.

Final pytest sonucu:
```
.venv/Scripts/python.exe -m pytest backend/tests/ -v
...
================= 350 passed, 4 skipped, 5 warnings in 21.78s =================
```
0 failed, tam yeşil.

Saga görev kaydı: `mcp__saga__task_create` bu oturumda erişilebilir
değildi; görev kaydı `artifacts/dosya-arama-recursive/
saga_task_336_follow_up.md` dosyasına düşüldü (projenin kendi
mekanizması).
