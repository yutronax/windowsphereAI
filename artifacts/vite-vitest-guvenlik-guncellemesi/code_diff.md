# Code Diff — vite-vitest-guvenlik-guncellemesi
_Reference: atdd.md, plan.md_

## Değiştirilen Dosyalar
`package.json` / `package-lock.json` — `npm audit fix --force` çalıştırıldı:
- `vite`: `^5.4.10` → `^8.2.1` (3 major sürüm)
- `vitest`: `^2.1.9` → `^4.1.10` (2 major sürüm)
- İlişkili paketler (`@vitest/mocker`, `vite-node`) otomatik güncellendi.
- `@vitejs/plugin-react@4.7.0` (peer dependency uyarısı verdi — `vite@^4.2.0 || ^5.0.0 || ^6.0.0 || ^7.0.0` bekliyor, `vite@8`'i henüz resmi peer listesinde değil) ama pratikte hatasız çalıştı (test kanıtı aşağıda).

Kod tarafında HİÇBİR dosya değişmedi — bu saf bir bağımlılık güncellemesi.

## Doğrulama (tüm mevcut regresyon testleri, yeni test YAZILMADI — atdd.md ile tutarlı)
- `npm audit` → **0 vulnerabilities** (AC-1).
- `npx tsc --noEmit` → hatasız.
- `npx vitest run` → **42/42 geçti** (AC-2). Yeni deprecation uyarıları var (`configLoader: 'native'`, `esbuild`→`oxc` geçişi öneriliyor) ama hiçbiri hataya dönüşmüyor.
- `npm run build` → başarılı (AC-4).
- `npx playwright test ui/e2e/onboarding.spec.ts` → **26/26 geçti** (AC-3). Bir testte (AC-1 placeholder testi) konsola zararsız bir "Unhandled rejection: Cannot read properties of undefined (reading 'invoke')" uyarısı düşüyor — bu, Tauri mock'lanmadan gerçek tarayıcıda `chooseFolder` denendiğinde beklenen bir durum, yükseltmeden ÖNCE de vardı (ilgisiz, test zaten pass), yükseltmenin getirdiği yeni bir regresyon değil.
- `"../.venv/Scripts/python.exe" -m pytest backend/tests/ -v` → **13/13 geçti** (backend npm'e bağımlı değil, etkilenmedi ama tam regresyon için çalıştırıldı).

## AC-5 Notu
Hiçbir uygulama davranışı değiştirilmedi — sadece `package.json`/`package-lock.json`. Config dosyalarında (`vite.config.ts`, `playwright.config.ts`) da değişiklik gerekmedi, mevcut haliyle vite 8/vitest 4 ile uyumlu çalıştı.
