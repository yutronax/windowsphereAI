---
task_slug: onboarding-istek-metin-kutusu
jira_id: null
saga_task_id: 253
priority: high
coverage_target: 80
performance_target: null
memory_target: null
test_strategy:
  unit: 20
  integration: 15
  e2e: 65
affected_modules:
  - ui/src/components/onboarding/OnboardingScreen.tsx
---

# ATDD — onboarding-istek-metin-kutusu

## Jira Kaynağı
Jira'ya bağlı değil — yerel görev (Saga task #253, epic #23).

## Persona
Türkiye pazarında muhasebeci/avukat gibi teknik olmayan masaüstü kullanıcısı
(kullanıcı mesajından — DESIGN_DECISIONS.md §1).

## Hedef (Neden)
Orijinal epic kırılımı (#253/#254/#255/#258) "istek metin kutusu"nun var
olduğunu varsayıyordu, ama #250'nin ATDD'si bilinçli olarak sadece klasör
seçimini kapsamıştı — metin kutusunun kendisi hiçbir task'ta inşa
edilmemişti. Bu task o boşluğu kapatıyor: kullanıcının doğal dilde isteğini
yazabileceği, state'e bağlı, #253'ün orijinal stil tanımını (12px
border-radius, #E5E7EB kenarlık) karşılayan textarea'yı ekliyor —
#254 (placeholder), #255 (boş istek engelleme), #258 (gönderim) bunun
üzerine inşa edecek.

## User Story
As a teknik olmayan masaüstü kullanıcısı
I want klasör seçtikten sonra doğal dilde isteğimi yazabileceğim bir metin kutusu görmek
So that "bu klasördeki PDF'leri tarihe göre sırala" gibi bir istek yazabileyim

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. [Critical] Given onboarding ekranı, When render edilir, Then klasör seçim alanının altında bir `textarea` görünür — min-height 120px, border-radius 12px, border `#E5E7EB`, 16px gövde yazısı, 16px iç boşluk.
2. [Critical] Given textarea, When kullanıcı metin yazar, Then yazılan metin component'in kendi state'inde tutulur (controlled component, `value` textarea'ya yansır).
3. [High] Given textarea, When klavye/fare ile odaklanılır, Then kenarlık `#2563EB` olur ve hafif bir odak gölgesi (`box-shadow`) görünür.
4. [Medium] Given odak textarea'dan ayrılır (blur), Then kenarlık `#E5E7EB`'e geri döner.

## Davranış Sözleşmesi (hangi durumda ne döner)
Bu task salt görsel + state bağlama — "dönen değer" yerine render/state
durumu tablosu kullanıldı:

| # | Durum | Görsel/State Beklentisi | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path — boş textarea, hiçbir etkileşim yok | `min-height:120px`, `border-radius:12px`, `border:1px solid #E5E7EB` | Yok | Boş, stilli metin kutusu | AC-1 |
| 2 | Kullanıcı metin yazar | `value` state'i güncellenir, textarea bunu yansıtır | Yok (henüz diske/ağa gitmiyor — #258'in işi) | Yazdığı metni görür | AC-2 |
| 3 | Focus | `border:#2563EB` + `box-shadow` | Yok | Odaklanmış görünüm | AC-3 |
| 4 | Blur | Kenarlık `#E5E7EB`'e döner | Yok | Normal görünüme dönüş | AC-4 |

**Silinen satırlar ve neden:** "Girdi geçersiz/eksik", "kaynak yok",
"yetkisiz erişim", "dış bağımlılık hatası", "zaman aşımı", "kısmi başarı",
"hiçbir şey yapılamadı ama hata yok" — bu task hiçbir doğrulama/ağ/dosya
sistemi etkileşimi içermiyor, salt görsel bileşen + yerel state. Boş istek
doğrulaması bilinçli olarak #255'e bırakıldı (kapsam dışı, aşağıda).

Kısmi başarı: Uygulanmaz.
Hiçbir şey yapılamadı ama hata da yok: Uygulanmaz.
Boş sonuç ↔ hata ayrımı: Uygulanmaz.

## Test Strategy
Unit: 20% — state güncelleme mantığı (controlled component davranışı).
Integration: 15% — `getComputedStyle` ile border-radius/border/min-height
değerlerinin doğru uygulandığının component test seviyesinde doğrulanması.
E2E: 65% — Playwright ile gerçek tarayıcıda yazma, focus, blur senaryoları.

## Benchmark / Başarı Ölçütü
Coverage Target: 80%
Performance Target: Yok
Memory: Yok
Görsel/UI kriteri: Ekran görüntüsü kullanıcıya (Yusuf) gösterilip görsel
onay alınacak.
Diğer ölçülebilir kriterler: Yok.

## Kapsam Dışı
- Placeholder metni (Saga task #254'ün işi).
- Boş/geçersiz istek gönderimini engelleme (Saga task #255'in işi).
- Gerçek gönderim/backend API çağrısı (Saga task #258'in işi) — bu round'da
  yazılan metin yalnızca `OnboardingScreen` component'inin kendi state'inde
  tutulur, hiçbir yere gönderilmez.
- Klavye ile tam form gezinme sırası (Saga task #257'nin işi).

## Etkilenen Dosyalar/Modüller (bilinen)
- `ui/src/components/onboarding/OnboardingScreen.tsx` — yeni bir
  `requestText` state'i ve textarea JSX'i eklenecek, mevcut `<style>`
  bloğuna yeni bir class (`.onboarding-textarea` gibi, `onboarding-*`
  konvansiyonu) eklenecek.

## Rollback Beklentisi
Uygulanmaz (N/A) — salt görsel + yerel state, kalıcı yan etki yok.

## Risks
- Bu task'ın orijinal epic kırılımında (#253/#254/#255/#258) "metin kutusu
  zaten var" varsayımı hatalıydı — bu ATDD o varsayımı düzeltip kutunun
  kendisini de kapsama aldı. Sonraki task'lar (#254/#255/#258) bu task'ın
  kurduğu `requestText` state adını ve textarea yapısını referans almalı.

## Assumptions
- `requestText` state'i şimdilik yalnızca `OnboardingScreen` component'i
  içinde kalır, `App.tsx`'e prop olarak dışarı verilmez — #258 (gerçek
  gönderim) geldiğinde yeniden değerlendirilecek, bu round'da erken
  soyutlama yapılmaz. (kullanıcı onayı alındı)
- Textarea'nın backend hazır olana kadar disabled olup olmayacağı
  netleştirilmedi (diğer elementlerle tutarlılık için mantıklı olabilir
  ama kullanıcıya sorulmadı) — bu round'da **disabled uygulanmıyor**,
  gerekirse ayrı bir task'ta ele alınır (bkz. Unknowns).

## Unknowns
- Textarea'nın backend hazır olmadan (`backendStatus !== 'ready'`) disabled
  olup olmayacağı netleşmedi — mevcut UI deseninde (Klasör Seç/Devam
  butonları) tutarlılık için gerekebilir, ileride sorulmalı.

## Sorular ve Cevaplar (ham kayıt)
1. Persona/hedef → DESIGN_DECISIONS.md'den (kullanıcı mesajından, tekrar
   sorulmadı).
2. Metin kutusunun kendisi eksik, ne yapalım? → Bu task'a (#253) kutuyu da
   ekle, sonra stil uygula.
3. Input türü? → textarea, çok satırlı (120px min-height ile tutarlı).
4. State'e bağlansın mı? → Evet, controlled component.
5. Focus stili? → #2563EB kenarlık + hafif odak gölgesi.
6. Test stratejisi oranı? → 20/15/65.
7. Kapsam dışı neler? → Placeholder (#254), boş istek engelleme (#255),
   gerçek gönderim (#258).
8. Kabul kriteri sahibi kim? → Otomatik test + kullanıcının (Yusuf) görsel
   onayı.
9. Rollback geçerli mi? → Hayır, N/A.
10. Risk/varsayım? → State App.tsx'e dışarı verilmez, OnboardingScreen
    içinde kalır.
