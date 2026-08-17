# Code Diff — klavye-ile-form-gezintisi
_Reference: atdd.md, plan.md, test_diff.md_

> **Not:** Codex kotası dolu; implementasyon istisnai olarak Claude
> tarafından yazıldı (`saga` skill Bölüm C override'ı).

## Değiştirilen Dosya
`ui/src/components/onboarding/OnboardingScreen.tsx`

### Yeni import
`useRef, useState` yanına `type KeyboardEvent` eklendi (`react`'ten) —
`handleFolderPathKeyDown`'ın parametre tipi için.

### Yeni ref'ler
- `chooseFolderButtonRef` (`useRef<HTMLButtonElement>(null)`) — "Klasör
  Seç" butonuna bağlı, hata sonrası odak taşımak için (AC-5).
- `requestTextareaRef` (`useRef<HTMLTextAreaElement>(null)`) — textarea'ya
  bağlı, boş istek hatası sonrası odak taşımak için (AC-4).

### Değiştirilen `chooseFolder`
```ts
if (latestRequestedPathRef.current !== normalizedPath) return;
setIsFolderInvalid(!isAccessible);
setIsValidatingFolder(false);
if (!isAccessible) chooseFolderButtonRef.current?.focus();
```
Sadece son satır eklendi — `isAccessible=false` olduğunda "Klasör Seç"
butonuna odak taşınıyor (AC-5). Ref her zaman DOM'da mevcut bir elemente
işaret ettiği için (buton koşulsuz render ediliyor) `useEffect` gerekmedi
— plan.md'nin öngördüğü zamanlama riski ortadan kalktı.

### Değiştirilen `handleContinueClick` (red-team düzeltmesi dahil)
```ts
const canSubmit = isReady && !!selectedFolder && !isFolderInvalid && !isValidatingFolder;

function handleContinueClick() {
  if (!canSubmit) return;
  if (requestText.trim() === '') {
    setIsRequestEmpty(true);
    requestTextareaRef.current?.focus();
    return;
  }
  onContinue();
}
```
`requestTextareaRef.current?.focus()` eklendi — boş istek hatası
gösterildiğinde odak textarea'ya taşınıyor (AC-4). Bu fonksiyon hem
"Devam" butonunun `onClick`'i hem de yeni `handleFolderPathKeyDown`
tarafından çağrıldığı için, hem tıklama hem Enter senaryosunda aynı odak
taşıma davranışı otomatik olarak sağlanıyor.

**Red-team bulgusu ve düzeltmesi:** İlk versiyonda `handleContinueClick`
sadece `requestText` boşluğunu kontrol ediyordu, `isFolderInvalid`/
`isValidatingFolder`'ı DEĞİL — bu kontrol sadece "Devam" butonunun
`disabled` özniteliğinde vardı. Bağımsız red-team incelemesi bunun bir
doğrulama atlatma açığı olduğunu buldu: `selected-folder-path` elementi
`isFolderInvalid` durumundan bağımsız olarak her zaman odaklanabilir
kaldığından, klavye kullanıcısı geçersiz bir klasör seçiliyken bu elemana
Tab'layıp Enter'a basarak `onContinue()`'u tetikleyebiliyordu — fare
kullanıcısının (disabled buton sayesinde) atlayamadığı bir kontrolü
klavye kullanıcısı atlatabiliyordu. Düzeltme: `canSubmit` adında tek bir
paylaşılan predicate çıkarıldı, hem "Devam" butonunun `disabled`
özniteliğinde hem `handleContinueClick`'in başında kullanılıyor — kural
artık tek bir yerde tanımlı, tıklama ve Enter aynı ön koşulları uyguluyor.

### Yeni fonksiyon: `handleFolderPathKeyDown`
```ts
function handleFolderPathKeyDown(e: KeyboardEvent) {
  if (e.key === 'Enter') handleContinueClick();
}
```
`selected-folder-path` `<p>` elementine bağlandı (AC-3, AC-4). Bu, native
buton davranışına sahip OLMAYAN tek odaklanabilir eleman olduğu için
(diğer ikisi zaten `<button>`) yeni kod gerektiren TEK yer — plan.md'nin
Assumptions bölümündeki tahmini doğruladı.

### JSX değişiklikleri
- `<button ref={chooseFolderButtonRef} ...>Klasör Seç</button>` — ref eklendi.
- `<p ... onKeyDown={handleFolderPathKeyDown}>` — mevcut `onFocus`/
  `onBlur`/`onMouseEnter`/`onMouseLeave` (tooltip için) korunarak yeni
  prop eklendi, çakışma yok.
- `<textarea ref={requestTextareaRef} ...>` — ref eklendi.
- "Devam" butonunun `disabled` özniteliği `!isReady || !selectedFolder ||
  isFolderInvalid || isValidatingFolder` yerine `!canSubmit` olarak
  sadeleştirildi (red-team düzeltmesi — tek kaynak).
- **"Devam" ve "Klasör Seç" butonlarına HİÇBİR yeni `onKeyDown` eklenmedi**
  — plan.md'nin varsayımı (native buton Enter davranışı zaten yeterli)
  gerçek tarayıcıda (Playwright) doğrulandı, ek kod gerekmedi (bkz.
  test_diff.md, e2e AC-3/AC-6 testleri ilk denemede yeşil geldi).

## Değiştirilmeyen Dosyalar (plan.md ile tutarlı)
- CSS (`<style>` bloğu) — hiç dokunulmadı, yeni bir görsel stil eklenmedi (atdd.md Benchmark kararıyla uyumlu).
- `App.tsx`, `backend/` — dokunulmadı.

## Doğrulama
- `npx vitest run ui/src/components/onboarding/OnboardingScreen.test.tsx` → 34/34 geçti (red-team düzeltmesi + regresyon testi dahil).
- `npx playwright test ui/e2e/onboarding.spec.ts` → 24/24 geçti (değişmedi, hâlâ yeşil).
- `npx tsc --noEmit` → hatasız.
- `npm run build` → başarılı (`✓ built in 619ms`).
