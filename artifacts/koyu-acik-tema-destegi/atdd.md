---
task_slug: koyu-acik-tema-destegi
jira_id: null
saga_task_id: 360
priority: low
coverage_target: 90
performance_target: null
memory_target: null
test_strategy:
  unit: 95
  integration: 5
  e2e: 0
affected_modules:
  - ui/src/tokens.ts
  - ui/src/theme.css
  - ui/src/main.tsx
  - ui/src/App.tsx
  - ui/src/lib/theme.ts
---

# ATDD — koyu-acik-tema-destegi

## Jira Kaynağı
Jira'ya bağlı değil — yerel görev. Saga Epic #41 "Koyu/Açık Tema Desteği" (proje: windows-ai-files, id 2), Saga Task #360.

## Persona
Masaüstü uygulaması kullanıcısı — ortam ışığına göre (parlak ortamda açık, karanlıkta koyu tema) tercih değiştirmek isteyen kişi. (Haiku alt-ajanı tarafından yanıtlandı.)

## Hedef (Neden)
Uygulama şu an sabit koyu görünümde. Açık tema seçeneği okunabilirlik/ergonomi ve kullanıcı tercihi sağlar. `tokens.ts`'deki statik hex renkler CSS custom property'lere (`var(--color-x)`) çevrilerek, mevcut 7 bileşenin (Button, Card, ChatScreen, PlanCard, ResultCard, SearchPanel, TransactionHistoryPanel) kaynak kodu hiç değişmeden tema-duyarlı hale getirilir. (Ana ajan tarafından kod keşfiyle doğrulandı: bu bileşenlerin hepsi zaten `tokens.colors.X` üzerinden okuyor.)

## User Story
As a masaüstü uygulaması kullanıcısı
I want Koyu/açık tema arasında geçiş yapabilmeyi
So that Ortam ışığına/tercihime uygun bir arayüz kullanabileyim

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. [Critical] Given uygulama ilk açıldığında (localStorage boş), When render edildiğinde, Then varsayılan tema koyu (mevcut görünüm) olur — davranış değişmez.
2. [Critical] Given kullanıcı tema toggle'ına tıkladığında, When tıklama gerçekleştiğinde, Then `document.documentElement`'e `data-theme="light"`/`data-theme` kaldırma (koyu) uygulanır ve tercih `localStorage`'a yazılır.
3. [Critical] Given daha önce bir tema tercihi kaydedilmişse, When uygulama yeniden yüklendiğinde (mount), Then `localStorage`'dan okunan tercih uygulanır.
4. [High] Given `localStorage` bozuk/geçersiz bir değer içeriyorsa, When uygulama yüklendiğinde, Then güvenli şekilde varsayılan (koyu) temaya düşülür — hata fırlatılmaz.
5. [Critical] Given `tokens.ts`'in renkleri CSS var referanslarına çevrildiğinde, When mevcut 7 bileşenin (Button, Card, ChatScreen, PlanCard, ResultCard, SearchPanel, TransactionHistoryPanel) testleri çalıştırıldığında, Then hepsi değişmeden yeşil kalır (bileşen kaynak kodu DEĞİŞMEZ).
6. [Medium] Given `theme.css` dosyası, When incelendiğinde, Then `:root` (koyu/mevcut varsayılan) ve `[data-theme="light"]` (açık) için tam bir CSS custom property seti tanımlı olur — `tokens.ts`'deki her renk anahtarına karşılık gelir.
7. [Medium] Given tema toggle butonu, When render edildiğinde, Then erişilebilir bir `aria-label`/`data-testid` içerir ve mevcut ekran akışlarını (fail-closed onay, arama, vb.) etkilemez.

