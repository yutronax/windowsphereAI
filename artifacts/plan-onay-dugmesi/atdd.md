---
task_slug: plan-onay-dugmesi
priority: high
coverage_target: "AC'lerin tamamı unit test ile kapsanır"
performance_target: "yok (UI katmanı)"
test_strategy: "70/0/30 (unit/integration/e2e) — mevcut vitest+RTL altyapısı"
affected_modules: ["ui/src/components/chat/PlanCard.tsx"]
---

# Plan onay düğmesini yalnızca güvenlikten geçen plan için etkinleştir (Saga #263)

## Persona
Plan kartını gören, dosya operasyonunu onaylamak/reddetmek üzere olan kullanıcı.

## Goal
Birincil "Planı onayla" düğmesi 44px min yükseklik ve belirgin odak durumuna sahip
olmalı; security katmanı reddederse düğme devre dışı kalmalı ve ret nedeni görünmeli.

## User Story
Bir kullanıcı olarak, güvenlik kontrolünden geçmemiş bir planı yanlışlıkla
onaylayamamalıyım; reddedilme sebebini görüp anlamalıyım.

## Acceptance Criteria
1. `PlanCard`, plan'ın güvenlik durumunu (`securityStatus: 'approved' | 'rejected'`)
   opsiyonel olarak alır.
2. `securityStatus` belirtilmemişse (backend henüz güvenlik kararı vermemişse) onay
   düğmesi gösterilir ve etkindir (varsayılan: mevcut davranışı bozma).
3. `securityStatus === 'rejected'` ise onay düğmesi `disabled` olur ve
   `rejectionReason` metni (varsa) `aria-live="polite"` bölgede görünür.
4. `securityStatus === 'approved'` ise düğme etkindir.
5. Düğme 44px min-height, `:focus-visible` belirgin outline taşır (OnboardingScreen'deki
   `.onboarding-primary-btn` konvansiyonuyla tutarlı).
6. Onaylandığında `onApprove` callback'i çağrılır.

## Behaviour-contract tablosu
| Durum | Buton | Ret nedeni |
|---|---|---|
| `securityStatus` yok | etkin | gösterilmez |
| `approved` | etkin | gösterilmez |
| `rejected`, `rejectionReason` var | disabled | gösterilir (aria-live) |
| `rejected`, `rejectionReason` yok | disabled | genel "Bu plan güvenlik kontrolünden geçemedi." metni gösterilir |

## Risks/Assumptions/Unknowns
- Assumption: "Planı değiştir" düğmesi bu task'ın kapsamı DIŞINDA (Saga #264).
  (saga-oto tarafından otomatik seçildi — dar kapsam)
- Assumption: Backend'den security kararı gelene kadar `securityStatus` alanı
  opsiyonel bırakılıp geriye dönük uyumluluk korundu (mevcut PlanCard testleri
  kırılmaz). (saga-oto otomatik seçildi)

## Test Strategy
70/0/30. `PlanCard.test.tsx`'e 5 yeni test eklendi.

## Benchmark
`npx vitest run` tüm testler yeşil.

## Sorular ve Cevaplar (saga-oto otomatik)
- S: "Planı değiştir" düğmesi de eklensin mi? C: Hayır, Saga #264 kapsamında,
  dar kapsam ilkesi. (saga-oto tarafından otomatik seçildi)
