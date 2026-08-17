---
task_slug: plan-validation-wiring
priority: medium
coverage_target: "70/0/30"
performance_target: "yok"
test_strategy: "unit (vitest, mock fetch)"
affected_modules:
  - ui/src/App.tsx
  - ui/src/components/chat/PlanCard.tsx
  - ui/src/components/chat/planValidation.ts
saga_task_id: 281
epic_id: 24
---

# ATDD — validatePlanResponse Wiring (Saga #281)

## Goal
`validatePlanResponse` (Saga #262/#280'de yazılmış ama hiç bağlanmamış)
gerçek backend entegrasyon noktasına (Saga #287'de kurulan `App.tsx`
`/api/plan` çağrısı) bağlanmalı; `PlanStep.operationType` tipi
`string`'den bilinen değerler union'ına sıkılaştırılmalı.

## Sorular ve Cevaplar (saga-oto tarafından otomatik seçildi)

**S1: `KNOWN_OPERATION_TYPES` nerede tanımlı olmalı — `PlanCard.tsx`
mı, `planValidation.ts` mı?** Cevap: `PlanCard.tsx` (PlanStep tipinin
sahibi), `planValidation.ts` oradan import eder + re-export eder
(geriye dönük import uyumluluğu için). Gerekçe: `PlanStep.operationType`
tipini sıkılaştırmak `KNOWN_OPERATION_TYPES`'a bağımlı, tip `PlanCard.
tsx`'te tanımlıyken sabiti `planValidation.ts`'te tutmak dairesel
import'a (circular import) yol açardı. (saga-oto tarafından otomatik
seçildi)

**S2: Doğrulama başarısız olursa (`ok: false`) ne gösterilecek?**
Cevap: Mevcut `planError`/retry mekanizması (Saga #267) — yeni bir
UI deseni icat edilmedi, task açıklamasında zaten bu belirtilmişti.
(saga-oto tarafından otomatik seçildi)

## Kabul Kriterleri
1. **AC-1 (kritik):** `App.tsx`'in `requestPlan`i, backend'den gelen
   ham JSON'u `PlanCard`'a vermeden önce `validatePlanResponse`'tan
   geçiriyor.
2. **AC-2 (kritik):** Doğrulama başarısız olursa `PlanCard` render
   EDİLMİYOR, `planError` set ediliyor (mevcut hata/retry UI'ı devreye
   giriyor).
3. **AC-3 (yüksek):** `PlanStep.operationType` artık
   `(typeof KNOWN_OPERATION_TYPES)[number]` — serbest string kabul
   etmiyor.
4. **AC-4 (yüksek):** Mevcut `PlanCard.test.tsx` testleri (serbest-string
   'İkinci'/'Birinci' test verisi gerçek operationType değerlerine
   çevrilerek) hiçbir davranış regresyonu olmadan geçiyor.

## Riskler / Varsayımlar / Bilinmeyenler
- Gerçek backend'in ürettiği `operationType` değerlerinin
  `KNOWN_OPERATION_TYPES` ile birebir eşleştiği varsayılıyor
  (`backend/models.py: OperationType` enum'u ile karşılaştırıldı,
  eşleşiyor: Taşı/Kopyala/Sil/Yeniden Adlandır/Listele).

## Test Stratejisi
`App.test.tsx`'e geçersiz `operationType` içeren bir 200 yanıtının
`planError`'ı tetikleyip `PlanCard`'ı render etmediğini doğrulayan test;
`PlanCard.test.tsx`'teki serbest-string test verisi düzeltildi.