## Davranış Sözleşmesi (hangi durumda ne döner)
| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | İlk yükleme, localStorage boş | `data-theme` attribute'u SET EDİLMEZ (varsayılan `:root` = koyu) | yok | Mevcut koyu görünüm (değişmez) | AC-1 |
| 2 | Toggle tıklama (koyu→açık) | `document.documentElement.dataset.theme = 'light'` | `localStorage.setItem('theme', 'light')` | Anında açık tema | AC-2 |
| 3 | Toggle tıklama (açık→koyu) | `data-theme` attribute'u KALDIRILIR | `localStorage.setItem('theme', 'dark')` | Anında koyu tema | AC-2 |
| 4 | Kayıtlı tercih var (mount) | `data-theme` mount sırasında localStorage'dan uygulanır | `localStorage.getItem('theme')` okunur | Kaydedilmiş tema ile açılır | AC-3 |
| 5 | localStorage bozuk/geçersiz değer (örn. "xyz") | Geçersiz değer yok sayılır, `data-theme` SET EDİLMEZ | yok (hata fırlatılmaz) | Varsayılan koyu tema | AC-4 |
| 6 | localStorage erişilemez (örn. gizli sekme/izin hatası) | try/catch ile yutulur, varsayılan koyu tema | yok (crash yok) | Varsayılan koyu tema | AC-4 |
| 7 | 7 bileşenin mevcut testleri (tema değişikliğinden ETKİLENMEMELİ) | Tüm testler token değerlerini `tokens.colors.X` üzerinden okumaya devam eder | yok | Test ortamında (jsdom, CSS var çözümlemesi sınırlı olabilir) davranış değişmez | AC-5 |

Kısmi başarı: Uygulanmaz — tema geçişi anlık ve tekil bir DOM attribute + localStorage yazma işlemi, ara durum yok.

Hiçbir şey yapılamadı ama hata da yok: localStorage erişilemezse (satır 6) sessizce varsayılana düşülür — bu BİLİNÇLİ bir "sessiz başarı" değil, "güvenli varsayılan" davranışıdır ve AC-4 ile açıkça belirtilmiştir.

Boş sonuç ↔ hata ayrımı: Uygulanmaz — bu görevde sorgu/veri döndüren bir akış yok.

## Test Strategy
Unit: 95% — tokens.ts'in CSS var referansları, theme.css'in her iki blok için tanımlı olması, tema toggle fonksiyonunun (localStorage yaz/oku, data-theme set/kaldır) davranışı, localStorage hata durumu
Integration: 5% — toggle bileşeninin gerçek render'da tıklanınca doğru attribute'u set ettiğinin RTL testi
E2E: 0% — Haiku alt-ajanı önerisi (DOM attribute + localStorage tamamen unit-testable, e2e gereksiz), kullanıcı onayı bekleniyor

## Benchmark / Başarı Ölçütü
Coverage Target: 90%
Performance Target: yok
Memory: yok
Görsel/UI kriteri: Her iki temada da (koyu/açık) 7 bileşenin okunabilir kalması — otomatik testler CSS var referanslarının varlığını doğrular, gerçek görsel kontrol `verify` adımında mümkünse yapılır (backend bağımlılığı nedeniyle önceki tasklarda olduğu gibi kısıtlı olabilir).
Diğer ölçülebilir kriterler: `tokens.ts` HARİCİNDE hiçbir bileşen dosyası (Button.tsx, Card.tsx, ChatScreen.tsx, PlanCard.tsx, ResultCard.tsx, SearchPanel.tsx, TransactionHistoryPanel.tsx) bu görev kapsamında DEĞİŞMEZ — değişirse bu bir mimari sapma olarak red-team'e bildirilir.

## Kapsam Dışı
- Sistem/işletim sistemi `prefers-color-scheme` tercihiyle otomatik eşleşme (v2'ye bırakıldı).
- `OnboardingScreen.tsx`'in tema-duyarlı hale getirilmesi (hâlâ hardcoded hex kullanıyor, `tokens.ts`'e hiç bağlı değil — ayrı bir follow-up task).
- Tema başına özel illüstrasyon/görsel farklılık.
- WCAG kontrast denetimi/accessibility audit'i (ayrı bir görev kapsamı).
- 7 bileşenin (Button/Card/ChatScreen/PlanCard/ResultCard/SearchPanel/TransactionHistoryPanel) kaynak kodunun değiştirilmesi — sadece `tokens.ts` + yeni `theme.css` + toggle mekanizması.

