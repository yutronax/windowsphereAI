---
task_slug: klavye-ile-form-gezintisi
jira_id: null
saga_task_id: 257
priority: high
coverage_target: 90
performance_target: null
memory_target: null
test_strategy:
  unit: 70
  integration: 0
  e2e: 30
affected_modules:
  - ui/src/components/onboarding/OnboardingScreen.tsx
  - ui/src/components/onboarding/OnboardingScreen.test.tsx
  - ui/e2e/onboarding.spec.ts
---

# ATDD — klavye-ile-form-gezintisi

## Jira Kaynağı
Jira'ya bağlı değil — yerel görev. Saga task #257, epic #23 "MVP: Kullanıcı girişi ve ilk kayıt akışı" (proje: windows-ai-files).

## Persona
Klavye ile gezinen (fare kullanamayan/kullanmayan) veya ekran okuyucu kullanan bir kullanıcı. Onboarding ekranındaki formu (klasör seçimi, istek yazma, gönderme) yalnızca klavye ile tamamlayabilmeli.

## Hedef (Neden)
Şu an hiçbir Enter tuşu işleme mantığı yok, hata sonrası odak taşıma yok. Kod keşfi (2026-08-17) doğruladı: `onKeyDown`/`onSubmit`/`.focus()` çağrısı hiçbir yerde bulunmuyor. Tab sırası zaten büyük ölçüde doğru (DOM sırası: Klasör Seç → path → textarea → Devam) ama Enter ile gönderim ve hata sonrası odaklanma tamamen eksik — klavye kullanıcısı hatayı görsel olarak fark etse bile odak orada kalmadığı için düzeltmek üzere tekrar Tab basması gerekiyor.

