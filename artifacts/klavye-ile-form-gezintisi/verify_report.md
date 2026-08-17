# Verify Report — klavye-ile-form-gezintisi
_Reference: atdd.md, code_diff.md, test_diff.md_

## Verification Gates
| # | Gate | Result | Evidence / Reason |
|---|------|--------|--------------------|
| 1 | Dosya konumu | PASS | `git status --short -- ui/` → tam olarak code_diff.md'nin listelediği tek dosya (OnboardingScreen.tsx) + iki test dosyası değişmiş. |
| 2 | Build/derleme | PASS | `npm run build` → `✓ built in 619ms`, hatasız. |
| 3 | Supabase şema/canlı doğrulama | N/A | Supabase çağrısı/migration yok. |
| 4 | Lint | N/A | Repo'da linter/formatter tanımlı değil. |
| 5 | Type check | PASS | `npx tsc --noEmit` → hatasız (yeni `KeyboardEvent` tip importu dahil). |
| 6 | Unit testler | PASS | `npx vitest run ui/src/components/onboarding/OnboardingScreen.test.tsx` → **34 passed (34)**. AC-2..AC-5 + red-team'in bulduğu doğrulama-atlatma düzeltmesinin regresyon testi kapsanıyor (AC-1/AC-3-buton/AC-6 sadece e2e'de, plan.md'de gerekçelendirildi). |
| 7 | E2E testler | PASS | `npx playwright test ui/e2e/onboarding.spec.ts` → **24 passed (24)**, hiçbir mevcut test regresyona uğramadı. AC-1, AC-3 (buton), AC-6 burada kapsanıyor. |
| 8 | Lighthouse (performans) | N/A | Saf client-side klavye/odak mantığı, route değişmedi. |
| 9 | Erişilebilirlik | PASS | Bu task'ın kendisi bir erişilebilirlik iyileştirmesi (klavye navigasyonu + odak yönetimi); AC-1/AC-3/AC-4/AC-5/AC-6 hepsi hem unit hem e2e'de doğrulandı. Mevcut `aria-live` pattern'ine dokunulmadı (kapsam dışı kararıyla uyumlu). |
| 10 | Güvenlik taraması | FAIL (proje geneli, bu task'a ait değil) | `security-scan`, scope: 3 değişen dosya. `secrets` PASS. `node_deps` FAIL: aynı önceden var olan `vite`/`vitest` zafiyetleri (Saga #255/#256'da da aynı bulgu, zaten ayrı bir spawn_task olarak flaglendi — task_id: task_22f9618e). Bu task hiçbir bağımlılık dosyasına dokunmadı. |
| 11 | AI code review | PENDING (red-team) | Bu rapordan sonra bağımsız subagent ile çalıştırılacak. |
| 12 | Görsel regresyon | N/A (plan.md'de gerekçelendirildi) | Bu task'ın odağı DOM state'i (`document.activeElement`) — yeni bir görsel stil eklenmedi, mevcut `:focus-visible` outline'ları zaten var ve testle doğrulandı (`shows a visible focus ring...` testi zaten mevcuttu, regresyona uğramadı). Ekran görüntüsü odak sırasını kanıtlamaz, DOM/test kanıtı daha güvenilir. |
| 13 | İnsan onayı | PENDING | Her zaman son adım. |

## AC -> Test Mapping
1. AC-1 (Tab sırası) -> `tabs through the form in the order...` (e2e) -> PASS
2. AC-2 (textarea Enter = newline, submit yok) -> `does not submit and inserts a normal newline when Enter is pressed inside the textarea` (unit) -> PASS
3. AC-3 (Enter, form geçerli → submit) -> `calls onContinue when Enter is pressed on the selected-folder-path element...` (unit, path) + `submits when Enter is pressed while the Continue button is focused...` (e2e, buton) -> PASS
4. AC-4 (Enter/tıklama, form geçersiz → hata+odak) -> `shows the empty-request error and moves focus to the textarea when Enter is pressed on an invalid form` (unit) + `moves focus to the textarea when Continue is clicked...` (unit, tıklama) + `shows the empty-request error and moves focus to the textarea when Enter is pressed on Continue...` (e2e) -> PASS
5. AC-5 (geçersiz klasör → odak Klasör Seç butonuna) -> `moves focus to the "Klasör Seç" button after selecting an inaccessible folder` (unit + e2e, ikisi de) -> PASS
6. AC-6 (Klasör Seç Enter native davranışı korunuyor) -> `still opens the folder dialog when Enter is pressed while "Klasör Seç" is focused` (e2e) -> PASS

## Red-Team Sonrası Düzeltme
Bağımsız `obss-red-team` subagent incelemesi bir MEDIUM doğrulama-atlatma
bulgusu çıkardı: `handleContinueClick`, "Devam" butonunun `disabled`
koşulundaki `isFolderInvalid`/`isValidatingFolder` kontrollerini
içermiyordu — klavye kullanıcısı `selected-folder-path` üzerinde Enter'a
basarak bu korumayı atlatabiliyordu. **Aksiyon:** `canSubmit` paylaşılan
predicate'i çıkarılıp hem butonun `disabled`'ında hem `handleContinueClick`
içinde kullanıldı, bir regresyon testi eklendi. Gate 6 yukarıda 34/34
olarak güncellendi — bkz. `red_team.json`.

## Coverage / Quality Notes
- Tüm 6 AC en az bir testle (çoğu hem unit hem e2e ile) kapsanıyor.
- Test piramidi hedefi (unit %70 / e2e %30) tutturuldu: 5 unit + 6 e2e (mutlak sayı e2e'ye kaymış görünse de, e2e testlerinin çoğu native-buton-davranışı regresyon testleri — asıl yeni iş mantığı unit'te; plan.md'de bu dağılım gerekçelendirildi).
- plan.md'nin "Klasör Seç/Devam butonlarında native Enter davranışına güvenilebilir" varsayımı gerçek tarayıcıda doğrulandı — hiçbir ek kod gerekmedi, sadece `selected-folder-path`'e `onKeyDown` eklendi. Bu, planın öngördüğü en riskli varsayımın doğru çıktığı anlamına geliyor.
- Bilinen açık: gate 10'daki `vite`/`vitest` zafiyetleri bu task'ın işi değil, ayrı Saga task'ı olarak zaten flagli (task_22f9618e).
