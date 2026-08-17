# Plan — Yükleniyor durumu (Saga #265)

## Değiştirilecek dosya
- `ui/src/components/chat/ChatScreen.tsx`
  - `Props`'a `isGeneratingPlan?: boolean` eklenir (varsayılan `false`).
  - Mesaj listesinden sonra, yazma alanından önce koşullu bir gösterge:
    `data-testid="plan-loading-indicator"`, `aria-live="polite"`,
    içinde "Plan hazırlanıyor…" metni + 3 nokta (`<span>` x3,
    `.plan-loading-dot` class'ı, CSS keyframe animasyonu).
  - `@media (prefers-reduced-motion: reduce)` ile `.plan-loading-dot`
    animasyonu `animation: none` yapılır.
  - textarea: `disabled={isGeneratingPlan}` eklenir.
  - gönder düğmesi: `disabled={draft.trim() === '' || isGeneratingPlan}`.

## Yeni bağımlılık yok
Saf CSS keyframe + React state/props yeterli.
