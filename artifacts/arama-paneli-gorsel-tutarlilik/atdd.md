---
task_slug: arama-paneli-gorsel-tutarlilik
jira_id: null
saga_task_id: 359
priority: low
coverage_target: 90
performance_target: null
memory_target: null
test_strategy:
  unit: 100
  integration: 0
  e2e: 0
affected_modules:
  - ui/src/components/search/SearchPanel.tsx
  - ui/src/components/search/SearchPanel.test.tsx
  - ui/src/tokens.ts
  - ui/src/components/primitives/Card.tsx
---

# ATDD — arama-paneli-gorsel-tutarlilik

## Jira Kaynağı
Jira'ya bağlı değil — yerel görev. Saga Epic #40 "Arama Paneli Görsel Tutarlılık" (proje: windows-ai-files, id 2), Saga Task #359.

## Persona
Masaüstü uygulaması (Tauri) kullanan, dosyalarını isim/uzantı/tarih filtreleriyle arayan kullanıcı. (Haiku alt-ajanı tarafından yanıtlandı.)

## Hedef (Neden)
`SearchPanel.tsx` şu an **tamamen stilsiz** — hiç `<style>` bloğu yok, className'ler tanımlı ama karşılığı yok (çıplak tarayıcı görünümü). Diğer ekranlar (ChatScreen, PlanCard, ResultCard, OnboardingScreen) merkezi `tokens.ts` + `Card`/`Button` primitiflerini kullanıyor; SearchPanel bu tutarlılığın dışında kalıyor. (Haiku alt-ajanı tarafından yanıtlandı.)

## User Story
As a masaüstü uygulaması kullanıcısı
I want Arama panelinin diğer ekranlarla (renk, spacing, kart görünümü) tutarlı olmasını
So that uygulama bütün olarak tutarlı ve profesyonel görünsün

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. [Critical] Given `SearchPanel.test.tsx`'teki 9 mevcut test, When stil eklendikten sonra çalıştırıldığında, Then hepsi değişmeden yeşil kalır (davranış/DOM/testid/fetch mantığı birebir korunur).
2. [Critical] Given `SearchPanel.tsx` kaynak kodu, When incelendiğinde, Then sarmalayıcı `<section>` yerine `Card` primitifi kullanılır (`data-testid="search-panel"` korunur).
3. [High] Given filtre input'ları/label'ları, When stillendirildiğinde, Then renk/font/spacing değerleri `tokens.ts`'den gelir, hardcoded hex/px değer kalmaz.
4. [High] Given sonuç listesi (`search-panel-results`, 4 span/satır), When stillendirildiğinde, Then PlanCard'ın liste deseniyle (`tokens.colors.textSecondary`, `tokens.fontSize.small`) tutarlı görünür.
5. [Medium] Given hata mesajı (`search-panel-error`, `role="alert"`), When stillendirildiğinde, Then `tokens.colors.danger` kullanılır (ResultCard'ın `is-failed` deseniyle tutarlı).
6. [Medium] Given hint/empty durum mesajları (`search-panel-hint`, `search-panel-empty`), When stillendirildiğinde, Then `tokens.colors.textSecondary`/`tokens.fontSize.small` kullanılır (statüs metni deseni PlanCard/ResultCard ile tutarlı).
7. [Critical] Given sonuç satırları (`<li>`), When stillendirildiğinde, Then satırlar tıklanabilir/interaktif hale GETİRİLMEZ (AC-7 orijinal "read-only liste" kuralı korunur — buton/link rolü eklenmez).

## Davranış Sözleşmesi (hangi durumda ne döner)
| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Hiç filtre yok (happy path/idle) | `search-panel-hint` render, fetch ÇAĞRILMAZ | yok | "Aramak için bir filtre girin" | AC-1 |
| 2 | Filtre girildi, 300ms debounce sonrası başarılı yanıt | `search-panel-results` render, sonuçlar listelenir | 1x POST `/api/search` | Sonuç listesi | AC-1, AC-4 |
| 3 | Yarış durumu (hızlı ardışık filtre değişimi) | Sadece en son isteğin sonucu state'e yazılır | 2x POST, eski yanıt yok sayılır | Sadece en güncel sonuç | AC-1 |
| 4 | fetch reddedilir (network hatası) | `search-panel-error` = "Sunucuya ulaşılamadı. Lütfen tekrar deneyin." | yok | Kırmızı hata metni | AC-1, AC-5 |
| 5 | response.ok=false, status≠422/410 | `search-panel-error` = "Arama sırasında bir hata oluştu." | yok | Kırmızı hata metni | AC-1, AC-5 |
| 6 | status=422 | `search-panel-error` = backend `detail` alanı | yok | Backend'in spesifik hata mesajı | AC-1, AC-5 |
| 7 | status=410 | `search-panel-error` = "Seçili klasör artık mevcut değil" | yok | Kırmızı hata metni | AC-1, AC-5 |
| 8 | Filtre var, sonuç boş | `search-panel-empty` = "Sonuç bulunamadı" | yok | Nötr metin (hint DEĞİL) | AC-1, AC-6 |
| 9 | Unmount/remount | Tüm state (filtreler, sonuçlar) sıfırlanır | yok | Baştan boş form | AC-1 |
| 10 | Sonuç satırına tıklama | Hiçbir aksiyon tetiklenmez | yok | Görsel değişiklik yok, buton/link rolü YOK | AC-1, AC-7 |

Kısmi başarı: Uygulanmaz — saf CSS ekleme görevi, "kısmi stil" durumu AC-3'ün (tüm renkler tokens.ts'den) FAIL sayılmasıyla eşdeğer, ayrı bir dönüş değeri yok.

