---
task_slug: ilk-istek-oturum-baglami
jira_id: null
saga_task_id: 258
priority: high
coverage_target: 90
performance_target: null
memory_target: null
test_strategy:
  unit: 70
  integration: 0
  e2e: 30
affected_modules:
  - backend/main.py
  - backend/models.py
  - backend/tests/test_main_integration.py
  - ui/src/App.tsx
  - ui/src/App.test.tsx
  - ui/src/components/onboarding/OnboardingScreen.tsx
  - ui/src/components/onboarding/OnboardingScreen.test.tsx
  - ui/src/lib/backendHealth.ts
  - ui/e2e/onboarding.spec.ts
---

# ATDD — ilk-istek-oturum-baglami

_Bu ATDD `saga-oto` skill'i tarafından, adaptif netleştirme sorularına
kullanıcıya sorulmadan en makul (Recommended) cevaplar seçilerek
oluşturuldu. Tüm kararlar aşağıdaki "Sorular ve Cevaplar" bölümünde
`(saga-oto tarafından otomatik seçildi)` notuyla işaretlidir._

## Jira Kaynağı
Jira'ya bağlı değil — yerel görev. Saga task #258, epic #23 "MVP: Kullanıcı girişi ve ilk kayıt akışı" (proje: windows-ai-files).

## Persona
Onboarding'i tamamlamış (geçerli klasör + boş olmayan istek girmiş) kullanıcı; "Devam"a bastığında isteğinin gerçekten backend'e ulaştığını ve bir oturumun başladığını görmek istiyor.

## Hedef (Neden)
`App.tsx:27`'deki `onContinue={() => {}}` şu ana kadar bilinçli olarak no-op bırakılmıştı (Saga #255/#256/#257'nin kapsamı client-side validasyon/klavye navigasyonuydu). Bu görev onu gerçek anlamda bağlıyor: frontend seçili klasörü ve normalize edilmiş istek metnini `127.0.0.1:8000` üzerindeki Entry uç noktasına gönderiyor, backend `docs/DESIGN_DECISIONS.md` D6'daki Entry katmanı sorumluluğuna uygun şekilde (girdiyi normalize eder, oturum bağlamı kurar, geçersizse net hata döner) bir `SessionContext` oluşturup dönüyor.

