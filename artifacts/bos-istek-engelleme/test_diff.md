# Test Diff — bos-istek-engelleme
_Reference: atdd.md, plan.md_

> **Not:** Codex CLI (`ask_codex.py` → `gpt-5.6-terra`) kotası 2026-08-16'da tükendi
> (2026-09-15'e kadar dolu, bkz. proje hafızası "Codex Kotası Tükendi"). Bu task'ta
> testler istisnai olarak Claude tarafından doğrudan yazıldı — kullanıcı 2026-08-16'da
> "codex ikincil plana, claude subagentler öncelikli olsun" talimatını verdiği için
> `saga` skill'inin Bölüm C override'ı uygulandı. `verify` ve bağımsız `red-team`
> subagent adımları normal şekilde çalıştırıldı/çalıştırılacak.

## Eklenen Testler

### `ui/src/components/onboarding/OnboardingScreen.test.tsx` (unit — Vitest/RTL)
Yeni `describe('empty request validation (bos-istek-engelleme)')` bloğu, 6 test:

| Test | AC | Doğruladığı |
|---|---|---|
| shows no error and calls onContinue when the request text is non-empty | AC-1 | Happy path: geçerli metinle hata yok, `onContinue` çağrılır |
| shows a red border and inline error, and does not call onContinue when the request is empty | AC-2 | Boş girdi: `#DC2626` kenarlık, mesaj görünür, `onContinue` çağrılmaz |
| treats whitespace-only text the same as empty | AC-3 | `"   \n\t  "` gibi sadece boşluktan oluşan girdi de boş sayılır |
| clears the error as soon as the user types non-empty content | AC-4 | Hata gösteriliyorken yazmaya başlayınca anında kaybolur |
| renders the error message inside an aria-live="polite" region | AC-5 | Erişilebilirlik: mesaj `aria-live="polite"` container içinde |
| re-shows the error if the user clears the field again and resubmits | AC-6 | Hata düzeltilip tekrar boşaltılırsa yeniden gösterilir |

Çalıştırma önce (red): 5/6 yeni test FAIL (AC-1 testi implementasyon öncesi de
trivially geçiyordu çünkü mevcut kod zaten koşulsuz `onContinue()` çağırıyordu ve
hiçbir hata elementi hiç render edilmiyordu — happy-path assertion'ları bu durumda
zaten doğruydu).

### `ui/e2e/onboarding.spec.ts` (e2e — Playwright)
2 yeni test, `first-run folder onboarding` describe bloğuna eklendi:

| Test | AC | Doğruladığı |
|---|---|---|
| shows a red border and inline error when Continue is clicked with an empty request | AC-2 | Gerçek tarayıcıda: klasör seçili + boş istekle Devam'a basınca `rgb(220, 38, 38)` kenarlık ve mesaj DOM'da görünür |
| clears the red border and error as soon as the user starts typing | AC-4 | Yazmaya başlayınca hata kalkar (odak kenarlığı `#2563EB` geçerli kalır, hata kenarlığı değil) |

## Doğrulama Komutları ve Sonuç (red → green)
```
npx vitest run ui/src/components/onboarding/OnboardingScreen.test.tsx
```
- İmplementasyon öncesi: 5 failed / 16 passed (21 total) — beklenen red.
- İmplementasyon sonrası: **21 passed (21)**.

```
npx playwright test ui/e2e/onboarding.spec.ts
```
- İlk çalıştırmada 1 test yanlış assertion içeriyordu (AC-4 e2e testi, odaktaki
  textarea'nın kenarlık rengini varsayılan `#E5E7EB` bekliyordu, oysa `fill()`
  sonrası element hâlâ focus'lu kalıyor ve `#2563EB` focus kenarlığı geçerli
  oluyor — test düzeltildi, implementasyon değil).
- Düzeltme sonrası: **16 passed (16)**, hiçbir mevcut test regresyona uğramadı.

## Kapsam Dışı Bırakılanlar (atdd.md ile tutarlı)
- `onContinue`'nun gerçek çağrılma/geçiş mantığı test edilmiyor (zaten no-op, `App.tsx` değişmedi).
- `selectedFolder` boşluğu senaryosu test edilmiyor (mevcut testler zaten kapsıyor, bu task'ın konusu değil).