Hiçbir şey yapılamadı ama hata da yok: Uygulanmaz — deterministik CSS ekleme, "sessiz başarı" riski yok.

Boş sonuç ↔ hata ayrımı: Zaten kodda net (satır 8 vs 4-7 yukarıdaki tabloda) — bu görev bu ayrımı DEĞİŞTİRMEZ, sadece görsel olarak ikisinin birbirinden ayırt edilebilir (örn. hata kırmızı, boş sonuç nötr renk) kalmasını sağlar.

## Test Strategy
Unit: 100% — SearchPanel.test.tsx (9 mevcut davranışsal test, değişmeden yeşil kalmalı)
Integration: 0%
E2E: 0% — saf CSS ekleme, PlanCard/ResultCard görevindeki kararla tutarlı (Haiku alt-ajanı önerisi, kullanıcı onayı bekleniyor)

## Benchmark / Başarı Ölçütü
Coverage Target: 90%
Performance Target: yok
Memory: yok
Görsel/UI kriteri: Diğer ekranlarla (ChatScreen/PlanCard/ResultCard) tutarlı renk/spacing/font — `verify` adımında mümkünse `vision-test` ile kontrol edilir.
Diğer ölçülebilir kriterler: `SearchPanel.tsx` içinde `grep -E "#[0-9A-Fa-f]{3,6}"` taraması 0 sonuç döner (tüm renkler tokens.ts'den).

## Kapsam Dışı
- Yeni filtre alanı eklenmesi.
- Debounce/fetch/state mantığının değişmesi.
- Sonuç satırlarının tıklanabilir/seçilebilir/interaktif hale getirilmesi (AC-7 kesin sınır).
- Yeni bir primitif bileşen oluşturulması (mevcut Card/Button yeterli olmalı; input için yeni bir primitif GEREKMEZ, plan.md'de netleştirilecek).

## Etkilenen Dosyalar/Modüller (bilinen)
- ui/src/components/search/SearchPanel.tsx
- ui/src/components/search/SearchPanel.test.tsx (davranış testleri değişmez, gerekirse stil-doğrulama testi eklenebilir)
- ui/src/tokens.ts (okuma amaçlı)
- ui/src/components/primitives/Card.tsx (okuma amaçlı)

## Proje Ortamı Kısıtı (arama/grep kapsamı)
Önceki task'ta (plan-result-kartlari-tasarim) doğrulanan proje kökü aynen geçerli: `C:\Users\YUSUF ÇİNAR\OneDrive\Belgeler\Masaüstü\projelerim\Yazılım_müh\windows-ai-files`. Arama bu klasörle sınırlı tutulmalı.

## Rollback Beklentisi
Stil ekleme bir testi kırarsa: kök neden (beklenmedik DOM yapısı değişikliği) bulunur, düzeltilemezse değişiklik geri alınır.

## Risks
- Haiku alt-ajanının önerdiği `tokens.spacing.md`/`tokens.spacing.sm` gibi token adları **tokens.ts'de gerçekte YOK** (mevcut tek spacing token'ı `tokens.spacing.buttonPadding`) — bu bir halüsinasyon, plan.md aşamasında gerçek `tokens.ts` içeriğine göre düzeltilecek, mevcut olmayan token adı kullanılmayacak.
- SearchPanel'de input elemanları için proje genelinde ortak bir "input stili" emsali yok (ilk kez bu görevde tanımlanıyor) — plan.md'de bu netleştirilmeli: yeni bir token eklenecek mi yoksa component-local mi kalacak.

## Assumptions
- (Varsayım) Input alanları için Button/Card gibi ayrı bir primitif oluşturulmayacak, component-local stil (tokens.ts referanslı) yeterli — CAVEMAN ilkesi.
- (Varsayım) Kabul kriteri: mevcut 9 testin yeşil kalması + kod incelemesinde hardcoded renk kalmaması yeterli, ek bir manuel görsel onay şart değil ama tercih edilir.

## Unknowns
- tokens.ts'e input-özel yeni bir token eklenip eklenmeyeceği (örn. input border rengi/height) — plan.md'de gerçek tokens.ts içeriğine bakılarak netleştirilecek.

## Sorular ve Cevaplar (ham kayıt)
1. Kullanıcı rolü/persona → (Haiku alt-ajanı tarafından yanıtlandı) Masaüstü uygulaması kullanıcısı, dosya arıyor.
2. Ana hedef → (Haiku alt-ajanı tarafından yanıtlandı) Stilsizlik diğer ekranlarla tutarsızlık yaratıyor.
3. Happy path → (Haiku alt-ajanı tarafından yanıtlandı) Card sarmalayıcı + tokens tabanlı input/label stili — spacing token adları hatalıydı, düzeltilecek.
4. Edge case 1 (sonuç listesi) → (Haiku alt-ajanı tarafından yanıtlandı) PlanCard liste deseni referans.
5. Edge case 2 (hata mesajı) → (Haiku alt-ajanı tarafından yanıtlandı) tokens.colors.danger.
6. Davranış sözleşmesi → (Haiku alt-ajanı tarafından yanıtlandı, yukarıdaki tabloya işlendi).
7. Başarı ölçütü → (Haiku alt-ajanı tarafından yanıtlandı) Testler yeşil + tokens kullanımı.
8. Kapsam dışı → (Haiku alt-ajanı tarafından yanıtlandı) Yeni filtre, davranış değişikliği, interaktif satır YASAK.
9. Bağımlılıklar → (Haiku alt-ajanı tarafından yanıtlandı) SearchPanel + tokens.ts + Card.
10. Test stratejisi → (Haiku alt-ajanı tarafından yanıtlandı) 100/0/0.
11. Rollback → (Haiku alt-ajanı tarafından yanıtlandı) Kök neden bulunur, düzeltilemezse geri alınır.
12. Kabul kriteri sahibi → (Haiku alt-ajanı tarafından yanıtlandı) Otomatik test yeşili + kod incelemesi.
