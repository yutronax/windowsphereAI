---
task_slug: onboarding-istek-placeholder
jira_id: null
saga_task_id: 254
priority: low
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

# ATDD — onboarding-istek-placeholder

## Jira Kaynağı
Jira'ya bağlı değil — yerel görev (Saga task #254, epic #23,
"MVP: Kullanıcı girişi ve ilk kayıt akışı").

## Persona
Türkiye pazarında muhasebeci/avukat gibi teknik olmayan masaüstü kullanıcısı
([[onboarding-istek-metin-kutusu]] / DESIGN_DECISIONS.md §1 — kullanıcı
mesajından, tekrar sorulmadı).

## Hedef (Neden)
#253 istek textarea'sını boş haliyle bıraktı ve placeholder'ı bilinçli
olarak kapsam dışına attı (#254'ün işi olarak işaretlendi). Teknik olmayan
kullanıcı boş bir kutuyla karşılaştığında ne yazması gerektiğini
bilemiyor — somut bir örnek istek (ör. "Bu klasördeki PDF'leri tarihe göre
sırala") placeholder olarak gösterilerek kullanıcı yönlendirilir.

## User Story
As a teknik olmayan masaüstü kullanıcısı
I want istek kutusunda ne yazabileceğime dair somut bir örnek görmek
So that boş kutu karşısında ne isteyeceğimi bilemediğim an kalmasın

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. [Critical] Given onboarding ekranı render edilmiş, boş istek textarea'sı, When kullanıcı hiçbir şey yazmamış, Then textarea `placeholder="Bu klasördeki PDF'leri tarihe göre sırala"` gösterir ve placeholder rengi `#9CA3AF` (gerçek girilen metnin varsayılan rengine göre düşük kontrast).
2. [Critical] Given placeholder görünür durumda, When kullanıcı textarea'ya metin yazmaya başlar, Then placeholder tamamen kaybolur, yalnızca kullanıcının yazdığı metin (normal metin rengiyle) görünür.
3. [High] Given kullanıcı yazdığı metni tamamen siler, When textarea tekrar boşalır, Then placeholder aynı metinle tekrar görünür hale gelir (native `placeholder` attribute davranışı — ayrı bir state yönetimi gerekmez).
4. [Medium] Given placeholder görünürken textarea focus/blur olur, Then #253'te tanımlı kenarlık davranışı (`#2563EB` focus / `#E5E7EB` blur) bozulmaz, placeholder görünürlüğü bu geçişten etkilenmez.

## Davranış Sözleşmesi (hangi durumda ne döner)
Bu task #253 gibi salt görsel + native HTML `placeholder` attribute'u —
doğrulama/ağ/dosya sistemi etkileşimi yok. "Dönen değer" yerine
render/state durumu tablosu kullanıldı (kullanıcı onayı alındı: tamamen
N/A):

| # | Durum | Görsel/State Beklentisi | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path — boş textarea, hiçbir etkileşim yok | `placeholder` attribute'u DOM'da, `::placeholder` rengi `#9CA3AF` | Yok | Örnek istek metni (düşük kontrast) | AC-1 |
| 2 | Kullanıcı yazmaya başlar | `value` state'i güncellenir (#253'ten miras), placeholder native olarak kaybolur | Yok | Yazdığı metni normal renkte görür | AC-2 |
| 3 | Kullanıcı yazdığını tamamen siler | `value` boşalır, tarayıcı placeholder'ı otomatik tekrar gösterir | Yok | Örnek istek metni tekrar görünür | AC-3 |
| 4 | Focus/blur (placeholder görünürken) | #253 AC-3/AC-4 kenarlık davranışı değişmez | Yok | Odak/normal görünüm geçişi, placeholder etkilenmez | AC-4 |

**Silinen satırlar ve neden:** "Girdi geçersiz/eksik", "kaynak yok",
"yetkisiz erişim", "dış bağımlılık hatası", "zaman aşımı", "kısmi başarı",
"hiçbir şey yapılamadı ama hata yok" — #253 ile aynı gerekçe: bu task
hiçbir doğrulama/ağ/dosya sistemi etkileşimi içermiyor, salt görsel
placeholder attribute'u (kullanıcı onayı alındı).

Kısmi başarı: Uygulanmaz.
Hiçbir şey yapılamadı ama hata da yok: Uygulanmaz.
Boş sonuç ↔ hata ayrımı: Uygulanmaz.

## Test Strategy
Unit: 20% — placeholder metninin doğru string ile render edildiğinin
doğrulanması.
Integration: 15% — `getComputedStyle`/`::placeholder` üzerinden
`#9CA3AF` renginin uygulandığının component test seviyesinde
doğrulanması.
E2E: 65% — Playwright ile gerçek tarayıcıda: (a) yazınca placeholder'ın
kaybolduğu, (b) silince tekrar göründüğü, (c) #253'ün focus/blur
davranışının bozulmadığı senaryoları.

## Benchmark / Başarı Ölçütü
Coverage Target: 80%
Performance Target: Yok
Memory: Yok
Görsel/UI kriteri: Ekran görüntüsü (placeholder görünür + yazarken
kaybolma) kullanıcıya (Yusuf) gösterilip görsel onay alınacak.
Diğer ölçülebilir kriterler: Yok.

## Kapsam Dışı
- Yeni görünür bir `<label>` elemanı eklenmesi — mevcut `aria-label`
  erişilebilirlik etiketi korunur, ayrı bir görünür label eklenmez
  (kullanıcı onayı alındı).
- Boş/geçersiz istek gönderimini engelleme (Saga task #255'in işi).
- Gerçek gönderim/backend API çağrısı (Saga task #258'in işi).
- Klavye ile tam form gezinme sırası (Saga task #257'nin işi).

## Etkilenen Dosyalar/Modüller (bilinen)
- `ui/src/components/onboarding/OnboardingScreen.tsx` — mevcut
  `request-textarea`'ya `placeholder="Bu klasördeki PDF'leri tarihe göre
  sırala"` attribute'u eklenecek, `.onboarding-textarea` CSS bloğuna
  `::placeholder { color: #9CA3AF; }` eklenecek.

## Rollback Beklentisi
Uygulanmaz (N/A) — salt görsel değişiklik, kalıcı yan etki yok.

## Risks
- Yok — dar kapsamlı, tek dosyalık, saf görsel bir değişiklik.

## Assumptions
- Placeholder metni Saga #254 açıklamasındaki örnekle birebir aynı:
  "Bu klasördeki PDF'leri tarihe göre sırala" (kullanıcı onayı alındı).
- Placeholder rengi `#9CA3AF` (Tailwind gray-400) olarak sabitlenir,
  tarayıcı varsayılanına bırakılmaz (kullanıcı onayı alındı).

## Unknowns
- Yok.

## Sorular ve Cevaplar (ham kayıt)
1. Persona/hedef → #253'ün ATDD'sinden ve DESIGN_DECISIONS.md'den
   (kullanıcı mesajından, tekrar sorulmadı).
2. Placeholder metni ne olacak? → Saga #254 açıklamasındaki örneği
   birebir kullan: "Bu klasördeki PDF'leri tarihe göre sırala".
3. Placeholder'ın düşük kontrast rengi nasıl belirlensin? → `#9CA3AF`
   (gri-400), `::placeholder` ile açıkça set edilir.
4. "Etiket görünür kalmalıdır" ifadesi ne anlama geliyor? → Yeni görünür
   bir `<label>` eklenmez; mevcut `aria-label` erişilebilirlik etiketi
   olarak yerinde kalır, ifade native placeholder davranışını
   (yazınca kaybolma) kastediyor.
5. Test stratejisi oranı? → #253 ile aynı: 20/15/65.
6. Coverage target? → #253 ile aynı: %80.
7. Kabul kriteri sahibi kim? → Otomatik test + kullanıcının (Yusuf)
   görsel onayı (#253 ile aynı).
8. Davranış sözleşmesi satırları uygulanır mı? → Hayır, #253 gibi
   tamamen Uygulanamaz (N/A) — saf görsel/CSS değişikliği.
9. Kapsam dışı onayı → Evet, gerçek gönderim (#258), boş istek
   engelleme (#255), klavye navigasyon sırası (#257) bu round'un
   dışında kalır.
10. Rollback geçerli mi? → Hayır, N/A.