## User Story
As a onboarding'i tamamlamış kullanıcı
I want "Devam"a bastığımda isteğimin backend'e iletilip bir oturumun başlatıldığını görmek
So that dosya işlemi isteğim gerçekten işleme alınsın, sadece client-side'da kalmasın

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. [Critical] Given form geçerli (boş olmayan istek + erişilebilir seçili klasör), When kullanıcı "Devam"a tıklar/Enter'a basar, Then frontend `POST http://127.0.0.1:8000/api/session` isteği gönderir (`{selectedFolder, requestText}` gövdesiyle), backend `201` + `{sessionId, selectedFolder, requestText}` döner, frontend ana sohbet ekranına (mevcut `data-testid="main-chat-screen"` stub'ı) geçer.
2. [Critical] Given backend `selectedFolder`/`requestText`'i geçersiz bulur (defense-in-depth — normalde frontend zaten boş göndermez ama Entry katmanı kendi başına da doğrulamalı), When istek gönderilir, Then backend `422` + net bir hata mesajı döner, frontend'de gönderim hatası gösterilir, ana ekrana geçiş OLMAZ.
3. [Critical] Given backend'e ulaşılamıyor (kapalı/network hatası), When kullanıcı "Devam"a basar, Then frontend'de "İstek gönderilemedi. Lütfen tekrar deneyin." hata mesajı gösterilir, "Devam" butonu tekrar denenebilir kalır (kalıcı olarak kilitlenmez).
4. [High] Given istek gönderiliyor (yanıt beklenirken), When kullanıcı tekrar "Devam"a basmaya çalışır, Then buton devre dışıdır — çift gönderim engellenir.
5. [High] Given backend başarıyla bir `SessionContext` oluşturur, Then dönen yanıt gerçek, doğrulanabilir bir `sessionId` (UUID) içerir — "başarılı" iddiası sadece `200`/`201` durum koduna değil, gözlemlenebilir bir kimliğe dayanır (davranış sözleşmesi, "başarı iddiası doğrulanabilir olmalı" ilkesi).
6. [Medium] Given `/api/session` POST isteği frontend origin'inden (`tauri://localhost` veya Vite dev origin'leri) gelir, Then mevcut CORS middleware bu isteği de kabul eder (regresyon — `allow_methods=["*"]` zaten POST'u kapsıyor, açıkça test edilecek).

## Davranış Sözleşmesi (hangi durumda ne döner)
| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path — geçerli klasör+istek | `201` + `{sessionId, selectedFolder, requestText}` | Backend'de in-memory session store'a kayıt eklenir | Ana sohbet ekranına geçiş | AC-1, AC-5 |
| 2 | Girdi geçersiz (backend tarafı, defense-in-depth) | `422` + `{detail: "..."}` (FastAPI/Pydantic varsayılan validasyon hatası biçimi) | Yok | Gönderim hatası mesajı, formda kalınır | AC-2 |
| 5 | Dış bağımlılık hatası — backend'e ulaşılamıyor/timeout | `fetch()` reddedilir (network error/timeout) | Yok | "İstek gönderilemedi. Lütfen tekrar deneyin." mesajı, buton tekrar aktif | AC-3 |

Kaynak yok / Yetkisiz erişim satırları silindi: bu bir oluşturma (create)
işlemi, var olan bir kaynağı arama değil; kimlik doğrulama bu MVP'de yok
(backend sadece `127.0.0.1`'de dinliyor, yerel tek-kullanıcı masaüstü
uygulaması).
Zaman aşımı satırı silindi: satır 5'teki genel ağ hatası kapsamına dahil
edildi — backend zaten localhost'ta çalıştığından agresif bir ayrı
timeout stratejisi gerekmiyor, tarayıcının varsayılan `fetch` davranışı
yeterli.
Kısmi başarı satırı silindi: `POST /api/session` atomik bir işlem, ara
durum yok.
Hiçbir şey yapılamadı ama hata yok satırı silindi: `fetch()` ya çözülen
bir response ya da reddedilen bir promise döner — üçüncü, sessiz bir
"belirsiz" durum React state'inde tutulmuyor; her iki dal da (then/catch)
açıkça ele alınıyor (AC-1/AC-2 veya AC-3).
Boş sonuç ↔ hata ayrımı: Bu task'ta geçerli değil — `/api/session` bir
liste/sorgu endpoint'i değil.

## Test Strategy
Unit: 70% — Backend: `pytest` ile `TestClient` üzerinden `/api/session` happy path + 422 validasyon senaryoları (`test_main_integration.py`'nin mevcut pattern'i genişletilerek). Frontend: `OnboardingScreen.test.tsx`'te `global.fetch` mock'lanarak happy path, backend-hatası, çift-gönderim-engelleme senaryoları.
Integration: 0% — Ayrı bir integration katmanı yok, backend testleri zaten `TestClient` ile gerçek FastAPI app'i çalıştırıyor (bu proje için "unit" sayılıyor, mevcut `test_main_integration.py` konvansiyonuyla tutarlı).
E2e: 30% — `onboarding.spec.ts`: gerçek tarayıcıda `page.route('**/api/session', ...)` ile mock'lanmış backend'e karşı happy path + hata senaryosu.

## Benchmark / Başarı Ölçütü
Coverage Target: 90% (önceki üç task ile tutarlı varsayılan)
Performance Target: yok (yerel loopback isteği, ağ gecikmesi yok)
Memory: yok
Görsel/UI kriteri: Gönderim hatası mesajı mevcut `.onboarding-error-message`/`aria-live="polite"` pattern'iyle gösterilmeli (yeni bir görsel dil icat edilmiyor) — `verify` adımında ekran görüntüsüyle doğrulanmalı (Codex vision-test kotası dolu, manuel/Playwright screenshot yöntemi kullanılacak).
Diğer ölçülebilir kriterler: Kabul kriteri sahibi otomatik testler (unit+e2e yeşile dönerse tamamlanmış sayılır — `saga-oto` kullanıcı onayı istemiyor).

## Kapsam Dışı
- Decision katmanına (LLM planner) gerçek bir çağrı yapılması — backend'de henüz bir planner/LLM modülü yok, bu ayrı bir MVP task'ı (muhtemelen epic #24 "Ana sohbet arayüzü" kapsamında).
- Session persistence (disk/DB) — MVP için in-memory bir Python dict yeterli kabul edildi; backend restart olursa oturumlar kaybolur, bu kabul edilebilir (tek kullanıcılı masaüstü uygulaması).
- Ana sohbet ekranının gerçek işlevselliği (plan gösterimi, onay akışı) — mevcut `data-testid="main-chat-screen"` stub'ı olduğu gibi yeniden kullanılıyor, yeni bir ekran inşa edilmiyor.
- Session expiry/timeout/temizleme mantığı.
- `config.json`'a (persisted setup) bu oturumun yazılması/güncellenmesi — mevcut `/api/config` GET-only akışına dokunulmuyor, ayrı bir kaygı.
- Kimlik doğrulama/yetkilendirme — backend sadece localhost'ta dinliyor, bu MVP'nin güvenlik modeli zaten bu (D6, Security katmanı ayrı bir gelecek task).

## Etkilenen Dosyalar/Modüller (bilinen)
- `backend/main.py` (yeni `POST /api/session` route'u)
- `backend/models.py` (yeni — `SessionRequest`, `SessionContext` Pydantic modelleri)
- `backend/tests/test_main_integration.py` (yeni testler)
- `ui/src/App.tsx` (`onContinue`'u gerçek bir geçiş tetikleyicisine bağlama)
- `ui/src/App.test.tsx` (yeni — şu an yok, oluşturulacak)
- `ui/src/components/onboarding/OnboardingScreen.tsx` (gerçek `fetch` çağrısı, `isSubmitting`/`submitError` state'leri)
- `ui/src/components/onboarding/OnboardingScreen.test.tsx` (yeni testler)
- `ui/src/lib/backendHealth.ts` (`BACKEND_ORIGIN` sabiti export edilip yeniden kullanılacak — kod tekrarını önlemek için)
- `ui/e2e/onboarding.spec.ts` (yeni e2e senaryoları)

## Rollback Beklentisi
Backend tarafında DB/migration yok (in-memory), frontend tarafında yan etkisiz bir `fetch` çağrısı — hata durumunda kullanıcı sadece formda kalır, tekrar deneyebilir. Standart `git revert` yeterli.

## Risks
- `SessionContext`'in gerçek alanları `docs/DESIGN_DECISIONS.md`'de somut olarak tanımlanmamış (sadece "girdi standardizasyonu, oturum bağlamı kurar" deniyor) — bu task, alanları (`sessionId`, `selectedFolder`, `requestText`) kendi makul yorumuyla tanımlıyor. İleride gerçek bir Decision/Planner entegrasyonu yapılırken bu şemanın genişletilmesi (örn. `createdAt`, `status`) gerekebilir.
- In-memory session store, backend her yeniden başladığında sıfırlanır — bu MVP için kabul edilebilir ama gerçek kullanıcı deneyiminde (backend crash/restart) veri kaybına yol açar; ayrı bir persistence task'ı gerekebilir (bu task'ın kapsamı dışı, gerekirse red-team/ilerideki bir task bunu flagleyebilir).

## Assumptions
- `SessionContext` yanıt alanları camelCase (`sessionId`, `selectedFolder`, `requestText`) — mevcut `/api/config`'in zaten camelCase (`selectedFolder`) döndürdüğü konvansiyonla tutarlı olması için varsayıldı.
- `POST /api/session` endpoint yolu — mevcut `/api/health`, `/api/config` isimlendirme konvansiyonuyla tutarlı olması için `/api/session` seçildi (Entry/SessionContext terminolojisiyle uyumlu).
- Backend validasyon hatası için FastAPI'nin varsayılan `422 Unprocessable Entity` + Pydantic hata gövdesi kullanılacağı varsayıldı (proje genelinde özel bir hata formatı/wrapper yok).

## Unknowns
- Gerçek Decision/Planner entegrasyonu geldiğinde `SessionContext` şemasının nasıl genişleyeceği (bkz. Risks) — bu task'ın çözemeyeceği, ileride tekrar ele alınacak bir konu.

## Sorular ve Cevaplar (ham kayıt)
1. Enter tuşu/tıklama sonrası backend'e gerçekten istek gönderilsin mi, yoksa yine no-op mu kalsın? → Gönderilsin, bu task'ın amacı bu (task açıklamasından, netti)
2. Backend session'ı nasıl saklamalı (DB mi, in-memory mi)? → In-memory (dar kapsam ilkesi — MVP tek-kullanıcılı masaüstü uygulaması, DB gereksiz karmaşıklık) (saga-oto tarafından otomatik seçildi)
3. Decision katmanına gerçek bir çağrı yapılsın mı? → Hayır, backend'de henüz planner modülü yok, kapsam dışı bırakıldı (saga-oto tarafından otomatik seçildi)
4. Başarılı gönderim sonrası kullanıcı ne görmeli? → Mevcut `main-chat-screen` stub'ı yeniden kullanılsın, yeni bir ekran inşa edilmesin (dar kapsam ilkesi) (saga-oto tarafından otomatik seçildi)
5. Backend hatası/network hatası durumunda davranış ne olmalı? → Mevcut `.onboarding-error-message`/`aria-live` pattern'iyle hata gösterilsin, buton tekrar denenebilir kalsın (saga-oto tarafından otomatik seçildi)
6. Çift gönderim nasıl engellenmeli? → `isSubmitting` state'i ile buton devre dışı bırakılsın (mevcut `isValidatingFolder` pattern'iyle tutarlı) (saga-oto tarafından otomatik seçildi)
7. Yanıt alan isimleri camelCase mi snake_case mi olmalı? → camelCase, mevcut `/api/config` konvansiyonuyla tutarlı (saga-oto tarafından otomatik seçildi)
8. Test stratejisi oranı (70/0/30) uygun mu? → Evet, önceki üç task ile tutarlı (saga-oto tarafından otomatik seçildi)
9. Kabul kriteri sahibi kim? → Otomatik testler yeşile dönerse yeterli (saga-oto tarafından otomatik seçildi)
10. Task-slug 'ilk-istek-oturum-baglami' uygun mu? → Evet, task başlığından türetildi (saga-oto tarafından otomatik seçildi)
