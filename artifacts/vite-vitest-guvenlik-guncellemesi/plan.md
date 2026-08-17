# Plan — vite-vitest-guvenlik-guncellemesi
_Reference: atdd.md_

## Files to Modify
| File | Why | Risk |
|------|-----|------|
| package.json | `npm audit fix --force` çalıştırıldığında vite/vitest ve zincirdeki paketler (major sürüm) güncellenecek. | high |
| package-lock.json | Otomatik güncellenecek. | low |
| vite.config.ts | Yükseltme breaking change içeriyorsa (API değişikliği) uyumluluk için düzeltilebilir. | medium |
| playwright.config.ts | Gerekirse (vite dev server entegrasyonu değiştiyse) kontrol edilip düzeltilebilir. | low |

## New Files
Yok.

## Dependencies
Bu değişiklik tüm frontend build/test zincirini etkiliyor — sıralı doğrulama gerekiyor: `npm audit fix --force` → `npx tsc --noEmit` → `npx vitest run` → `npm run build` → `npx playwright test`. Herhangi biri kırmızıysa önce onu düzelt, sıradakine geçme.

## Migration Required?
No.

## Risks
atdd.md'den taşındı — 3 major sürüm atlaması (vite 5→8), vitest'in de büyük olasılıkla eşlik etmesi gerekecek, `@vitejs/plugin-react`/`jsdom`/`@testing-library/react` uyumluluğu doğrulanmalı.

## Open Questions
Yok.
