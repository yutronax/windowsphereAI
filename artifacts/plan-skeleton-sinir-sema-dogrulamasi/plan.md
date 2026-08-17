# Plan — Boundary şema doğrulaması (Saga #280)

## Yeni dosya
- `ui/src/components/chat/planValidation.ts`
  - `KNOWN_OPERATION_TYPES = ['Taşı', 'Kopyala', 'Sil', 'Yeniden Adlandır', 'Listele'] as const`
  - `export type PlanValidationResult = { ok: true; plan: Plan } | { ok: false; error: string }`
  - `export function validatePlanResponse(data: unknown): PlanValidationResult`
    - `data` obje değilse veya `steps` bir dizi değilse reddet.
    - Her `steps[i]` için: `order` (Number.isInteger, >=0), `operationType`
      (KNOWN_OPERATION_TYPES içinde), `targetFolder` (non-empty string),
      `affectedFileCount` (Number.isInteger, >=0) kontrolü. İlk hata
      bulunduğunda dizin bilgisiyle birlikte hata mesajı döner.
    - `order` tekilliği: bir `Set` ile tüm adımlar toplandıktan sonra
      kontrol edilir.
    - `securityStatus` opsiyonel — varsa `'approved'|'rejected'` olmalı.
    - `rejectionReason` opsiyonel — varsa string olmalı.
    - Tümü geçerliyse `{ ok: true, plan: { steps, securityStatus?,
      rejectionReason? } }` döner (yeni bir obje kopyalanarak, girdi
      referansı değil).

## Yeni test dosyası
- `ui/src/components/chat/planValidation.test.ts`

## Yeni bağımlılık yok
El yazımı saf fonksiyon.
