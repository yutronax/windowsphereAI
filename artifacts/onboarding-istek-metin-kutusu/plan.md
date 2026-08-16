# Plan — onboarding-istek-metin-kutusu
_Reference: atdd.md_

## Files to Modify
| File | Why | Risk |
|------|-----|------|
| `ui/src/components/onboarding/OnboardingScreen.tsx` | AC-1..AC-4: yeni `requestText` state'i + textarea JSX'i + `.onboarding-textarea` CSS class'ı (task #251/#252'nin `onboarding-*` konvansiyonunu takip eder) eklenecek | low — mevcut hiçbir davranışı değiştirmiyor, sadece klasör yolu gösteriminden sonra yeni bir eleman ekliyor |
| `ui/src/components/onboarding/OnboardingScreen.test.tsx` | AC-1..AC-4 için yeni testler eklenecek | low |
| `ui/e2e/onboarding.spec.ts` | Focus/blur/yazma senaryoları için yeni e2e testler eklenecek | low |

**Not (görsel regresyon):** `OnboardingScreen.tsx` rendered bir web UI
dosyası — `verify` adımında gate 12 aktif çalışmalı.

## New Files
(Yok — mevcut dosyaya, task #251/#252'nin kurduğu emsale uygun ekleniyor.)

## Dependencies
- Task #251'in `.onboarding-primary-btn` ve task #252'nin `.onboarding-path`
  CSS class deseni — yeni `.onboarding-textarea` class'ı aynı `<style>`
  bloğunda, aynı `onboarding-*` konvansiyonuyla eklenmeli.
- Mevcut `selectedFolder`/`backendStatus` state'leri korunuyor, yeni
  `requestText` state'i bunlardan bağımsız.

## Migration Required?
Hayır.

## Risks
(atdd.md'den taşındı) Bu task'ın orijinal epic kırılımındaki (#254/#255/#258)
task'lar "metin kutusu zaten var" varsayımıyla yazılmıştı — bu task o
boşluğu dolduruyor, sonraki task'lar bu task'ın kurduğu `requestText` state
adını referans almalı.

## Open Questions
(Yok — atdd.md açık noktayı Unknowns'a taşıdı: textarea'nın backend hazır
olmadan disabled olup olmayacağı, bu round'da disabled UYGULANMIYOR,
bilinçli karar.)
