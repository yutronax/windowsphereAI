---
task_slug: api-health-tanilama
jira_id: null
saga_task_id: 331
priority: low
coverage_target: 85
performance_target: "<3s (LLM ping dahil)"
memory_target: null
test_strategy:
  unit: 25
  integration: 65
  e2e: 10
affected_modules:
  - backend/main.py
  - backend/plan_generation.py
  - backend/security.py
  - backend/models.py
---

# ATDD — api-health-tanilama

## Jira Kaynağı
Jira'ya bağlı değil — yerel görev. Saga #331: "/api/health'e LLM sağlayıcı ve whitelist tanılama kontrolü ekle".

## Persona
Destek/geliştirici (curl veya log üzerinden manuel çağırıyor). Bu iterasyonda Tauri UI'da görsel bir "Sistem Durumu" paneli YOK — API-seviyesi bir tanılama yüzeyi.

## Hedef (Neden)
Kullanıcıdan "plan üretilemiyor" şikayeti geldiğinde, sorunun LLM sağlayıcısında mı (api_key/ağ/timeout) yoksa whitelist/config'te mi (allowed_root dışı yol) olduğunu hızlıca ayırt etmek. Mevcut `GET /api/health` sadece `{"status": "ok"}` döndüğü için hiçbir gerçek bağımlılık kontrolü yapmıyor.

## User Story
As a destek/geliştirici
I want `/api/health`'in LLM sağlayıcısına ve verilen bir yolun whitelist'e uygunluğuna gerçekten bakmasını
So that "plan üretilemiyor" şikayetlerinde kök nedeni (LLM mi whitelist mi) hızlıca teşhis edebileyim

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. [Critical] Given config'te geçerli bir LLM api_key ayarlı ve LLM sağlayıcı erişilebilir, When `GET /api/health` (path parametresiz) çağrılır, Then `200 {"status": "ok", "llm_reachable": true, "path_allowed": null}` döner.
2. [Critical] Given LLM sağlayıcıya ağ hatası/timeout nedeniyle erişilemiyor, When `GET /api/health` çağrılır, Then yine `200` döner ama `"llm_reachable": false`.
3. [High] Given geçerli bir `path` query parametresi allowed_root içinde, When `GET /api/health?path=...` çağrılır, Then `"path_allowed": true` döner.
4. [High] Given `path` query parametresi allowed_root DIŞINDA (whitelist ihlali), When `GET /api/health?path=...` çağrılır, Then `200` içinde `"path_allowed": false` döner (hata değil — tanılama sonucu).
5. [Medium] Given `path` parametresi hiç verilmedi, When `GET /api/health` çağrılır, Then whitelist kontrolü atlanır ve `"path_allowed": null` döner.
6. [Medium] Given config hiç yapılmamış (setup tamamlanmamış), When `GET /api/health` çağrılır, Then `200` döner, `llm_reachable` config eksikliğini yansıtır (`false`), `path_allowed` `null` kalır — 500 patlamaz.
7. [Medium] Given `path` query parametresi malformed (ör. boş string, path-traversal denemesi gibi ayrıştırılamayan bir değer), When `GET /api/health?path=...` çağrılır, Then `400 {"detail": "path geçersiz"}` döner.

## Davranış Sözleşmesi (hangi durumda ne döner)
| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path (LLM erişilebilir, path verilmedi) | 200 `{"status":"ok","llm_reachable":true,"path_allowed":null}` | Yok (read-only) | "Sistem hazır" | AC-1 |
| 2 | Girdi geçersiz (path malformed) | 400 `{"detail":"path geçersiz"}` | Yok | API hata mesajı | AC-7 |
| 3 | Kaynak yok (config/setup hiç yapılmamış) | 200 `{"status":"ok","llm_reachable":false,"path_allowed":null}` | Yok | "Setup eksik, LLM kontrolü başarısız" | AC-6 |
| 4 | Dış bağımlılık hatası (LLM ağ/timeout) | 200 `{"status":"ok","llm_reachable":false,...}` | Yok | "LLM şu an ulaşılamıyor" | AC-2 |
| 5 | Zaman aşımı (LLM ping çok uzun sürerse) | 200, ping 5sn'de timeout → `llm_reachable:false` (retry yok) | Yok | "LLM çok yavaş / ulaşılamıyor" | AC-2 |
| 6 | Kısmi başarı (LLM up, path whitelist dışında — veya tersi) | 200 `{"status":"ok","llm_reachable":true,"path_allowed":false}` | Yok | "LLM ok, path reddedildi" | AC-4 |

