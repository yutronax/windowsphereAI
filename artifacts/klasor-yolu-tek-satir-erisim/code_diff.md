# Code Diff — klasor-yolu-tek-satir-erisim
_efektor subagent tarafından yazıldı (Codex kotası tükendiği için), GREEN adımı._

## Değiştirilen Dosya

| Dosya | Değişiklik |
|---|---|
| `ui/src/components/onboarding/OnboardingScreen.tsx` | `truncateWindowsPath` kaldırıldı; `.onboarding-path` CSS class'ı (nowrap/ellipsis) + `tabIndex`/tooltip mantığı eklendi |

## Acceptance Criteria Kapsamı
- **AC-1** ✅ — `.onboarding-path` class'ı `white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:320px`.
- **AC-2** ✅ — `tabIndex={0}` + `onFocus`/`onBlur` ile `folder-path-tooltip` görünürlüğü.
- **AC-3** ✅ — Aynı tooltip `onMouseEnter`/`onMouseLeave` ile de tetikleniyor.
- **AC-4** ✅ — Element artık ham `selectedFolder` metnini doğrudan içeriyor (JS kesme yok).

## Plandan Sapma (gerekçeli)
Plan/atdd.md "CSS-only, React state gerekmesin" tercih etmişti. Saf CSS
(`:hover`/`:focus` + adjacent-sibling, tooltip her zaman DOM'da ama
`display:none`) denendi, ama şu sorunla çakıştı: mevcut (dokunulmaması
gereken) bir testte `screen.findByText(fullPath)` çağrısı, aynı tam metnin
hem `<p>` hem tooltip `<span>`'de aynı anda DOM'da bulunması yüzünden
"multiple elements found" hatası verdi; AC-4 de elementin gerçek metin
içermesini zorunlu kıldığı için metni `content: attr()` ile gizlemek de
mümkün değildi. Bunun yerine minimal bir `useState` (`isPathTooltipVisible`)
+ native `onFocus/onBlur/onMouseEnter/onMouseLeave` olaylarıyla koşullu
render'a geçildi — hâlâ ek kütüphane yok, CAVEMAN'e uygun en küçük sapma.

## CAVEMAN İncelemesi
- 1 dosya değiştirildi, yeni dosya yok.
- Tek yeni state (`isPathTooltipVisible`) — gerekçesi yukarıda açıklandı.
- Mevcut `chooseFolder`/`disabled` mantığı ve task #251'in buton stili
  bozulmadı.

## Red-team Sonrası Düzeltme (efektor)
obss-red-team incelemesi 2 MEDIUM bulgu buldu, ikisi de düzeltildi:
- **Focus/hover state çakışması:** `isPathTooltipVisible` tek boolean'ı,
  `isFocused`/`isHovered` iki ayrı state'e bölündü (görünürlük `isFocused ||
  isHovered`) — Tab ile odaklanıp fare üzerinden geçip ayrılma artık
  tooltip'i yanlışlıkla kapatmıyor.
- **ARIA bağlantısı eksikliği:** Tooltip span'ine `id` + `role="tooltip"`,
  tetikleyici `<p>` elementine `aria-describedby` eklendi.

## Final Test Durumu
- `npx vitest run` → 13/13 PASS
- `npx playwright test` → 9/9 PASS (2 kez tekrarlandı, flaky değil)
- `npm run build` → hatasız

## Sıradaki Adım
`verify` — gate'lerin tamamı tekrar gerçek çalıştırmayla doğrulanacak.
