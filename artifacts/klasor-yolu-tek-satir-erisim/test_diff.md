# Test Diff — klasor-yolu-tek-satir-erisim
_efektor subagent tarafından yazıldı (Codex kotası tükendiği için), RED adımı._

## Yapılan Değişiklikler
- `OnboardingScreen.test.tsx`: `truncateWindowsPath` import'u ve kendi
  `describe` bloğu kaldırıldı (fonksiyon implementasyon adımında
  kaldırılacak, testi artık anlamsız — ölü kod temizliği).
- `OnboardingScreen.test.tsx`: AC-1 (CSS truncation computed style) ve AC-4
  (kısa yolda tam metin) için yeni testler eklendi.
- `onboarding.spec.ts`: AC-2 (Tab-focus tooltip) ve AC-3 (hover tooltip)
  için yeni testler eklendi, `data-testid="folder-path-tooltip"` konvansiyonu
  seçildi.
- `onboarding.spec.ts` satır ~34'teki mevcut `toHaveText` assertion'ına
  dokunulmadı.

## Gerçek Çalıştırma Sonucu (implementasyon öncesi, beklenen RED)
- `npx vitest run`: 13 test, **12 PASS, 1 FAIL** (AC-1). AC-4 zaten PASS
  (text content zaten tam, JS kesme hiç olmadığı için doğal olarak geçiyor
  — bu normal, "red" kavramı bu AC'ye kısmen uygulanmıyor).
- `npx playwright test`: 9 test, **7 PASS, 2 FAIL** (AC-2, AC-3). Eski 7
  test (satır ~34'teki `toHaveText` dahil) bozulmadı.

## AC → Test Mapping
1. AC-1 (CSS tek satır kesme) → `OnboardingScreen.test.tsx` yeni test → **FAIL (beklenen)**
2. AC-2 (klavye tooltip) → `onboarding.spec.ts` yeni test → **FAIL (beklenen)**
3. AC-3 (hover tooltip) → `onboarding.spec.ts` yeni test → **FAIL (beklenen)**
4. AC-4 (kısa yol, kesme yok) → `OnboardingScreen.test.tsx` yeni test → **PASS** (implementasyondan bağımsız zaten doğru)

## Sıradaki Adım
`code-copilot` — `OnboardingScreen.tsx`'te `truncateWindowsPath` kaldırılıp
CSS truncation + tooltip mantığı eklenerek AC-1/AC-2/AC-3 testleri yeşile
çevrilecek.
