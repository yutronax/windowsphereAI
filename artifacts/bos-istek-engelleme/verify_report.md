# Verify Report — bos-istek-engelleme
_Reference: atdd.md, code_diff.md, test_diff.md_

## Verification Gates
| # | Gate | Result | Evidence / Reason |
|---|------|--------|--------------------|
| 1 | Dosya konumu | PASS | `git status --short -- ui/` → tam olarak code_diff.md/test_diff.md'nin listelediği 3 dosya değişmiş: `ui/e2e/onboarding.spec.ts`, `ui/src/components/onboarding/OnboardingScreen.test.tsx`, `ui/src/components/onboarding/OnboardingScreen.tsx`. |
| 2 | Build/derleme | PASS | `npm run build` (`tsc --noEmit && vite build`, package.json'daki kanonik komut) → `✓ built in 590ms`, hatasız. |
| 3 | Supabase şema/canlı doğrulama | N/A | code_diff.md hiçbir Supabase çağrısı/migration dosyası içermiyor — saf client-side React state değişikliği. |
| 4 | Lint | N/A | Repo'da `.eslintrc*`/`eslint.config.*`/`.prettierrc*` yok, package.json'da `lint`/`format` script'i tanımlı değil — proje linter/formatter tanımlamıyor. |
| 5 | Type check | PASS | `npx tsc --noEmit` → çıktı yok, hatasız (gate 2'nin build komutuna zaten dahil, ayrıca doğrulandı). |
| 6 | Unit testler | PASS | `npx vitest run ui/src/components/onboarding/OnboardingScreen.test.tsx` → **21 passed (21)**. AC-1..AC-6 hepsi kapsanıyor (bkz. aşağıdaki AC→Test eşlemesi). |
| 7 | E2E testler | PASS | `npx playwright test ui/e2e/onboarding.spec.ts` → **16 passed (16)**, hiçbir mevcut test regresyona uğramadı. |
| 8 | Lighthouse (performans) | N/A | Bu değişiklik saf client-side validasyon; ATDD'de performance_target `null` olarak işaretlenmiş, ayrı bir Lighthouse turu gerektirmiyor — mevcut sayfa yapısı/route değişmedi. |
| 9 | Erişilebilirlik | PASS (kısmi, manuel) | AC-5 unit testinde `aria-live="polite"` container doğrulandı. Lighthouse turu çalıştırılmadı (gate 8 N/A gerekçesiyle) — bu nedenle otomatik a11y skoru yok, sadece hedefli AC-5 kontrolü var. |
| 10 | Güvenlik taraması | FAIL (proje geneli, bu task'a ait değil) | `security-scan` çalıştırıldı, scope: 3 değişen dosya. `secrets` gate PASS. `node_deps` gate FAIL: `vite` (high) ve `vitest` (critical) devDependency zafiyetleri — bu task hiçbir bağımlılık dosyasına (`package.json`/`package-lock.json`) dokunmadı, önceden var olan proje geneli bir durum. Ayrı bir bağımlılık-güncelleme task'ı gerektirir, bu görevin kapsamına dahil edilmedi. |
| 11 | AI code review | PENDING (red-team) | `red-team` adımı bu rapordan sonra bağımsız bir subagent ile çalıştırılacak. |
| 12 | Görsel regresyon | PASS (manuel screenshot, Codex vision-test DEĞİL) | Codex kotası 2026-09-15'e kadar dolu olduğu için standart `vision-test` skill'i (Codex vision) çalıştırılamadı. Bunun yerine gerçek Vite dev server + Playwright ile ekran görüntüsü alındı (`artifacts/bos-istek-engelleme/empty_request_error_state.png`), Claude tarafından doğrudan görsel olarak incelendi: kırmızı (`#DC2626`) kenarlık ve "Devam etmek için bir istek yazın." mesajı tam beklenen konumda ve renkte görünüyor. |
| 13 | İnsan onayı | PENDING | Her zaman son adım — kullanıcı onayı bekleniyor. |

## AC -> Test Mapping
1. AC-1 (happy path) -> `shows no error and calls onContinue when the request text is non-empty` (unit) -> PASS
2. AC-2 (boş girdi) -> `shows a red border and inline error, and does not call onContinue when the request is empty` (unit) + `shows a red border and inline error when Continue is clicked with an empty request` (e2e) -> PASS
3. AC-3 (whitespace-only) -> `treats whitespace-only text the same as empty` (unit) -> PASS
4. AC-4 (hata temizleme) -> `clears the error as soon as the user types non-empty content` (unit) + `clears the red border and error as soon as the user starts typing` (e2e) -> PASS
5. AC-5 (aria-live) -> `renders the error message inside an aria-live="polite" region` (unit) -> PASS
6. AC-6 (tekrar boş bırakma) -> `re-shows the error if the user clears the field again and resubmits` (unit) -> PASS

## Coverage / Quality Notes
- Tüm 6 AC en az bir testle kapsanıyor, kritik olanlar (AC-1/2/3) hem unit hem de (AC-2 için) e2e ile çift kapsanıyor.
- Test piramidi hedefi (unit %70 / e2e %30) fiilen tutturuldu: 6 unit + 2 e2e (yaklaşık 75/25).
- Bilinen açık: gate 10'daki `vite`/`vitest` zafiyetleri bu task'ın işi değil ama proje sahibine ayrı bir bağımlılık güncelleme task'ı olarak bildirilmeli.
- CSS özgüllük riski (plan.md'de öngörülmüştü) `has-error:focus` kuralıyla çözüldü, ekran görüntüsünde de doğrulandı.
