# Plan — dosya-icerik-arama-encoding-timeout
_Reference: atdd.md_

## Files to Modify
| File | Why | Risk |
|------|-----|------|
| backend/file_search.py | `search_files()` içine `content_contains` parametresi, 3-encoding fallback (utf-8→latin-1→cp1254), global 10sn timeout, binary/10MB+ atlama, symlink dışlama eklenir (AC-1..3, AC-8..9) | medium |
| backend/models.py | `SearchRequest.contentContains` alanı (max_length=500, boş/whitespace reddi validator — AC-4, AC-9), `SearchResponse.partial: bool = False` alanı (AC-2) eklenir | low |
| backend/main.py | `search_endpoint()` içinde `content_contains` parametresinin `search_files()`'a geçirilmesi ve `partial` bayrağının response'a yansıtılması (mevcut modifiedAfter/Before try/except pattern'i izlenir) | low |

## New Files
Yok — mevcut #313 dosyalarının üzerine ekleme yapılıyor, yeni modül gerekmiyor.

## Dependencies
- `backend/file_search.py::search_files()` mevcut filtre-zinciri deseni (AND mantığı, `entry.iterdir()` üzerinde sıralı filtre uygulama) korunmalı — content filtresi aynı zincire eklenir.
- `backend/models.py::SearchResultItem` değişmiyor (mutlak path içermeme ilkesi — Saga #283).
- `is_path_allowed`/`security.py` içindeki symlink-güvenli path çözümleme deseni yoksa (AC-8 için `entry.is_symlink()` kontrolü + `entry.resolve()`'un `allowed_root.resolve()` altında kalıp kalmadığı kontrolü) `file_search.py` içine yeni, izole bir yardımcı olarak eklenecek — `security.py`'nin plan-validasyon fonksiyonlarına (rename/merge/redact hedefleri) dokunulmayacak, onlar bu task'ın kapsamı dışında.
- Testler mevcut `backend/tests/test_file_search.py` ve `backend/tests/test_main_integration.py` dosyalarına eklenir (yeni test dosyası açılmıyor, mevcut `TestSearchFiles*` sınıf deseni izlenir).

## Migration Required?
Hayır — DB şeması / SQLAlchemy modeli değişmiyor, sadece Pydantic request/response şeması (`SearchRequest`/`SearchResponse`) ve saf fonksiyon parametresi ekleniyor.

## Risks
- (atdd.md'den taşındı) Encoding fallback sırası: utf-8 dene → `UnicodeDecodeError` ise latin-1 dene → o da başarısız olursa cp1254 dene. latin-1 pratikte HER byte dizisini hatasız decode eder (256 kod noktasının hepsi tanımlı), yani `UnicodeDecodeError` fırlatmaz — bu yüzden "latin-1 başarılı ama yanlış" senaryosu gerçek bir risktir ve tek başına except-zincirinden yakalanamaz. code-copilot'a NOT: sıra utf-8 → cp1254 → latin-1 (cp1254 önce, latin-1 en son çünkü o hep "başarılı" görünür) olarak uygulanmalı, ya da bir heuristic (decode edilen metinde geçersiz/kontrol karakteri oranı) eklenmeli. Bu netleştirme code-copilot'a extra_instructions olarak geçirilmeli.
- (atdd.md'den taşındı) 10sn global timeout, dosya bazında değil TÜM taramanın toplamı için işletilmeli (tek büyük dosyanın okunması timeout'u tek başına aşmamalı — 10MB limiti zaten bunu sınırlıyor ama okuma+decode+substring maliyeti göz önünde tutulmalı).
- Yeni risk (plan aşamasında bulundu): `SearchRequest`'e `max_length=500` Pydantic constraint'i eklemek, mevcut `field_validator("sessionId")` desenine ek bir `Field(max_length=500)` veya ayrı validator gerektirir — iki yaklaşımdan hangisinin kod tabanı konvansiyonuna uyduğu (bu dosyada zaten `field_validator` kullanılıyor) code-copilot'a örnek olarak gösterilmeli.

## Open Questions
Yok — atdd.md + threat-model + bu keşif turu açık soru bırakmadı; sıra netleştirmesi (risk maddesi) code-copilot'a doğrudan talimat olarak aktarılacak, kullanıcıya tekrar soru gerekmiyor.
