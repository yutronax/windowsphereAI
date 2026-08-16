# Test Diff — onboarding-birincil-buton-stili
_efektor subagent tarafından yazıldı (Codex kotası tükendiği için), RED adımı._

## Eklenen Testler

| Dosya | Yeni test sayısı | Hedef AC |
|---|---|---|
| `ui/src/components/onboarding/OnboardingScreen.test.tsx` | 3 (AC-1, AC-3, AC-5) | Enabled computed style, disabled computed style, WCAG kontrast hesabı |
| `ui/e2e/onboarding.spec.ts` | 2 (AC-2, AC-4) | Klavye odak halkası, hover/active renk geçişi |

## Gerçek Çalıştırma Sonucu (implementasyon öncesi, beklenen RED)
- `npx vitest run`: 12 test, **10 PASS, 2 FAIL** (AC-1, AC-3 — implementasyon yok). AC-5 zaten implementasyondan bağımsız saf bir WCAG hesaplama testi olduğu için PASS (bu normal, "red" kavramı bu AC'ye uygulanmıyor). Eski 9 test (6 OnboardingScreen + 3 backendHealth) bozulmadı.
- `npx playwright test`: 7 test, **5 PASS, 2 FAIL** (AC-2, AC-4 — implementasyon yok). Eski 5 e2e testi bozulmadı.

## AC → Test Mapping
1. AC-1 (enabled stil) → `OnboardingScreen.test.tsx` yeni test → **FAIL (beklenen)**
2. AC-2 (odak halkası) → `onboarding.spec.ts` yeni test → **FAIL (beklenen)**
3. AC-3 (disabled stil) → `OnboardingScreen.test.tsx` yeni test → **FAIL (beklenen)**
4. AC-4 (hover/active) → `onboarding.spec.ts` yeni test → **FAIL (beklenen)**
5. AC-5 (WCAG kontrast) → `OnboardingScreen.test.tsx` yeni test → **PASS** (implementasyondan bağımsız hesaplama)

## Sıradaki Adım
`code-copilot` — `OnboardingScreen.tsx`'teki "Klasör Seç" butonuna inline
style eklenerek AC-1..AC-4 testleri yeşile çevrilecek.
