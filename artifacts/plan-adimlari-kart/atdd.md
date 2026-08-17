---
task_slug: plan-adimlari-kart
priority: high
coverage_target: "AC'lerin tamamı unit test ile kapsanır"
performance_target: "yok (UI katmanı)"
test_strategy: "70/0/30 (unit/integration/e2e) — mevcut vitest+RTL altyapısı"
affected_modules: ["ui/src/components/chat/PlanCard.tsx", "ui/src/components/chat/ChatScreen.tsx"]
---

# Plan adımlarını numaralı ve dosya etkisini belirten kartta göster (Saga #262)

## Persona
Sohbet ekranında bir dosya operasyonu isteyen kullanıcı; asistan bir plan-skeleton
döndürdüğünde onaylamadan önce kapsamı görmek istiyor.

## Goal
LLM plan-skeleton yanıtındaki her adım; sıra numarası, işlem türü, hedef klasör ve
etkilenecek dosya sayısıyla bir kartta gösterilmeli.

## User Story
Bir kullanıcı olarak, asistanın önerdiği planı onaylamadan önce hangi adımların
hangi sırayla, hangi klasörde, kaç dosyayı etkileyeceğini net biçimde görmek
istiyorum, böylece bilinçli onay verebilirim.

## Acceptance Criteria (öncelik sırasına göre)
1. Plan içeren bir asistan mesajı geldiğinde, mesaj metninin yanında/altında bir
   "plan kartı" render edilir.
2. Her adım: sıra numarası (1, 2, 3...), işlem türü (ör. "Taşı", "Kopyala", "Sil"),
   hedef klasör, etkilenecek dosya sayısı ("N dosya") gösterir.
3. Adımlar plan'daki sırayla (order alanına göre) listelenir.
4. Plan kartı erişilebilir bir liste yapısı (ol/li, ordered) kullanır — ekran
   okuyucu adım sırasını doğal olarak duyurabilir.
5. Onay/değiştir düğmeleri bu task'ın KAPSAMI DIŞINDA (Saga #263/#264'te ele
   alınacak) — sadece görüntüleme.

## Behaviour-contract tablosu
| Durum | Beklenen davranış |
|---|---|
| Mesajda `plan` yok | PlanCard render edilmez |
| `plan.steps` boş dizi | Kart render edilir ama adım listesi boş (hata yok) |
| Çok adımlı plan | Adımlar `order` alanına göre sıralı gösterilir |
| `affectedFileCount: 0` | "0 dosya" olarak gösterilir (gizlenmez) |

## Risks/Assumptions/Unknowns
- Assumption: Plan verisinin backend'den nasıl geleceği (gerçek LLM entegrasyonu)
  bu task'ın kapsamı dışında — component sadece verilen `Plan` tipini render eder,
  mock/sabit veriyle test edilir. (saga-oto tarafından otomatik seçildi — dar kapsam)
- Assumption: `operationType` insan-okunur Türkçe metin olarak zaten backend'den
  gelir varsayıldı (ör. "Taşı"), component bir çeviri/mapping katmanı eklemez —
  gelecekte enum→etiket haritası gerekirse ayrı task. (saga-oto otomatik seçildi,
  dar kapsam ilkesi)

## Test Strategy
70/0/30 unit/integration/e2e. Yeni: `PlanCard.test.tsx` + `ChatScreen.test.tsx`'e
plan-entegrasyonu için 1-2 ek test.

## Benchmark
Kabul kriteri: `npx vitest run` içinde tüm testler yeşil.

## Sorular ve Cevaplar (saga-oto otomatik)
- S: Onay/değiştir butonları bu task'a dahil mi? C: Hayır, ayrı task'lar
  (#263/#264) var, dar kapsam ilkesiyle sadece görüntüleme yapılır. (saga-oto
  tarafından otomatik seçildi)
