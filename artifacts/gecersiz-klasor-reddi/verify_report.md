# Verify Report — gecersiz-klasor-reddi
_Reference: atdd.md, code_diff.md, test_diff.md_

## Verification Gates
| # | Gate | Result | Evidence / Reason |
|---|------|--------|--------------------|
| 1 | Dosya konumu | PASS | `git status --short -- ui/ package.json package-lock.json` → tam olarak code_diff.md'nin listelediği 5 dosya değişmiş. |
| 2 | Build/derleme | PASS | `npm run build` (`tsc --noEmit && vite build`) → `✓ built in 651ms`, hatasız. |
| 3 | Supabase şema/canlı doğrulama | N/A | code_diff.md hiçbir Supabase çağrısı/migration içermiyor. |
| 4 | Lint | N/A | Repo'da linter/formatter tanımlı değil (bos-istek-engelleme task'ında da aynı sonuç). |
| 5 | Type check | PASS | `npx tsc --noEmit` → hatasız (yeni `@tauri-apps/api` import'u dahil). |
| 6 | Unit testler | PASS | `npx vitest run ui/src/components/onboarding/OnboardingScreen.test.tsx` → **28 passed (28)**. AC-1..AC-5 + davranış sözleşmesi satır 8 (invoke reddi) + TOCTOU düzeltmesi (red-team bulgusu, aşağıya bakınız) hepsi kapsanıyor. |
| 7 | E2E testler | PASS | `npx playwright test ui/e2e/onboarding.spec.ts` → **19 passed (19)**, hiçbir mevcut test regresyona uğramadı. |
| 8 | Lighthouse (performans) | N/A | Saf client-side validasyon, performance_target `null`, route değişmedi. |
| 9 | Erişilebilirlik | PASS (kısmi, manuel) | Hata mesajı `aria-live="polite"` container içinde (bos-istek-engelleme'deki pattern tekrar kullanıldı); otomatik Lighthouse a11y skoru yok (gate 8 N/A gerekçesiyle). |
| 10 | Güvenlik taraması | FAIL (proje geneli, bu task'a ait değil) | `security-scan`, scope: 4 değişen dosya (3 UI + package.json). `secrets` PASS. `node_deps` FAIL: aynı önceden var olan `vite`/`vitest` zafiyetleri (bkz. Saga #255'te de aynı bulgu, zaten ayrı bir spawn_task olarak flaglendi — task_id: task_22f9618e). `@tauri-apps/api` eklenmesi yeni bir zafiyet getirmedi. |
| 11 | AI code review | PENDING (red-team) | Bu rapordan sonra bağımsız subagent ile çalıştırılacak. |
| 12 | Görsel regresyon | PASS (manuel screenshot, Codex vision-test DEĞİL) | Codex kotası dolu olduğu için gerçek Vite dev server + Playwright ile ekran görüntüsü alındı (`artifacts/gecersiz-klasor-reddi/inaccessible_folder_error_state.png`): path korunuyor, `#DC2626` hata mesajı ve devre dışı "Devam" butonu doğrulandı. |
| 13 | İnsan onayı | PENDING | Her zaman son adım. |

## AC -> Test Mapping
1. AC-1 (happy path, erişilebilir klasör) -> `shows no error and enables Continue when the selected folder is accessible` (unit) -> PASS
2. AC-2 (erişilemez klasör) -> `keeps the path visible, shows a red error, and disables Continue when the folder is inaccessible` (unit) + `keeps the path visible and disables Continue when the selected folder is inaccessible` (e2e) -> PASS
3. AC-3 (yeniden seçim) -> `clears the error and re-enables Continue after selecting a valid folder` (unit) + `clears the folder error and enables Continue after re-selecting a valid folder` (e2e) -> PASS
4. AC-4 (trailing slash normalize) -> `strips a trailing slash/backslash from the selected path` (unit) + `strips a trailing backslash from the displayed folder path` (e2e) -> PASS
5. AC-5 (ardışık geçersiz seçim) -> `re-shows the error on each consecutive inaccessible folder selection` (unit) -> PASS
6. Davranış sözleşmesi satır 8 (invoke reddi) -> `treats a rejected invoke call as inaccessible instead of failing silently` (unit) -> PASS

## Coverage / Quality Notes
- Tüm 5 AC + davranış sözleşmesi tablosunun 8. satırı (sessiz başarı riski) en az bir testle kapsanıyor.
- Test piramidi hedefi (unit %70 / e2e %30) tutturuldu: 7 unit + 3 e2e (yaklaşık 70/30).
- Race condition riski (plan.md'de öngörülmüştü) `latestRequestedPathRef` ile kodda ele alındı; bağımsız red-team incelemesi bunu doğru buldu.
- Bilinen açık: gate 10'daki `vite`/`vitest` zafiyetleri bu task'ın işi değil, ayrı Saga task'ı olarak zaten flagli (task_22f9618e).

## Red-Team Sonrası Düzeltmeler (bu rapor red-team'den ÖNCE yazılmıştı, sonradan güncellendi)
Bağımsız `obss-red-team` subagent incelemesi 2 bulgu çıkardı:
1. **HIGH (mimari, bu task'ın kapsamı dışı ama release-blocking):** Gerçek
   `@tauri-apps/plugin-fs`/`src-tauri` olmadan bu özellik paketlenip
   gerçek kullanıcıya ulaşırsa, `invoke` reddedilir ve HER klasör
   "erişilemez" gösterilir — onboarding kalıcı çıkmaz sokak olur. Bu,
   atdd.md'de zaten Risk olarak kayıtlıydı ama bir release gate'e
   bağlanmamıştı. **Aksiyon:** Saga task #279 (RELEASE-BLOCKER, critical,
   #256'ya depends_on) oluşturuldu — commit engellenmedi (bu task'ın kendi
   kapsamı içinde doğru), ama paketleme öncesi bu task'ın kapatılması
   zorunlu olarak işaretlendi.
2. **MEDIUM (TOCTOU boşluğu, bu task kapsamında düzeltildi):** Kullanıcı
   zaten geçerli bir klasör seçmişken yeni bir klasör seçtiğinde, `exists`
   sonucu gelene kadarki asenkron pencerede "Devam" yanlışlıkla
   tıklanabilir kalıyordu (eski `isFolderInvalid=false` durumu). **Aksiyon:**
   `isValidatingFolder` state'i eklendi, "Devam"ın `disabled` koşuluna
   dahil edildi, bir unit test (28. test) ile doğrulandı — bkz. code_diff.md.

Gate 6 (Unit testler) yukarıda 28/28 olarak güncellendi, gate 11 (AI code
review) artık PENDING değil — bkz. `red_team.json`.