## User Story
As a klavye ile gezinen kullanıcı
I want formu (klasör seç → istek yaz → gönder) yalnızca klavye ile, mantıklı bir sırayla ve Enter ile tamamlayabilmek
So that fareye ihtiyaç duymadan onboarding'i bitirebileyim, hata olduğunda da odak otomatik olarak düzeltmem gereken alana gitsin

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. [Critical] Given klasör seçili ve form durumu herhangi, When kullanıcı sırayla Tab'a basarak gezinir, Then odak sırası "Klasör Seç" → `selected-folder-path` → `request-textarea` → "Devam" şeklinde ilerler (regresyon-koruması — mevcut DOM sırası zaten bu, kod değişikliği gerektirmeyebilir ama açıkça test edilmeli).
2. [Critical] Given `request-textarea` odaklı, When kullanıcı Enter'a basar, Then textarea'ya normal bir yeni satır eklenir; `onContinue` çağrılmaz, hiçbir hata tetiklenmez (textarea'nın çok satırlı yazma davranışı korunur).
3. [Critical] Given form geçerli (boş olmayan istek + erişilebilir seçili klasör), When "Devam" butonu VEYA `selected-folder-path` odaklıyken Enter'a basılır, Then `onContinue` çağrılır (tıklamayla aynı davranış).
4. [High] Given form geçersiz (istek boş/whitespace-only), When "Devam"a tıklanır VEYA "Devam"/`selected-folder-path` odaklıyken Enter'a basılır, Then kırmızı hata mesajı gösterilir VE odak `request-textarea`'ya taşınır.
5. [High] Given kullanıcı erişilemez/geçersiz bir klasör seçer, When hata gösterilir, Then odak "Klasör Seç" butonuna taşınır (yeniden seçime hazır durumda).
6. [Medium] Given "Klasör Seç" butonu odaklı, When Enter'a basılır, Then tarayıcının native buton davranışıyla dialog açılır (`chooseFolder` tetiklenir) — bu davranış submit mantığıyla karışmaz, değişmez.

## Davranış Sözleşmesi (hangi durumda ne döner)
| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path — form geçerliyken Enter/click (Devam veya path odağında) | `onContinue()` çağrılır | Yok (bu task kapsamında `onContinue` no-op kalıyor — Kapsam Dışı) | Görsel değişiklik yok (sonraki ekrana geçiş ayrı task) | AC-3 |
| 2 | Girdi geçersiz — boş istek, Enter/click ile submit denemesi | `isRequestEmpty: true` | Odak `request-textarea`'ya taşınır | Kırmızı kenarlık + mesaj + odak metin kutusunda | AC-4 |
| 3 | Kaynak yok / erişilemez klasör (chooseFolder anında tetiklenir, submit denemesiyle değil) | `isFolderInvalid: true` | Odak "Klasör Seç" butonuna taşınır | Kırmızı hata mesajı + odak buton üzerinde | AC-5 |
| 8 | Hiçbir şey yapılamadı ama hata da yok — Enter, hiçbir izlenen elemana odaklı değilken (örn. `<body>`) basılırsa | Hiçbir state değişmez | Yok | Hiçbir görsel değişiklik yok | Bilinçli no-op — global bir keydown dinleyicisi YOK, sadece belirli elementlere (`selected-folder-path`, `request-textarea`) `onKeyDown` eklendi; "Devam"/"Klasör Seç" butonlarında Enter zaten tarayıcının native buton davranışıyla kendi `onClick`'ini tetikler, ekstra kod gerekmez |

Kısmi başarı: Bu task'ta geçerli değil — odak taşıma ve Enter işleme atomik, senkron DOM işlemleri.
Yetkisiz erişim / Dış bağımlılık hatası / Zaman aşımı satırları silindi: Bu task saf klavye/odak mantığı; klasör erişilebilirlik kontrolünün kendisi (ağ/IPC çağrısı) zaten Saga #256'da ele alındı, burada tekrar edilmiyor.
Boş sonuç ↔ hata ayrımı: Bu task'ta geçerli değil.

## Test Strategy
Unit: 70% — `OnboardingScreen.test.tsx`: `fireEvent.keyDown` ile Enter senaryoları (textarea içi/dışı, geçerli/geçersiz form), `document.activeElement` ile odak taşıma doğrulaması.
Integration: 0% — backend/API entegrasyonu bu task kapsamında yok.
E2E: 30% — `onboarding.spec.ts`: gerçek tarayıcıda `page.keyboard.press('Tab')`/`page.keyboard.press('Enter')` ile uçtan uca klavye gezintisi ve odak doğrulaması.

## Benchmark / Başarı Ölçütü
Coverage Target: 90% (önceki iki task ile tutarlı varsayılan)
Performance Target: yok
Memory: yok
Görsel/UI kriteri: Odak göstergeleri (focus ring/outline) zaten mevcut CSS'te tanımlı (`.onboarding-primary-btn:focus-visible`), yeni bir görsel stil eklenmiyor — bu task sadece odağın DOĞRU ELEMANA taşınmasıyla ilgili, görünümüyle değil. `verify` adımında ekran görüntüsü gerekmeyebilir (odak DOM state'i, `document.activeElement` ile test edilir), ama regresyon kontrolü için yine de bir tur önerilir.
Diğer ölçülebilir kriterler: Kabul kriteri sahibi otomatik testler (unit+e2e yeşile dönerse tamamlanmış sayılır).

## Kapsam Dışı
- Ekran okuyucu duyuru iyileştirmeleri — mevcut `aria-live="polite"` pattern'i (Saga #255/#256'dan) yeterli kabul edildi, yeni bir ARIA stratejisi eklenmiyor.
- Focus-trap/modal davranışı — bu ekranda modal yok, alakasız.
- `<form>` elementine sarma / native `onSubmit` — kullanıcı kararıyla manuel `onKeyDown` handler'ları tercih edildi, JSX yapısı büyük ölçüde korunuyor.
- `onContinue`'nun gerçek çağrılma/geçiş mantığı — hâlâ no-op (Saga #255'te de aynı karar verilmişti).
- `selected-folder-path`'in tab sırasından çıkarılması — kullanıcı kararıyla kalıyor, mevcut tooltip erişilebilirliği korunuyor.

