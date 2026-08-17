# Plan — plan-adimlari-kart (Saga #262)

## Değiştirilecek dosyalar
- **Yeni** `ui/src/components/chat/PlanCard.tsx` — plan adımlarını numaralı/detaylı kartta gösterir.
- **Yeni** `ui/src/components/chat/PlanCard.test.tsx` — 5 unit test.
- **Değişecek** `ui/src/components/chat/ChatScreen.tsx` — `ChatMessage` tipine opsiyonel `plan` alanı eklendi, mesaj `plan` taşıyorsa `PlanCard` render edilir.
- **Değişecek** `ui/src/components/chat/ChatScreen.test.tsx` — 2 entegrasyon testi eklendi.

## Bağımlılıklar
Yeni npm paketi yok.

## Riskler
- Onay/değiştir aksiyonları bu task'ın kapsamı dışında (Saga #263/#264).