Silinen satırlar ve neden:
- **Yetkisiz erişim**: N/A — bu endpoint zaten auth'suz, local-only tanılama amaçlı; yetkilendirme kapsamı bu görevde yok.
- **Hiçbir şey yapılamadı ama hata yok**: N/A — endpoint tasarımı gereği her durumda bir tanılama sonucu (`llm_reachable`/`path_allowed` alanlarıyla) döner, sessiz "hiçbir şey olmadı" durumu yapısal olarak mümkün değil.

Kısmi başarı: LLM erişilebilir ama path reddedilirse (veya tersi), HTTP 200 ile iki alan bağımsız olarak raporlanır — biri `true` biri `false` olabilir, çağıran taraf hangi bağımlılığın sorunlu olduğunu ayırt edebilir.
Hiçbir şey yapılamadı ama hata da yok: Geçerli değil — bkz. yukarıdaki silinme notu.
Boş sonuç ↔ hata ayrımı: `path_allowed: null` ("path hiç sorulmadı") ile `path_allowed: false` ("path sorgulandı ve reddedildi") AÇIKÇA farklı değerler — `null` ve `false` karıştırılmaz.

## Test Strategy
Unit: 25% — `plan_generation.py`'deki LLM erişilebilirlik kontrolü (mock client ile reachable/unreachable/timeout senaryoları)
Integration: 65% — `/api/health` endpoint'i (path var/yok/malformed, config var/yok, LLM mock üzerinden reachable/unreachable) — FastAPI TestClient ile
E2E: 10% — varsa gerçek/canlı bir LLM sağlayıcıya karşı tek bir smoke test (CI'da opsiyonel/skip edilebilir, gerçek api_key gerektirir)

## Benchmark / Başarı Ölçütü
Coverage Target: 85%
Performance Target: `/api/health` toplam yanıt süresi <3 saniye (LLM ping'e dahili 5sn timeout uygulanır, ama endpoint pratikte timeout'u beklemeden hızlı fallback ile 3sn altında tamamlanmalı — LLM ping'i ayrı bir kısa timeout'la sınırlandırılmalı, ör. 2-2.5sn)
Memory: Belirtilmedi (N/A)
Görsel/UI kriteri: Yok — bu görev sadece API, frontend değişikliği kapsam dışı.
Diğer ölçülebilir kriterler: Yanıtta gerçek dosya sistemi yolu (allowed_root'un mutlak yolu) asla açık dönmemeli — sadece boolean/null.

## Kapsam Dışı
- Periyodik/cron tabanlı otomatik health-check
- Tauri UI'da görsel "Sistem Durumu" paneli
- Whitelist altındaki TÜM alt klasörlerin taranması/doğrulanması (sadece verilen tek `path` kontrol edilir)
- Authentication/authorization eklenmesi (endpoint zaten local-only, mevcut auth modeliyle aynı kalır)

## Etkilenen Dosyalar/Modüller (bilinen)
- `backend/main.py` — `/api/health` endpoint'inin genişletilmesi
- `backend/plan_generation.py` — `OpenAICompatibleLLMClient`'a erişilebilirlik kontrolü eklenmesi (veya endpoint'in bu client'ı kullanarak hafif bir ping çağrısı yapması)
- `backend/security.py` — mevcut `is_path_allowed(path, allowed_root)` fonksiyonunun doğrudan kullanılması (değişiklik gerekmeyebilir)
- `backend/models.py` — yeni `HealthCheckResponse` Pydantic modeli (`status: str`, `llm_reachable: bool`, `path_allowed: bool | None`)

## Rollback Beklentisi
N/A — salt-okunur (read-only) `GET` endpoint'i, herhangi bir state/dosya değiştirmiyor, rollback kavramı geçerli değil.

## Risks
- LLM sağlayıcıya her `/api/health` çağrısında gerçek bir ağ isteği atmak, sık çağrılırsa (ör. bir izleme aracı tarafından) gereksiz LLM kotası/maliyeti tüketebilir — bu görev kapsamında bir rate-limit/cache eklenmiyor, ileride gerekirse ayrı bir Saga görevi açılmalı.
- LLM ping'in "gerçekten erişilebilir" olduğunu göstermesi için hangi hafif API çağrısının kullanılacağı (ör. models.list() vs. basit bir tamamlama isteği) sağlayıcıya göre değişebilir — implementasyon sırasında netleşecek.

## Assumptions
- `allowed_root`, `load_setup_config()` ile okunan mevcut config mekanizmasından geliyor (varsayım — kod incelemesinden çıkarıldı, kullanıcı tarafından ayrıca doğrulanmadı).
- Endpoint'in auth gerektirmediği, mevcut `/api/health`'in zaten auth'suz olduğu düzenin bu görevde de korunacağı varsayıldı.

## Unknowns
- LLM erişilebilirlik kontrolü için tam olarak hangi API çağrısının (models.list, minimal completion, vb.) kullanılacağı — `plan` adımında netleştirilmeli.
- `path` query parametresinin "malformed" sayılacağı tam kural seti (boş string mi, sadece path-traversal payload'ları mı, yoksa herhangi bir `Path()` parse hatası mı) — `plan` adımında netleştirilmeli.

## Sorular ve Cevaplar (ham kayıt)
1. Persona → Destek/geliştirici (curl/log), Tauri UI entegrasyonu bu kapsamda yok. (Haiku alt-ajanı tarafından yanıtlandı)
2. Ana hedef → "plan üretilemiyor" şikayetlerinde LLM ↔ whitelist ayrımı yapmak. (Haiku alt-ajanı tarafından yanıtlandı)
3. Happy path JSON şekli → `{"status":"ok","llm_reachable":true,"path_allowed":true}` (path verildiğinde); path verilmediğinde `path_allowed:null`. (Haiku alt-ajanı tarafından yanıtlandı)
4. LLM erişilemezse → HTTP 200, `llm_reachable:false` (sistem UP ama LLM DOWN, tanılama başarıyla raporlanıyor). (Haiku alt-ajanı tarafından yanıtlandı)
5. Path parametresi verilmezse → opsiyonel, kontrol atlanır, `path_allowed:null`. (Haiku alt-ajanı tarafından yanıtlandı)
6. Davranış sözleşmesi tablosu → yukarıdaki tabloda dolduruldu; "Yetkisiz erişim" ve "Hiçbir şey yapılamadı ama hata yok" satırları N/A olarak silindi. (Haiku alt-ajanı tarafından yanıtlandı)
7. Benchmark → <3 saniye toplam yanıt süresi, LLM ping'i kendi içinde ~2-2.5sn'de sınırlanmalı. (Haiku alt-ajanı tarafından yanıtlandı)
8. Kapsam dışı → cron health-check, Tauri UI paneli, whitelist'in tamamının taranması, auth eklenmesi. (Haiku alt-ajanı tarafından yanıtlandı)
9. Etkilenen dosyalar → main.py, plan_generation.py, security.py, models.py (yeni HealthCheckResponse). (Haiku alt-ajanı tarafından yanıtlandı)
10. Güvenlik kısıtı → yanıtta sadece boolean/null döner, gerçek dosya sistemi yolu asla açık edilmez. (Haiku alt-ajanı tarafından yanıtlandı)
11. Rollback → N/A, read-only GET, state değişmiyor. (Haiku alt-ajanı tarafından yanıtlandı)
12. Test stratejisi oranı → 25/65/10 (unit/integration/e2e) — entegrasyon-ağırlıklı çünkü health-check dış bağımlılık (LLM) kontrolü içeriyor. (Haiku alt-ajanı tarafından yanıtlandı)
