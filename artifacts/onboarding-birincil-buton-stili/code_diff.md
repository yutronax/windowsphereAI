# Code Diff — onboarding-birincil-buton-stili
_efektor subagent tarafından yazıldı (Codex kotası tükendiği için), GREEN adımı._

## Değiştirilen Dosya

| Dosya | Değişiklik |
|---|---|
| `ui/src/components/onboarding/OnboardingScreen.tsx` | "Klasör Seç" butonuna component içine gömülü `<style>` bloğu + `.onboarding-primary-btn` CSS class'ı eklendi (gerçek `:hover`/`:active`/`:focus-visible`/`:disabled` pseudo-class'ları kullanıldı — inline style ile mümkün olmayan durumlar için tek, tutarlı bir yöntem) |

## Acceptance Criteria Kapsamı
- **AC-1** ✅ — `height:44px`, `border-radius:8px`, `background-color:#2563EB`, `color:#fff`.
- **AC-2** ✅ — `:focus-visible { outline: 2px solid #1E40AF; outline-offset: 2px; }`.
- **AC-3** ✅ — `:disabled { background-color:#94A3B8; cursor:not-allowed; }`.
- **AC-4** ✅ — `:hover:not(:disabled)` → `#1D4ED8`, `:active:not(:disabled)` → `#1E40AF`.
- **AC-5** ✅ — WCAG kontrast testi implementasyondan bağımsız olarak zaten geçiyordu (sabit renk değerleri doğru seçilmiş).

## CAVEMAN İncelemesi
- 1 dosya değiştirildi, yeni dosya yok.
- Tek yöntem (CSS class + gerçek pseudo-class'lar) hem enabled/disabled hem
  hover/active/focus-visible durumlarını çözdü — React state ile hover/active
  taklit etme gibi daha karmaşık bir yaklaşım kullanılmadı.
- Mevcut `chooseFolder`/`disabled={!isReady}` mantığı bozulmadı.

## Bulunan ve Düzeltilen Yan Sorun
İlk implementasyon turunda AC-2'nin e2e testi 3/3 deterministik FAIL verdi —
kök neden implementasyon değil, `ui/e2e/onboarding.spec.ts`'teki testin
`page.goto('/')` sonrası hiç beklemeden Tab basması, `App.tsx`'in async
config/health zinciriyle yarışmasıydı. Ayrı bir efektor turu ile testin
kendisine (SADECE bu testin içine) bir `toBeEnabled()` bekleme adımı
eklendi, 3 ardışık koşuda 7/7 stabil PASS doğrulandı.

## Final Test Durumu
- `npx vitest run` → 12/12 PASS
- `npx playwright test` → 7/7 PASS (3 kez tekrarlandı, flaky değil)
- `npm run build` → hatasız

## Sıradaki Adım
`verify` — gate'lerin tamamı tekrar gerçek çalıştırmayla doğrulanacak.