## Etkilenen Dosyalar/Modüller (bilinen)
- ui/src/tokens.ts (statik hex → CSS var referansı)
- ui/src/theme.css (YENİ — `:root` + `[data-theme="light"]`)
- ui/src/main.tsx (theme.css import)
- ui/src/App.tsx (toggle bileşeninin/mount-time tema uygulamasının yaşayacağı yer — plan.md'de netleştirilecek)
- ui/src/lib/theme.ts (YENİ, muhtemel — localStorage oku/yaz + data-theme set/kaldır yardımcı fonksiyonları; plan.md'de gerekliliği doğrulanacak)

## Proje Ortamı Kısıtı (arama/grep kapsamı)
Önceki tasklarda doğrulanan proje kökü aynen geçerli: `C:\Users\YUSUF ÇİNAR\OneDrive\Belgeler\Masaüstü\projelerim\Yazılım_müh\windows-ai-files`.

## Rollback Beklentisi
Bir test kırılırsa veya bir bileşen bir temada bozuk görünürse: kök neden bulunur (CSS var eksik/yanlış tanımlı mı, tokens.ts'de referans hatası mı), düzeltilemezse değişiklik geri alınır. `tokens.ts` dışındaki bileşen dosyalarının değişmemesi gerektiği için rollback riski düşük.

## Risks
- `tokens.ts`'in mevcut testi (`tokens.test.ts`) muhtemelen renklerin belirli hex değerlere eşit olduğunu doğruluyor olabilir — bu test, renkler `var(--x)` string'lerine çevrildiğinde KIRILABİLİR. plan.md'de bu dosya incelenip gerçek assertion'lar tespit edilecek.
- jsdom (test ortamı), gerçek tarayıcı gibi CSS custom property'leri `getComputedStyle` ile çözümlemeyebilir — bu, Button.test.tsx/Card.test.tsx gibi `toHaveStyle({ backgroundColor: tokens.colors.primary })` şeklindeki MEVCUT testlerin (artık `tokens.colors.primary` bir `var(--x)` string'i döndüreceği için) DEĞİŞMEDEN geçip geçmeyeceği belirsiz — plan.md'de doğrulanacak, gerekirse bu ATDD'nin AC-5 sözü ("mevcut testler değişmeden yeşil kalır") ile çelişebilir, kullanıcıya açıkça bildirilecek.

## Assumptions
- (Varsayım, Haiku alt-ajanı önerisi) Sadece manuel toggle + localStorage yeterli, `prefers-color-scheme` v1 kapsamında değil.
- (Varsayım, Haiku alt-ajanı önerisi) OnboardingScreen kapsam dışı.
- (Varsayım) Toggle UI'ının tam yeri (ChatScreen üst köşesi mi, App.tsx seviyesinde bir global header mı) plan.md'de gerçek kod keşfiyle netleştirilecek.

## Unknowns
- `tokens.test.ts`'in mevcut içeriği ve bu görevle çelişip çelişmediği (Risks'te işaretlendi, plan.md'de çözülecek).
- jsdom'un CSS var string'lerini mevcut `toHaveStyle` testleriyle nasıl etkileşeceği (Risks'te işaretlendi, plan.md'de çözülecek — büyük olasılıkla mevcut testler zaten `tokens.colors.X` değerini kullanıyor, string eşitliği bozulmaz çünkü hem test hem component AYNI `tokens.colors.X` referansını okuyor).

## Sorular ve Cevaplar (ham kayıt)
1. Kullanıcı rolü/persona → (Haiku alt-ajanı tarafından yanıtlandı) Ortam ışığına göre tema değiştiren kullanıcı.
2. Ana hedef → (Haiku alt-ajanı tarafından yanıtlandı) Okunabilirlik/ergonomi + tercih.
3. Happy path → (Haiku alt-ajanı tarafından yanıtlandı) Toggle ikonu, anında değişim, localStorage persist.
4. Edge case 1 (prefers-color-scheme) → (Haiku alt-ajanı tarafından yanıtlandı) v1'de gerekmez, sadece manuel toggle.
5. Edge case 2 (OnboardingScreen) → (Haiku alt-ajanı tarafından yanıtlandı) Kapsam dışı.
6. Davranış sözleşmesi → (Haiku alt-ajanı tarafından yanıtlandı, yukarıdaki tabloya işlendi).
7. Başarı ölçütü → (Haiku alt-ajanı tarafından yanıtlandı) Testler yeşil + 7 bileşen kodu değişmez.
8. Kapsam dışı → (Haiku alt-ajanı tarafından yanıtlandı) prefers-color-scheme, OnboardingScreen, illüstrasyon, a11y audit.
9. Bağımlılıklar → (Haiku alt-ajanı tarafından yanıtlandı) tokens.ts, theme.css, main.tsx, toggle bileşeni.
10. Test stratejisi → (Haiku alt-ajanı tarafından yanıtlandı) 95/5/0.
11. Rollback → (Haiku alt-ajanı tarafından yanıtlandı) Hızlı geri alma, minimal kaynak değişimi sayesinde düşük risk.
12. Kabul kriteri sahibi → (Haiku alt-ajanı tarafından yanıtlandı) Otomatik test yeşili + minimal manuel spot-check.
