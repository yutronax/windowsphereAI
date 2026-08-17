---
task_slug: plan-hazirlaniyor-yukleniyor-durumu
priority: high
coverage_target: "AC'lerin tamamı unit test ile kapsanır"
performance_target: "yok (UI katmanı)"
test_strategy: "70/0/30 (unit/integration/e2e) — mevcut vitest+RTL altyapısı"
affected_modules: ["ui/src/components/chat/ChatScreen.tsx"]
---

# Plan üretilirken gönderimi kilitleyen yükleniyor durumunu göster (Saga #265)

## Persona
Bir mesaj gönderip asistanın plan üretmesini bekleyen kullanıcı.

## Goal
Asistan tarafında hareket azaltma tercihine saygılı bir üç nokta göstergesi ve
"Plan hazırlanıyor…" metni görünmeli; aynı isteğin iki kez gönderilmesini
önlemek için giriş alanı ve gönder düğmesi işlem bitene kadar devre dışı kalmalı.

## User Story
Bir kullanıcı olarak, mesajımı gönderdikten sonra asistanın plan ürettiğini
görsel olarak anlayabilmek ve bu süreçte yanlışlıkla ikinci bir istek
göndermemek istiyorum.

## Acceptance Criteria (öncelik sırasına göre)
1. `isGeneratingPlan` true olduğunda mesaj listesinin altında bir yükleniyor
   göstergesi görünür: "Plan hazırlanıyor…" metni + üç nokta animasyonu.
2. `prefers-reduced-motion: reduce` tercihine saygı gösterilir — animasyon
   CSS `@media (prefers-reduced-motion: reduce)` ile durdurulur, metin
   her durumda görünür kalır.
3. `isGeneratingPlan` true iken yazma alanı (textarea) VE gönder düğmesi
   devre dışı kalır — kullanıcı aynı isteği ikinci kez gönderemez.
4. `isGeneratingPlan` false/verilmemiş iken göstergenin görünmediği ve
   giriş alanının normal (draft'a göre) davranmaya devam ettiği doğrulanır
   (regresyon: Saga #259/#264 davranışları bozulmamalı).
5. Gösterge `aria-live="polite"` bir bölgede duyurulur (ekran okuyucu).

## Behaviour-contract tablosu
| Durum | Beklenen davranış |
|---|---|
| `isGeneratingPlan=true` | Gösterge görünür, textarea disabled, gönder butonu disabled |
| `isGeneratingPlan=false` (varsayılan) | Gösterge yok, mevcut davranış korunur |
| `isGeneratingPlan=true` iken Enter'a basılır | Mesaj gönderilMEZ (textarea zaten disabled, onKeyDown React'ta tetiklenmez) |
| `prefers-reduced-motion: reduce` | Animasyon durur, "Plan hazırlanıyor…" metni yine görünür |

## Risks/Assumptions/Unknowns
- Assumption: `isGeneratingPlan` bu task'ta bir prop olarak DIŞARIDAN
  kontrol edilir (parent/App bileşeni gerçek backend isteğinin durumunu
  yönetecek) — ChatScreen kendi içinde bir HTTP çağrısı yapmıyor, bu
  backend/LLM entegrasyonu henüz yok (dar kapsam ilkesi, #259/#264 ile
  aynı desen). (saga-oto tarafından otomatik seçildi)
- Assumption: Gösterge, mesaj listesinin ALTINDA (yazma alanının hemen
  üstünde) render edilir — ayrı bir "asistan mesajı" olarak listeye
  eklenmez, çünkü henüz gerçek bir asistan mesajı yok. (saga-oto
  tarafından otomatik seçildi)

## Test Strategy
70/0/30 unit/integration/e2e. `ChatScreen.test.tsx`'e yeni testler.

## Benchmark
Kabul kriteri: `npx vitest run` içinde tüm testler yeşil.

## Sorular ve Cevaplar (saga-oto otomatik)
- S: `isGeneratingPlan` state'i ChatScreen içinde mi yönetilir? C: Hayır,
  dışarıdan prop olarak alınır — gerçek plan üretimi backend/LLM
  entegrasyonu bu task'ın kapsamı DIŞINDA. (saga-oto tarafından otomatik
  seçildi)
- S: Erişilebilirlik için animasyon nasıl durdurulur? C: CSS
  `@media (prefers-reduced-motion: reduce)` ile — düşük maliyetli,
  yüksek değerli, projede zaten kabul edilen bir ilke (bkz. task
  açıklaması). (saga-oto tarafından otomatik seçildi)
