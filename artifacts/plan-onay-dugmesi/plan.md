# Plan — plan-onay-dugmesi (Saga #263)

## Değiştirilecek dosyalar
- **Değişecek** `ui/src/components/chat/PlanCard.tsx` — Plan tipine `securityStatus`/`rejectionReason` eklendi, "Planı onayla" düğmesi eklendi (44px, focus-visible, security rejected ise disabled).
- **Değişecek** `ui/src/components/chat/PlanCard.test.tsx` — 5 yeni test.

## Bağımlılıklar
Yok.

## Riskler
- "Planı değiştir" düğmesi kapsam dışı (Saga #264).
