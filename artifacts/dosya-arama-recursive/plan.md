# Plan — dosya-arama-recursive
_Reference: atdd.md_

## Files to Modify
| File | Why | Risk |
|------|-----|------|
| backend/file_search.py | `search_files()`'ın `folder.iterdir()` ile sınırlı toplama mantığı, recursive bir gezinmeye dönüştürülür: derinlik sayacı (limit=3, `security.py::MAX_PATH_DEPTH` ile aynı değer ama bağımsız sabit), ziyaret edilen resolved-path seti (döngü koruması), gizli klasörlerin altına hiç inilmemesi, mevcut allowed_root-dışı symlink dışlamasının (AC-8, #314) her seviyede uygulanması (AC-1..7) | high |

## New Files
Yok.

## Dependencies
- `backend/security.py::MAX_PATH_DEPTH = 3` — DEĞER referans alınır ama `security.py`'ye dokunulmaz (plan kararı: bağımsız bir sabit, `file_search.py` içinde tanımlanıp yorumla `security.py::MAX_PATH_DEPTH`'e bağlandığı belirtilir — atdd.md Risks'te işaretlendiği gibi, iki sabit gelecekte birbirinden sapabilir, bu bilinçli bir trade-off).
- `_is_symlink_escaping_root()` (Saga #314'te eklenen mevcut yardımcı fonksiyon) — recursive gezinme sırasında HER seviyede tekrar kullanılır, değiştirilmez.
- `_read_file_content_lower()`, `_CONTENT_ENCODINGS`, timeout mantığı (Saga #314) — recursive bağlamda aynen kullanılmaya devam eder, `content_contains` akışı değişmez, sadece dosya KEŞFETME mantığı (hangi dosyaların taranacağı) recursive olur.
- Testler mevcut `backend/tests/test_file_search.py` ve `backend/tests/test_main_integration.py` dosyalarına eklenir.

## Migration Required?
Hayır.

## Risks
- (atdd.md'den taşındı) Derinlik sabiti `security.py::MAX_PATH_DEPTH` ile aynı DEĞERDE ama ayrı bir tanım — biri değişip diğeri değişmezse tutarsızlık oluşur. Yorum satırıyla bağlantı belgelenecek ama otomatik senkron yok.
- Recursive gezinme mevcut `search_files()`'ın DÜZ (`iterdir()` sonra `sorted()`) yapısını değiştiriyor — bu fonksiyon zaten Saga #314 ile içerik arama/timeout/encoding mantığını taşıyordu, recursive'e geçiş fonksiyonun karmaşıklığını daha da artırıyor. code-copilot'a NOT: gezinme mantığını (`_walk_recursive` gibi) ayrı bir yardımcı fonksiyona çıkarmak, `search_files()`'ın ana gövdesini okunur tutar (CAVEMAN ilkesi, red-team'in kontrol edeceği bir nokta).
- Test fixture'ları (özellikle döngüsel symlink, AC-3) Windows'ta symlink oluşturma admin/developer-mode gerektirebilir — Saga #314'teki gibi `pytest.mark.skipif` deseni tekrarlanabilir, ama bu durumda AC-3 (en kritik AC — sonsuz döngü koruması) Windows'ta hiç doğrulanmamış olur. code-copilot'a NOT: mümkünse döngü testini symlink KULLANMADAN da simüle eden bir birim test ekle (örn. ziyaret-edilen-set mantığını doğrudan, gerçek symlink olmadan, mock bir dizin yapısıyla test et) — böylece AC-3'ün ÇEKİRDEK mantığı Windows'ta da gerçekten doğrulanır, sadece "gerçek symlink" entegrasyonu skip edilir.

## Open Questions
Yok — atdd.md'nin derinlik sınırı belirsizliği (kullanıcı sorusunda yanlışlıkla "5" denmişti) bu plan turunda `security.py` okunarak düzeltildi (gerçek değer: 3), atdd.md güncellendi.
