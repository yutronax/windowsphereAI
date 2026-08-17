# Plan — gecersiz-klasor-reddi
_Reference: atdd.md_

## Files to Modify
| File | Why | Risk |
|------|-----|------|
| ui/src/components/onboarding/OnboardingScreen.tsx | `chooseFolder` sonrası path normalize edilecek (trailing slash/backslash temizleme) ve `invoke('plugin:fs|exists', { path })` (`@tauri-apps/api/core`) çağrılacak. Yeni `isFolderInvalid` state eklenip `false` dönerse hata mesajı + `#DC2626` gösterilecek, `true` dönerse temizlenecek. "Devam" butonunun `disabled` koşuluna `isFolderInvalid` eklenecek (atdd.md AC-2: erişilemezken buton devre dışı). Race condition'a karşı en son seçilen path referans alınacak (atdd.md Risks). | medium |
| ui/src/components/onboarding/OnboardingScreen.test.tsx | Yeni `describe` bloğu: `@tauri-apps/api/core`'un `invoke` fonksiyonu `vi.mock` ile mocklanıp true/false/reject senaryoları test edilecek (AC-1..AC-5), trailing slash normalize testi (AC-4). | low |
| ui/e2e/onboarding.spec.ts | Mevcut `window.__TAURI_INTERNALS__.invoke` mock'u genişletilecek: `'plugin:fs|exists'` komutu da ele alınacak (şu an sadece `'plugin:dialog|open'` handle ediliyor). Gerçek tarayıcıda erişilemez klasör seçimi + hata mesajı + yeniden seçimle düzelme senaryoları eklenecek. | low |
| package.json | `@tauri-apps/api` şu an sadece `@tauri-apps/plugin-dialog`'un transitive/peer bağımlılığı olarak `node_modules`'ta mevcut ama `package.json`'da açıkça listelenmiyor. Kod doğrudan `@tauri-apps/api/core`'dan `invoke` import edeceği için, bu paket `dependencies`'e açıkça eklenmeli — transitive çözümlemeye güvenmek kırılgan (plugin-dialog kendi bağımlılığını değiştirirse kod kırılabilir). Bu, atdd.md'nin "gerçek @tauri-apps/plugin-fs eklenmesi kapsam dışı" kararıyla ÇELİŞMİYOR — `@tauri-apps/api` zaten var olan bir paket, yeni bir plugin değil, sadece `invoke` fonksiyonuna erişim sağlıyor. | low |

## New Files
Yok — mevcut dosyalara ekleme yapılıyor.

## Dependencies
- Mevcut `chooseFolder`/`selectedFolder` state mimarisiyle tutarlı kalınacak; `bos-istek-engelleme` task'ındaki `isRequestEmpty`/`has-error`/`.onboarding-error-message` pattern'i birebir tekrar kullanılacak (aynı CSS class'ları, aynı `aria-live="polite"` yaklaşımı — yeni bir hata gösterme mekanizması icat edilmeyecek).
- Unit testte `open()`'ın zaten `vi.mock('@tauri-apps/plugin-dialog', ...)` ile mocklandığı pattern'e paralel olarak, yeni `invoke()` da `vi.mock('@tauri-apps/api/core', ...)` ile mocklanacak.
- E2e testte mevcut `window.__TAURI_INTERNALS__.invoke` switch-case yapısı (`cmd === 'plugin:dialog|open' ? ... : Promise.reject(...)`) genişletilecek, yeni bir mock mekanizması kurulmayacak.
- "Devam" butonunun `disabled` koşulu: `!isReady || !selectedFolder || isFolderInvalid` (atdd.md AC-2 ile uyumlu — erişilemez klasördeyken buton devre dışı kalmalı).

## Migration Required?
No — DB/schema değişikliği yok, saf frontend state + bir npm bağımlılığının açıkça listelenmesi.

## Risks
- (atdd.md'den taşındı) **Race condition**: kullanıcı hızlıca art arda birden fazla klasör seçerse, önceki bir `exists` invoke'unun geç dönen sonucu daha yeni bir seçimin state'ini geçersiz kılabilir. Çözüm: `chooseFolder` içinde invoke çağrılırken referans alınan path'i bir değişkende tutup, invoke sonucu geldiğinde state'e yazmadan önce "hâlâ en güncel seçim bu mu?" kontrolü yapılacak (örn. bir `useRef` ile en son seçilen path karşılaştırılarak).
- (atdd.md'den taşındı) **Mock/gerçek API uyuşmazlığı**: `invoke('plugin:fs|exists', {path})` sözleşmesi gerçek `@tauri-apps/plugin-fs`'in gelecekteki API'siyle birebir eşleşmeyebilir — bu task'ın bilinçli kapsam kararı, ileride yeniden doğrulanmalı.
- `@tauri-apps/api`'nin `package.json`'a eklenmesi `package-lock.json`'da da değişikliğe yol açacak (npm install sonrası) — bu, `verify` adımındaki `security-scan` gate'inin `node_deps` sonucunu etkileyebilir (mevcut vite/vitest zafiyetleri zaten oradaydı, ayrı bir Saga task'ı olarak flagli — bu task'ın onu büyütüp büyütmediği verify'da kontrol edilmeli).

## Open Questions
Yok — atdd.md'deki 12 soru-cevap ve yukarıdaki `@tauri-apps/api` bağımlılık kararı (Files to Modify'de gerekçelendirildi) planı netleştirmeye yetti.

## Not
`OnboardingScreen.tsx` bir React component'i (rendered web UI) — bu, `verify` adımında gate 11/12'nin (`vision-test`) N/A değil AKTİF çalışacağı anlamına gelir; kırmızı hata mesajı ve korunan path göstergesi ekran görüntüsüyle doğrulanmalı (Codex kotası dolu olduğu için bos-istek-engelleme task'ındaki manuel/Playwright screenshot yöntemi tekrarlanacak).
