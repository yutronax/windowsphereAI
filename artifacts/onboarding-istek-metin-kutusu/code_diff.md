# Code Diff — onboarding-istek-metin-kutusu
_efektor subagent tarafından yazıldı (Codex kotası tükendiği için), GREEN adımı._

## Değiştirilen Dosya
| Dosya | Değişiklik |
|---|---|
| `ui/src/components/onboarding/OnboardingScreen.tsx` | `requestText` state'i + `.onboarding-textarea` CSS class'ı + textarea JSX'i eklendi |

## Acceptance Criteria Kapsamı
- **AC-1** ✅ — `min-height:120px; border-radius:12px; border:1px solid #E5E7EB; font-size:16px; padding:16px`.
- **AC-2** ✅ — Controlled component (`value={requestText}`, `onChange` ile `setRequestText`).
- **AC-3** ✅ — `:focus { border-color:#2563EB; box-shadow:0 0 0 3px rgba(37,99,235,0.1); }`.
- **AC-4** ✅ — Blur'da varsayılan `#E5E7EB` kenarlığa dönüş (CSS `:focus` kuralı kalkınca doğal olarak).

## CAVEMAN İncelemesi
- 1 dosya değiştirildi, yeni dosya yok.
- Task #251/#252'nin `onboarding-*` class konvansiyonu takip edildi.
- Textarea bilinçli olarak disabled yapılmadı (atdd.md Unknowns — ayrı karar).

## Red-team Sonrası Düzeltme (efektor)
obss-red-team incelemesi 2 MEDIUM bulgu buldu, ikisi de düzeltildi:
- **A11y eksikliği:** textarea'ya `aria-label="Dosya işlemi isteği"` eklendi.
- **Width/box-sizing eksikliği:** `.onboarding-textarea` class'ına
  `width:100%; box-sizing:border-box;` eklendi (padding'in genişliğe dahil
  olması, native dar varsayılan genişlik riskinin giderilmesi için).

## Final Test Durumu
- `npx vitest run` → 15/15 PASS
- `npx playwright test` → 11/11 PASS (2 kez tekrarlandı, flaky değil)
- `npm run build` → hatasız

## Sıradaki Adım
`verify` — gate'lerin tamamı tekrar gerçek çalıştırmayla doğrulanacak.
