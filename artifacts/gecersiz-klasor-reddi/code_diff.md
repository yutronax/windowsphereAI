# Code Diff — gecersiz-klasor-reddi
_Reference: atdd.md, plan.md, test_diff.md_

> **Not:** Codex kotası dolu (2026-09-15'e kadar); implementasyon istisnai
> olarak Claude tarafından yazıldı (`saga` skill Bölüm C override'ı).
> Bağımsız `red-team` subagent doğrulaması ayrıca çalıştırılacak.

## Değiştirilen Dosyalar

### `package.json`
`@tauri-apps/api` (`^2.11.1`) `dependencies`'e açıkça eklendi. Daha önce
sadece `@tauri-apps/plugin-dialog`'un transitive bağımlılığı olarak
`node_modules`'ta mevcuttu; kod artık doğrudan `@tauri-apps/api/core`'dan
`invoke` import ettiği için açık bağımlılık gerekiyor (plan.md'de
gerekçelendirildi — yeni bir plugin değil, zaten kurulu bir paketin açık
deklarasyonu). `npm install` çalıştırılıp `package-lock.json` senkronize
edildi.

### `ui/src/components/onboarding/OnboardingScreen.tsx`

**Yeni state ve ref:**
- `isFolderInvalid` (`useState<boolean>`) — hata görünür mü kontrolü.
- `isValidatingFolder` (`useState<boolean>`) — async `exists` kontrolü
  sürerken "Devam"ı devre dışı tutan ek bayrak (bkz. TOCTOU düzeltmesi aşağıda).
- `latestRequestedPathRef` (`useRef<string | null>`) — race condition
  koruması: kullanıcı art arda hızlı klasör seçerse, eski/yavaş bir
  `invoke` sonucu daha yeni bir seçimin state'ini ezmesin diye en son
  istenen path referans alınıyor.

**Değiştirilen `chooseFolder`:**
```ts
async function chooseFolder() {
  const folder = await open({ directory: true, multiple: false });
  if (typeof folder !== 'string') return;

  const normalizedPath = folder.replace(/[\\/]+$/, '');
  latestRequestedPathRef.current = normalizedPath;
  setSelectedFolder(normalizedPath);
  setIsFolderInvalid(false);
  setIsValidatingFolder(true);

  let isAccessible: boolean;
  try {
    isAccessible = await invoke<boolean>('plugin:fs|exists', { path: normalizedPath });
  } catch {
    isAccessible = false;
  }

  if (latestRequestedPathRef.current !== normalizedPath) return;
  setIsFolderInvalid(!isAccessible);
  setIsValidatingFolder(false);
}
```
- Trailing slash/backslash normalize (`/[\\/]+$/` regex) — AC-4.
- Path her zaman hemen state'e yazılır (seçim korunur — atdd.md'nin
  "hata mesajı seçimi korumalı" kararıyla uyumlu), erişilebilirlik kontrolü
  ayrı ve asenkron.
- `invoke` reddedilirse (`catch`) `isAccessible = false` — davranış
  sözleşmesi tablosundaki 8. satır ("hiçbir şey yapılamadı ama hata da
  yok" riskine karşı sessiz başarı yasağı) burada uygulanıyor.
- Stale-response guard: invoke sonucu geldiğinde `latestRequestedPathRef`
  hâlâ aynı path'i gösteriyorsa state güncellenir, değilse (kullanıcı bu
  arada başka bir klasör seçmişse) sonuç sessizce atılır.
- **TOCTOU düzeltmesi (red-team bulgusu, commit öncesi uygulandı):**
  İlk versiyonda, kullanıcı zaten geçerli bir klasör seçmişken (Devam aktif)
  yeni bir klasör seçtiğinde, yeni `exists` kontrolü sonuçlanana kadar geçen
  asenkron pencerede `isFolderInvalid` hâlâ eski (`false`) değerini
  taşıyordu — bu da "Devam"ın, henüz doğrulanmamış yeni bir klasörle
  tıklanabilir kalmasına yol açıyordu (tam da bu task'ın önlemeye çalıştığı
  senaryo, sadece bir zamanlama boşluğuyla). Düzeltme: yeni seçimde hem
  `isFolderInvalid` hemen `false`'a çekiliyor (eski hatayı temizler) hem de
  `isValidatingFolder` `true` yapılıp "Devam" butonunun `disabled`
  koşuluna ekleniyor — doğrulama süren pencerede buton kesin olarak devre
  dışı kalıyor.

**JSX değişiklikleri:**
- `selected-folder-path` bloğundan hemen sonra, `isFolderInvalid` true
  iken `aria-live="polite"` container içinde `.onboarding-error-message`
  class'lı (bos-istek-engelleme task'ından tekrar kullanılan, yeni CSS
  eklenmedi) "Seçilen klasöre erişilemiyor. Lütfen başka bir klasör seçin."
  mesajı render ediliyor.
- "Devam" butonunun `disabled` koşuluna `isFolderInvalid` VE `isValidatingFolder`
  eklendi: `!isReady || !selectedFolder || isFolderInvalid || isValidatingFolder`.
- "Yeniden seçim düğmesi" için yeni bir buton eklenmedi — kullanıcı
  kararıyla mevcut "Klasör Seç" butonu bu işlevi görüyor (DRY).

## Değiştirilmeyen Dosyalar (plan.md ile tutarlı)
- `App.tsx` — dokunulmadı.
- `backend/` — dokunulmadı, doğrulama tamamen frontend/mock-Tauri tarafında.
- CSS (`<style>` bloğu) — yeni kural eklenmedi, mevcut `.onboarding-error-message` class'ı yeniden kullanıldı.

## Doğrulama
- `npx vitest run ui/src/components/onboarding/OnboardingScreen.test.tsx` → 28/28 geçti (TOCTOU düzeltmesi + testi dahil).
- `npx playwright test ui/e2e/onboarding.spec.ts` → 19/19 geçti.
- `npx tsc --noEmit` → hatasız.
- `npm run build` → başarılı (`✓ built in 651ms`).
- Manuel ekran görüntüsü (Codex vision-test kotası dolu, bos-istek-engelleme emsaliyle): `artifacts/gecersiz-klasor-reddi/inaccessible_folder_error_state.png` — path korunuyor, kırmızı hata mesajı ve devre dışı "Devam" butonu doğrulandı.