## Etkilenen Dosyalar/Modüller (bilinen)
- `ui/src/components/onboarding/OnboardingScreen.tsx` (yeni `onKeyDown` handler'ları, `useRef` ile textarea/Klasör-Seç-butonu referansları, hata sonrası `.focus()` çağrıları)
- `ui/src/components/onboarding/OnboardingScreen.test.tsx` (yeni unit testler)
- `ui/e2e/onboarding.spec.ts` (yeni e2e senaryoları)

## Rollback Beklentisi
Geçerli değil — state'siz, yan etkisiz bir UI davranışı; DB/dosya değişikliği yok, standart `git revert` yeterli.

## Risks
- "Klasör Seç" ve "Devam" butonlarında Enter'ın native buton davranışına güvenilmesi (ekstra `onKeyDown` eklenmemesi) — bu davranış tüm tarayıcılarda/JSDOM'da tutarlı olmayabilir, implementasyon sırasında (`code_diff.md`'de) doğrulanmalı; gerekirse bu butonlara da açık `onKeyDown` eklenebilir.
- Hata sonrası `.focus()` çağrısının React'ın render/commit döngüsüyle doğru zamanlanması (state güncellemesi commit olduktan SONRA focus çağrılmalı, yoksa henüz DOM'a yazılmamış bir elemente focus denenebilir) — `useEffect` veya callback ref kullanımı gerekebilir, plan.md'de netleştirilecek.

## Assumptions
- "Klasör Seç" butonu odaklıyken Enter'a basmanın zaten native olarak `chooseFolder`'ı tetiklediği (submit ile karışmadığı) varsayıldı — tarayıcıların standart buton davranışı, ayrı kod gerekmiyor (AC-6 bunu bir regresyon-koruma testi olarak doğruluyor, yeni davranış eklemiyor).
- "Devam" butonu odaklıyken Enter'a basmanın zaten native olarak `onClick={handleContinueClick}`'i tetiklediği varsayıldı — aynı native buton davranışı.
- Bu iki varsayım doğruysa, gerçek yeni kod sadece `selected-folder-path`'e (native buton olmayan tek tabIndex=0 eleman) bir `onKeyDown` eklemekle ve hata sonrası odak taşıma mantığıyla sınırlı kalabilir — plan.md aşamasında doğrulanacak.

## Unknowns
- Yukarıdaki native-buton-Enter varsayımının JSDOM (unit test ortamı) içinde de gerçek tarayıcıdaki gibi davranıp davranmayacağı — test yazarken doğrulanacak, davranmazsa `code-copilot`/implementasyon aşamasında butonlara da açık `onKeyDown` eklenecek.

## Sorular ve Cevaplar (ham kayıt)
1. selected-folder-path tab sırasında kalsın mı? → Evet, kalsın
2. Enter tuşu nerede submit tetiklemeli? → Textarea dışında herhangi bir odakta
3. Enter'a basıldığında form geçersizse ne olmalı? → Devam'a tıklanmış gibi davranılır, hata gösterilir, odak hatalı alana gider
4. Boş istek hatası sonrası odak nereye taşınmalı? → request-textarea'ya
5. Geçersiz klasör hatası sonrası odak nereye taşınmalı? → 'Klasör Seç' butonuna
6. Implementasyon yaklaşımı: form mu, manuel onKeyDown mı? → Manuel onKeyDown handler'ları
7. Test stratejisi oranı (70/0/30) uygun mu? → Evet
8. Kabul kriteri sahibi kim? → Otomatik testler (unit+e2e) yeşile dönerse yeterli
9. Kapsam dışı: ekran okuyucu iyileştirmeleri ve focus-trap? → Evet, ikisi de kapsam dışı
10. Task-slug 'klavye-ile-form-gezintisi' uygun mu? → Evet
