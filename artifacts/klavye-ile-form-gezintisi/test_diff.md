# Test Diff — klavye-ile-form-gezintisi
_Reference: atdd.md, plan.md_

> **Not:** Codex CLI kotası 2026-09-15'e kadar dolu. Önceki iki task
> (#255, #256) ile aynı örnekle, testler istisnai olarak Claude tarafından
> doğrudan yazıldı (`saga` skill Bölüm C override'ı).

## Eklenen Testler

### `ui/src/components/onboarding/OnboardingScreen.test.tsx` (unit — Vitest/RTL)
Yeni `describe('keyboard navigation and focus management (klavye-ile-form-gezintisi)')` bloğu, 5 test:

| Test | AC | Doğruladığı |
|---|---|---|
| does not submit and inserts a normal newline when Enter is pressed inside the textarea | AC-2 | textarea'da Enter'ın `onContinue`'u tetiklemediği (regresyon-koruması, textarea'ya hiçbir yeni handler eklenmedi) |
| calls onContinue when Enter is pressed on the selected-folder-path element and the form is valid | AC-3 | `selected-folder-path`'e eklenen `onKeyDown` — form geçerliyken Enter submit ediyor |
| shows the empty-request error and moves focus to the textarea when Enter is pressed on an invalid form | AC-4 | Aynı `onKeyDown`, form geçersizken (boş istek) hata gösterip odağı textarea'ya taşıyor |
| moves focus to the textarea when Continue is clicked on an invalid form | AC-4 (tıklama) | Odak taşımanın Enter'a özel olmadığı, tıklamada da çalıştığı |
| moves focus to the "Klasör Seç" button after selecting an inaccessible folder | AC-5 | `chooseFolder` içinde `isAccessible=false` sonrası `document.activeElement`'in doğru buton olduğu |

plan.md'de netleştirildiği gibi, "Devam"/"Klasör Seç" butonlarının Enter'da
native tetiklenmesi (AC-3'ün buton kısmı, AC-6) jsdom'da güvenilir simüle
edilemediği için unit testte YOK — sadece e2e'de test ediliyor.

Çalıştırma önce (red): 4/5 yeni test FAIL (AC-2 testi implementasyon
öncesi de trivially geçiyordu çünkü textarea'ya hiçbir handler eklenmemişti
— Enter zaten hiçbir şey tetiklemiyordu, assertion baştan doğruydu), 29/29
eski test PASS.

### `ui/e2e/onboarding.spec.ts` (e2e — Playwright)
6 yeni test, `first-run folder onboarding` describe bloğuna eklendi:

| Test | AC | Doğruladığı |
|---|---|---|
| tabs through the form in the order: choose folder, path, request textarea, continue | AC-1 | Gerçek `Tab` tuşuyla dört durağın da doğru sırada odaklandığı |
| submits when Enter is pressed while the Continue button is focused and the form is valid | AC-3 (buton) | Native buton Enter davranışının submit'i tetiklediği |
| shows the empty-request error and moves focus to the textarea when Enter is pressed on Continue with an invalid form | AC-4 | Devam odağında Enter, geçersiz formda hata+odak taşıma |
| moves focus to the "Klasör Seç" button after selecting an inaccessible folder, in a real browser | AC-5 | Gerçek tarayıcıda odak taşımanın çalıştığı (jsdom'daki `.focus()` simülasyonundan bağımsız doğrulama) |
| still opens the folder dialog when Enter is pressed while "Klasör Seç" is focused | AC-6 | Native buton davranışının bozulmadığı (regresyon) |

## Red-Team Sonrası Ek Test
Bağımsız red-team incelemesi bir doğrulama atlatma açığı buldu:
`handleContinueClick`'in `isFolderInvalid` kontrolü olmadığı için, klavye
kullanıcısı geçersiz bir klasör seçiliyken `selected-folder-path`
elementine Tab'layıp Enter'a basarak `onContinue()`'u tetikleyebiliyordu
(fare kullanıcısının disabled buton sayesinde atlayamadığı bir kontrol).
Düzeltme (`canSubmit` paylaşılan predicate) + yeni regresyon testi:

| Test | Doğruladığı |
|---|---|
| does not call onContinue when Enter is pressed on selected-folder-path while the folder is invalid, even with non-empty request text | Düzeltmenin gerçekten çalıştığı — geçersiz klasör + dolu istek metni + path'te Enter → `onContinue` ÇAĞRILMAZ |

## Doğrulama Komutları ve Sonuç (red → green)
```
npx vitest run ui/src/components/onboarding/OnboardingScreen.test.tsx
```
- İmplementasyon öncesi: 4 failed / 29 passed (33 total) — beklenen red.
- İlk implementasyon sonrası: 33 passed (33).
- Red-team düzeltmesi + regresyon testi sonrası: **34 passed (34)**.

```
npx playwright test ui/e2e/onboarding.spec.ts
```
- **24 passed (24)**, hiçbir mevcut test regresyona uğramadı. Yeni 6 test
  dahil — bu, plan.md'nin "Klasör Seç/Devam butonlarında native Enter
  davranışına güvenilebilir" varsayımını (atdd.md Unknowns) gerçek
  tarayıcıda doğruladı: hiçbir ek `onKeyDown` kodu olmadan bu iki test de
  ilk denemede yeşil geldi.

```
npx tsc --noEmit
```
- Hatasız (yeni `KeyboardEvent` tip importu dahil).

## Kapsam Dışı Bırakılanlar (atdd.md ile tutarlı)
- Ekran okuyucu duyuru iyileştirmeleri, focus-trap/modal davranışı — test edilmedi (kapsam dışı).
- `onContinue`'nun gerçek çağrılma/geçiş mantığı — no-op kaldığı için sadece "çağrıldı mı" kontrol ediliyor, sonrası test edilmiyor.
