# Test Diff — plan-result-kartlari-tasarim
_Red step — implementasyon henüz yok, aşağıdaki yeni testler BAŞARISIZ olması beklenir._

> Not: Codex CLI kotası dolu (Saga skill Bölüm C override). Testler ana
> ajan tarafından değil, `test-copilot`'un kendi normal akışıyla (Haiku
> alt-ajan, `Agent` tool, `model: "haiku"`) yazıldı — bu skill zaten
> Codex'e değil Haiku'ya yönlendiriyor, ek bir istisna gerekmedi.

## Genişletilen Dosyalar

| Dosya | Yeni Test Sayısı |
|---|---|
| `ui/src/components/primitives/Button.test.tsx` | 2 |
| `ui/src/components/chat/PlanCard.test.tsx` | 2 |
| `ui/src/components/chat/ResultCard.test.tsx` | 3 |

## AC Eşlemesi

| Test | Dosya | AC |
|---|---|---|
| `renders Button with danger-outline variant: transparent background, red border and text` | Button.test.tsx | AC-6 |
| `danger-outline variant disabled applies disabled styling while keeping outline style` | Button.test.tsx | AC-6 |
| `plan-card section uses Card primitive background and border styling from tokens` | PlanCard.test.tsx | AC-7 |
| `plan-approve-button uses Button primitive token values for height, padding, borderRadius and fontSize` | PlanCard.test.tsx | AC-4 |
| `result-card section uses Card primitive background and border styling from tokens` | ResultCard.test.tsx | AC-7 |
| `result-revert-button uses danger-outline variant: transparent background, red border and text` | ResultCard.test.tsx | AC-6 |
| `result-revert-confirm-button uses danger variant: red background, white text` | ResultCard.test.tsx | AC-6 |

## Dokunulmayan (korunan) mevcut testler
`PlanCard.test.tsx:118` (`toHaveClass('plan-card-approve-btn')`) dahil tüm mevcut testler değiştirilmedi — plan.md Karar 2 gereği.

## Varsayımlar
- Testler şu an RED: `Button.tsx` henüz `danger-outline` variant'ını desteklemiyor, `PlanCard.tsx`/`ResultCard.tsx` henüz `Card`/`Button` primitiflerini kullanmıyor.
- Token import yolu tüm dosyalarda `../../tokens` (mevcut Button.test.tsx deseniyle tutarlı).

## Sıradaki adım
`code-copilot` — bu testleri yeşile çeviren implementasyonu yazacak (Button.tsx'e `danger-outline` variant eklemek + PlanCard.tsx/ResultCard.tsx'i primitiflere taşımak).
