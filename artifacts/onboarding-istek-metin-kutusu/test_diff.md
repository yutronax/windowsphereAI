# Test Diff — onboarding-istek-metin-kutusu
_efektor subagent tarafından yazıldı (Codex kotası tükendiği için), RED adımı._

## Eklenen Testler
- `OnboardingScreen.test.tsx`: AC-1 (computed style: min-height/border-radius/border-color), AC-2 (controlled component — yazılan metin state'e yansır).
- `onboarding.spec.ts`: AC-3 (focus stili), AC-4 (blur sonrası eski stile dönüş).

**Seçilen selector:** `data-testid="request-textarea"` — implementasyon adımında aynısı kullanılacak.

## Gerçek Çalıştırma Sonucu (implementasyon öncesi, beklenen RED)
- `npx vitest run`: 12 test, **10 PASS, 2 FAIL** (AC-1, AC-2 — textarea DOM'da yok).
- `npx playwright test`: 11 test, **9 PASS, 2 FAIL** (AC-3, AC-4 — locator bulunamadı, 30sn timeout, beklenen).

## AC → Test Mapping
1. AC-1 (textarea + stil) → `OnboardingScreen.test.tsx` → **FAIL (beklenen)**
2. AC-2 (state bağlama) → `OnboardingScreen.test.tsx` → **FAIL (beklenen)**
3. AC-3 (focus stili) → `onboarding.spec.ts` → **FAIL (beklenen)**
4. AC-4 (blur) → `onboarding.spec.ts` → **FAIL (beklenen)**

## Sıradaki Adım
`code-copilot` — `OnboardingScreen.tsx`'e `data-testid="request-textarea"`
ile textarea eklenip 4 AC yeşile çevrilecek.
