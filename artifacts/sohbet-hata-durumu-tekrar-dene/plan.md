# Plan — Hata durumu + Tekrar dene (Saga #267)

## Değiştirilecek dosya
- `ui/src/components/chat/ChatScreen.tsx`
  - `Props`'a `planError?: string | null` (varsayılan `null`) ve
    `onRetry?: () => void` eklenir.
  - `isGeneratingPlan` göstergesinden hemen önce/sonra koşullu bir hata
    göstergesi: `planError && !isGeneratingPlan` iken render edilir.
    `data-testid="plan-error-indicator"`, `role="alert"`, içinde hata
    metni + `data-testid="plan-retry-button"` "Tekrar dene" düğmesi
    (`onClick={() => onRetry?.()}`).
  - textarea/gönder düğmesi disabled mantığı DEĞİŞMEZ (sadece
    `isGeneratingPlan`'a bağlı kalır, `planError`'a bağlı değil).

## Yeni bağımlılık yok

## Riskler
- `planError` ve `isGeneratingPlan` aynı anda true olursa (misuse):
  yükleniyor göstergesi önceliklidir, hata göstergesi bastırılır.
