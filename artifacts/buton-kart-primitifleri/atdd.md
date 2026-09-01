---
task_slug: buton-kart-primitifleri
jira_id: null
saga_task_id: 346
priority: high
coverage_target: 100
performance_target: null
memory_target: null
test_strategy:
  unit: 80
  integration: 20
  e2e: 0
affected_modules:
  - ui/src/components/primitives/Button.tsx (yeni)
  - ui/src/components/primitives/Button.test.tsx (yeni)
  - ui/src/components/primitives/Card.tsx (yeni)
  - ui/src/components/primitives/Card.test.tsx (yeni)
  - ui/src/components/primitives/index.ts (yeni)
  - ui/src/tokens.ts (sadece import edilir, değişmez)
---

# ATDD — buton-kart-primitifleri

## Jira Kaynağı
Jira'ya bağlı değil — yerel görev (Saga #346, Epic #36 "Tasarım Sistemi
Temeli").

## Persona
Ekran geliştiricileri — bu primitifleri ileride PlanCard, ResultCard,
ChatScreen, OnboardingScreen, TransactionHistoryPanel gibi ekranlara
taşıyacak kişiler (ayrı, ekran-özel epic'lerde). Bu task'ta primitifleri
hiçbir ekran doğrudan tüketmez; task sadece API'yı kurar.

## Hedef (Neden)
`ui/src/tokens.ts` (Saga #345) zaten var ama hiçbir bileşen kullanmıyor;
her ekran kendi inline `<style>` bloğunda buton/kart tekrar tanımlıyor. Bu
task, token katmanı üzerine kurulu, tip-güvenli, tekrar kullanılabilir
Button/Card React bileşenlerini kurarak bu tekrarın önüne geçecek temel
primitifleri sağlar (DRY + tasarım tutarlılığı).

## User Story
As a ekran geliştiricisi
I want token'lara dayanan hazır `<Button>` ve `<Card>` React bileşenlerini
So that ileride her ekranı bu primitiflere taşırken (ayrı task'larda) inline
stil tekrarı yazmak zorunda kalmayayım.

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. [Critical] Given `ui/src/tokens.ts`, When
   `ui/src/components/primitives/Button.tsx` oluşturulur, Then `<Button>`
   bileşeni `variant` prop'u (`'primary' | 'danger'`, default `'primary'`)
   ve `disabled` prop'u alır; `primary` → `tokens.colors.primary`/
   `primaryHover`/`primaryActive`, `danger` → `tokens.colors.danger`
   renklerini, `tokens.radius.default`, `tokens.size.buttonHeight`,
   `tokens.fontSize.base`, `tokens.spacing.buttonPadding` değerlerini
   kullanır — hiçbir renk/ölçü değeri inline sabit olarak tekrar
   yazılmaz.
2. [Critical] Given `ui/src/tokens.ts`, When
   `ui/src/components/primitives/Card.tsx` oluşturulur, Then `<Card>`
   bileşeni `tokens.colors.panelBackground`, `tokens.colors.border`,
   `tokens.radius.default` değerlerini kullanır ve `children` render eder.
3. [Critical] Given `Button.tsx`/`Card.tsx`, When
   `Button.test.tsx`/`Card.test.tsx` (Vitest + RTL) çalıştırılır, Then her
   variant/prop kombinasyonunun doğru stil/attribute'u uyguladığı
   doğrulanır (render testi).
4. [High] Given primitif dosyaları, When `tsc --noEmit` çalıştırılır, Then
   TypeScript derlemesi hatasız geçer (tip güvenliği; `variant` için
   geçersiz bir string derleme zamanında hata verir).
5. [High] Given primitifler henüz hiçbir ekrana bağlanmamış, When mevcut
   ekran testleri (Onboarding/ChatScreen/PlanCard/ResultCard/
   TransactionHistoryPanel/SearchPanel) çalıştırılır, Then hiçbir regresyon
   oluşmaz (bu task saf ekleme, hiçbir mevcut import değişmiyor).
6. [Medium] Given `ui/src/components/primitives/index.ts`, When dışarıdan
   `import { Button, Card } from './components/primitives'` yapılır, Then
   ikisi de named export olarak erişilebilir olur.

## Davranış Sözleşmesi (hangi durumda ne döner)
| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path: `<Button variant="primary">` render edilir | Token renklerini uygulayan bir `<button>` DOM elemanı | Yok (saf render) | Buton mavi (#1E3A8A), 44px yükseklik, 8px radius | AC-1, AC-3 |
| 1b | Happy path: `<Card>{children}</Card>` render edilir | `panelBackground`/`border` uygulayan bir `<div>` | Yok | Açık gri panel, çocuklar içinde render | AC-2, AC-3 |
| 2 | Geçersiz `variant` değeri (TS tipine uymayan string) | Derleme zamanı TypeScript hatası — runtime'a hiç ulaşmaz | Build kırılır | `tsc` çıktısında tip hatası | AC-4 |
| 2b | `variant` verilmez | Default `'primary'` uygulanır | Yok | Buton mavi render edilir | AC-1 |
| 7 | Kısmi başarı: `Button.tsx` tamamlanır, `Card.tsx` eksik/hatalı kalır | Kabul edilemez — PR/commit tamamlanmış sayılmaz, test suite kırmızı kalır | Yok | Test çıktısında Card testleri FAIL | AC-2, AC-3 |
| 8 | Hiçbir şey yapılamadı ama hata yok | Bu senaryo bu task'ta oluşamaz: dosyalar ya derlenir+testleri geçer ya da `tsc`/Vitest açıkça FAIL verir; sessiz "hiçbir şey olmadı" imkansız | — | — | AC-3, AC-4 |

Boş sonuç ↔ hata ayrımı: Uygulanmaz — bu bir sorgu/API değil, statik React
bileşenleri. Eksik/bozuk bir primitif her zaman AC-3 (test) veya AC-4 (tip
kontrolü) FAIL'iyle açıkça görünür.

## Test Strategy
Unit: 80% — `Button.test.tsx`/`Card.test.tsx` içinde her variant/prop
kombinasyonunun (variant, disabled, children) doğru render edildiğini
doğrulayan RTL render testleri.
Integration: 20% — primitiflerin `tokens.ts`'ten doğru değerleri okuduğunu
(token değişirse bileşenin de değişmesi) doğrulayan testler; henüz hiçbir
ekrana bağlı olmadığından ekran-seviyeli entegrasyon testi bu task
kapsamında yok.
E2E: 0% — hiçbir ekran bu primitifleri tüketmiyor, E2E senaryosu anlamsız.

## Benchmark / Başarı Ölçütü
Coverage Target: 100% (Button + Card'daki her prop/variant dalının test
edilmesi)
Performance Target: Uygulanmaz (statik React bileşenleri, runtime maliyeti
yok)
Memory: Uygulanmaz
Görsel/UI kriteri: Uygulanmaz — bu task hiçbir ekranı görsel olarak
değiştirmiyor (primitifler henüz hiçbir yerde kullanılmıyor). Görsel
doğrulama, primitiflerin ekranlara taşındığı SONRAKİ task'larda yapılacak.
Diğer ölçülebilir kriterler: `npm run test` (Vitest) primitif testlerinde
yeşil, `tsc --noEmit` hatasız, mevcut 6 bileşenin (Onboarding, ChatScreen,
PlanCard, ResultCard, TransactionHistoryPanel, SearchPanel) test suite'i
kırmızıya düşmez.

## Kapsam Dışı
- Mevcut ekranların (PlanCard, ResultCard, ChatScreen, OnboardingScreen,
  TransactionHistoryPanel, SearchPanel) bu primitiflere taşınması — ayrı,
  ekran-özel epic/task'larda yapılacak (bu task'ın description'ında
  açıkça belirtilmiş).
- Dark mode / tema-switch desteği — Epic #41'in işi.
- `Card` için variant sistemi (örn. `elevated`, `outlined`) — mevcut
  envanterde (task #347) tek bir kart stili görüldü, spekülatif variant
  eklenmeyecek; ihtiyaç doğarsa ayrı task.
- CSS custom properties üretimi — `tokens.ts` zaten TS sabitleri olarak
  kurulmuş (Saga #345 kararı), bu task o kararı değiştirmiyor.

## Etkilenen Dosyalar/Modüller (bilinen)
- `ui/src/components/primitives/Button.tsx` (yeni)
- `ui/src/components/primitives/Button.test.tsx` (yeni)
- `ui/src/components/primitives/Card.tsx` (yeni)
- `ui/src/components/primitives/Card.test.tsx` (yeni)
- `ui/src/components/primitives/index.ts` (yeni, re-export)
- `ui/src/tokens.ts` (sadece import edilir, değiştirilmez)

## Rollback Beklentisi
Git revert yeterli — yeni dosyalar hiçbir mevcut ekran/import tarafından
henüz tüketilmiyor, state taşımıyor. Revert edilirse dependent task #348
("verify: token/primitif katmanı hiçbir ekranın görünümünü bozmadığını
doğrula") yeniden planlanır.

## Risks
- Task #347 envanterinin örneklem olması riski (design-tokens-foundation
  atdd.md'de de not edilmiş) — primitifler sadece `tokens.ts`'te açıkça
  var olan değerleri kullanır; yeni bir stil ihtiyacı keşfedilirse ayrı
  task ile `tokens.ts`'e eklenip primitife yansıtılır.

## Assumptions
- Primitifler React wrapper bileşenleri (`<Button>`, `<Card>`) olarak
  kurulacak, salt CSS class'ları DEĞİL — proje zaten TSX kullanıyor ve
  tip-güvenli prop API'sı (variant/disabled) CSS class string'inden daha
  güvenli. Bu bir varsayımdır; Haiku alt-ajanı tarafından önerildi,
  kullanıcı henüz onaylamadı.
- `Button` variant seti `'primary' | 'danger'` ile sınırlı tutuldu — mevcut
  envanterde (design-tokens-foundation'da referans verilen 5 bileşen)
  görülen tek ayrım birincil/tehlike rengiydi; başka bir variant ihtiyacı
  keşfedilirse ayrı task.
- `Card`'ın tek bir stil varyantı var (variant prop'u yok) — envanterde
  kart için tek bir görsel stil (panelBackground + border + radius)
  görüldü.

## Unknowns
- Envanterdeki (task #347) 5 bileşenin gerçek buton/kart prop ihtiyaçları
  (örn. icon-only buton, loading state) — bu task'ta kapsam dışı
  bırakıldı, ekran-özel taşıma task'larında ortaya çıkarsa primitif
  genişletilir.

## Sorular ve Cevaplar (ham kayıt)
(Haiku alt-ajanı tarafından yanıtlandı — claude-omni bu makinede kurulu
değil, Adım B fallback kullanıldı)

1. Persona → Ekran geliştiricileri (diğer epiklerde primitifleri tüketecek
   kişiler) (Haiku alt-ajanı tarafından yanıtlandı)
2. Ana hedef → DRY + tasarım tutarlılığı; tokens.ts var ama hiçbir yerde
   kullanılmıyor sorunu (Haiku alt-ajanı tarafından yanıtlandı)
3. Happy path yapı → React wrapper bileşenleri (`<Button>`, `<Card>`) +
   TypeScript props, salt CSS class değil (Haiku alt-ajanı tarafından
   yanıtlandı)
4. Edge case 1 (eksik/geçersiz prop) → TypeScript derleme zamanı hatası;
   `variant` verilmezse default `'primary'` (Haiku alt-ajanı tarafından
   yanıtlandı)
5. Edge case 2 (isim çakışması) → `ui/src/components/primitives/` ayrı
   namespace altında izole tutulur (Haiku alt-ajanı tarafından yanıtlandı)
6. Davranış sözleşmesi → yukarıdaki tabloya işlendi; kısmi başarı "kabul
   edilemez, test suite kırmızı kalır" olarak netleşti (Haiku alt-ajanı
   tarafından yanıtlandı, atdd.md yazarı tarafından somutlaştırıldı)
7. Benchmark → TypeScript hatasız derleme + RTL render testleri yeşil +
   mevcut ekranlarda 0 regresyon (Haiku alt-ajanı tarafından yanıtlandı)
8. Kapsam dışı → ekranların primitife taşınması HARİÇ (task
   description'ından zaten netti, Haiku teyit etti)
9. Bağımlılıklar → `ui/src/components/primitives/{Button,Card}.tsx` +
   testleri + `index.ts` (Haiku alt-ajanı tarafından yanıtlandı)
10. Performans/güvenlik kısıtı → yok, statik/runtime-zero bileşenler
    (Haiku alt-ajanı tarafından yanıtlandı)
11. Rollback → git revert yeterli, henüz hiçbir ekran tüketmiyor (Haiku
    alt-ajanı tarafından yanıtlandı)
12. Test stratejisi → %80 unit / %20 integration / %0 e2e — Haiku'nun
    önerisi (%75/%25/%0) atdd.md yazarı tarafından %80/%20/%0'a
    yuvarlandı, kullanıcı onayı bekleniyor
13. Kabul kriteri sahibi → otomatik test (Vitest+RTL+tsc) yeterli; bu
    proje tek-geliştirici akışında ayrı bir "design/lead review" adımı
    yok, bu nedenle Haiku'nun önerdiği %60/%40 insan-onay bölünmesi
    kullanılmadı — pipeline zaten `red-team` adımında otomatik kod
    incelemesi içeriyor (varsayım olarak işaretlendi)
