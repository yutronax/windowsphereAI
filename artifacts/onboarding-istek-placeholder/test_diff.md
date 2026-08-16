# Test Diff — onboarding-istek-placeholder

> **Not:** Codex CLI kotası 15 Eylül 2026'ya kadar dolu olduğu için (canlı
> hata: `ERROR: You've hit your usage limit`), kullanıcı onayıyla bu dar
> kapsamlı görev için testler istisnai olarak Claude tarafından yazıldı
> (test-copilot'un normal kuralı: testler Codex'ten gelir). code-copilot
> adımı da aynı istisna kapsamında Claude tarafından yürütüldü.

## Değiştirilen Test Dosyaları

### `ui/src/components/onboarding/OnboardingScreen.test.tsx`
Yeni `describe('request textarea placeholder (onboarding-istek-placeholder)')`
bloğu eklendi (mevcut testlere dokunulmadı):
- `shows the guiding placeholder text with a muted #9CA3AF color when empty (AC-1)`
- `keeps the placeholder attribute intact while the user types — the browser hides it natively (AC-2)`
- `clears the typed value back to empty so the placeholder is visible again (AC-3)`

### `ui/e2e/onboarding.spec.ts`
Mevcut `test.describe('first-run folder onboarding')` bloğunun sonuna 3 yeni
test eklendi (mevcut testlere dokunulmadı):
- `shows the guiding placeholder text with a muted color on the empty request textarea (AC-1)` — placeholder attribute + `::placeholder` rengi (`rgb(156, 163, 175)`).
- `hides the placeholder once the user starts typing into the request textarea (AC-2)`
- `shows the placeholder again after the typed text is fully cleared (AC-3)`

AC-4 (focus/blur regresyonu) için ayrı bir yeni test yazılmadı — plan.md'de
belirtildiği gibi mevcut `shows a focus border...` / `reverts the request
textarea border...` testleri (satır ~132-156) zaten regresyon garantisi
sağlıyor; placeholder eklendikten sonra da geçtikleri doğrulandı (bkz.
verify_report.md).

## Kırmızı → Yeşil Doğrulaması
1. Testler yazıldıktan hemen sonra, implementasyon eklenmeden önce
   `npx vitest run` çalıştırıldı: 3 yeni test **fail** (`expected '' to be
   'Bu klasördeki PDF'leri tarihe göre sırala'`), 15 mevcut test geçti
   (kırmızı adım doğrulandı).
2. `OnboardingScreen.tsx`'e `placeholder` attribute + `::placeholder` CSS
   kuralı eklendikten sonra `npx vitest run`: **18/18 geçti**.
3. `npx playwright test onboarding.spec.ts`: **14/14 geçti** (3 yeni + 11
   mevcut, regresyon yok).
