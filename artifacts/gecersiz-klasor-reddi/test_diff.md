# Test Diff — gecersiz-klasor-reddi
_Reference: atdd.md, plan.md_

> **Not:** Codex CLI kotası 2026-09-15'e kadar dolu (bkz. proje hafızası
> "Codex Kotası Tükendi"). `bos-istek-engelleme` (Saga #255) task'ındaki
> emsalle aynı şekilde, testler istisnai olarak Claude tarafından doğrudan
> yazıldı (`saga` skill Bölüm C override'ı). `verify` ve bağımsız `red-team`
> subagent adımları normal şekilde çalıştırılacak.

## Eklenen Testler

### `ui/src/components/onboarding/OnboardingScreen.test.tsx` (unit — Vitest/RTL)
Dosya başına `vi.mock('@tauri-apps/api/core', ...)` eklendi (mevcut
`@tauri-apps/plugin-dialog` mock pattern'iyle tutarlı), `beforeEach`'te
varsayılan `invokeTauriCommand.mockResolvedValue(true)` ayarlandı ki mevcut
21 test (klasör her zaman "erişilebilir" kabul edilerek) regresyona
uğramasın.

Yeni `describe('invalid folder rejection (gecersiz-klasor-reddi)')` bloğu, 7 test:

| Test | AC | Doğruladığı |
|---|---|---|
| shows no error and enables Continue when the selected folder is accessible | AC-1 | Happy path: `exists` `true` dönerse hata yok, Devam aktif, `invoke` doğru parametrelerle çağrılıyor |
| disables Continue while a newly-selected folder's accessibility check is still pending, even if the previous folder was valid | TOCTOU düzeltmesi (red-team bulgusu) | Önceden geçerli bir klasör seçiliyken yeni bir klasör seçilir seçilmez, `exists` sonucu gelene kadar "Devam" kesin olarak devre dışı kalır — stale `isFolderInvalid=false` penceresi kapatıldı |
| keeps the path visible, shows a red error, and disables Continue when the folder is inaccessible | AC-2 | `exists` `false` dönerse path korunur, `#DC2626` renkte hata mesajı, Devam disabled |
| clears the error and re-enables Continue after selecting a valid folder | AC-3 | Önce geçersiz sonra geçerli klasör seçilince hata kalkar |
| strips a trailing slash/backslash from the selected path | AC-4 | `"C:\...\Belgeler\"` → `"C:\...\Belgeler"` normalize ediliyor, `invoke` normalize edilmiş path ile çağrılıyor |
| re-shows the error on each consecutive inaccessible folder selection | AC-5 | Art arda geçersiz seçimlerde hata her seferinde yeniden gösteriliyor |
| treats a rejected invoke call as inaccessible instead of failing silently | Davranış sözleşmesi satır 8 | `invoke` reddedilirse (Promise rejection) sessiz başarı değil, "erişilemez" hatası gösteriliyor |

Çalıştırma önce (red): 6/6 yeni test FAIL, 21/21 eski test PASS (toplam 27
testten 6'sı kırmızı) — beklenen red durumu.

### `ui/e2e/onboarding.spec.ts` (e2e — Playwright)
Mevcut 5 `__TAURI_INTERNALS__.invoke` mock bloğu (satır ~26, 96, 116, 210,
228 civarı) genişletildi: artık `'plugin:fs|exists'` komutunu da `true`
döndürerek ele alıyor — aksi halde mevcut testler (klasör seçiminin Devam'ı
aktifleştirdiğini varsayan) yeni `isFolderInvalid` kontrolü yüzünden kırılırdı.

3 yeni test, `first-run folder onboarding` describe bloğuna eklendi:

| Test | AC | Doğruladığı |
|---|---|---|
| keeps the path visible and disables Continue when the selected folder is inaccessible | AC-2 | Gerçek tarayıcıda: `exists: false` dönünce path görünür kalır, hata mesajı görünür, Devam disabled |
| clears the folder error and enables Continue after re-selecting a valid folder | AC-3 | İki ardışık dialog çağrısı (önce geçersiz, sonra geçerli) simüle edilip hata düzeliyor |
| strips a trailing backslash from the displayed folder path | AC-4 | Trailing backslash içeren path gerçek tarayıcıda temizleniyor |

## Doğrulama Komutları ve Sonuç (red → green)
```
npx vitest run ui/src/components/onboarding/OnboardingScreen.test.tsx
```
- İmplementasyon öncesi: 6 failed / 21 passed (27 total) — beklenen red.
- İlk implementasyon sonrası: 27 passed (27).
- Red-team'in TOCTOU bulgusu üzerine `isValidatingFolder` eklenip 7. test
  yazıldıktan sonra: **28 passed (28)** (bir mevcut testte — AC-5,
  "re-shows the error on each consecutive..." — yeni senkron `isFolderInvalid(false)`
  sıfırlaması stale-DOM-eşleşme yarışına yol açtı, `waitFor` ile path
  güncellemesini önce bekleyip stale elementi eleyecek şekilde test
  düzeltildi — implementasyon değil, test sıralaması hatalıydı).

```
npx playwright test ui/e2e/onboarding.spec.ts
```
- **19 passed (19)**, hiçbir mevcut test regresyona uğramadı (5 mock bloğu
  genişletilmeden önce çalıştırılmadı — implementasyonla birlikte tek
  seferde yeşile alındı, ayrı bir red/green döngüsü gerektirmedi çünkü mock
  genişletmesi implementasyonla eş zamanlı yapıldı).

```
npx tsc --noEmit
```
- Hatasız, temiz derleme (yeni `@tauri-apps/api` import'u dahil).

## Kapsam Dışı Bırakılanlar (atdd.md ile tutarlı)
- "Yok" ile "izinsiz" hata nedenlerinin ayrı test edilmesi — tek bir `exists: false` senaryosu yeterli kabul edildi.
- Diske yazma başlamadığını doğrulayan ayrı bir spy testi — invariant olarak kabul edildi, test yazılmadı (kullanıcı kararı).
- Gerçek `@tauri-apps/plugin-fs`/`src-tauri` entegrasyon testleri — bu task'ın kapsamı sadece mock'lanabilir `invoke` sözleşmesi.
