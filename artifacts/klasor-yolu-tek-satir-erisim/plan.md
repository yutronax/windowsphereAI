# Plan — klasor-yolu-tek-satir-erisim
_Reference: atdd.md_

## Bağlam
Mevcut `OnboardingScreen.tsx:66` şu an:
```tsx
{selectedFolder && <p data-testid="selected-folder-path" title={selectedFolder}>{truncateWindowsPath(selectedFolder, 80)}</p>}
```
`truncateWindowsPath` (satır 12-21) JS ile 80 karaktere kesiyor, `title`
sadece mouse hover'da native tarayıcı tooltip'i gösteriyor — klavye
kullanıcısı tam yolu hiç göremiyor. Task #251'de kurulan emsal (component
içine gömülü `<style>` + CSS class, satır 42-64) bu task'ta da takip
edilecek.

## Files to Modify
| File | Why | Risk |
|------|-----|------|
| `ui/src/components/onboarding/OnboardingScreen.tsx` | AC-1..AC-4: `truncateWindowsPath` fonksiyonu ve çağrısı kaldırılacak; `selected-folder-path` elementine CSS truncation (`.onboarding-path` class, `white-space:nowrap`/`overflow:hidden`/`text-overflow:ellipsis`) + `tabIndex={0}` + focus/hover'da açılan bir tooltip (`title` yerine ayrı bir `<span>` + `:hover`/`:focus` görünürlük CSS'i) eklenecek | medium — hem görüntüleme hem etkileşim mantığı değişiyor |
| `ui/src/components/onboarding/OnboardingScreen.test.tsx` | `import { truncateWindowsPath }` kaldırılacak, satır 120'deki `describe('truncateWindowsPath', ...)` bloğu silinecek (fonksiyon artık yok), AC-1..AC-4 için yeni testler eklenecek. **Satır 48 (`not.toBeInTheDocument`) ve diğer 8 test dokunulmadan kalmalı.** | low — sadece ölü kod temizliği + ekleme |
| `ui/e2e/onboarding.spec.ts` | AC-2/AC-3 (klavye/fare tam yol gösterimi) için yeni testler eklenecek. **Satır 34'teki `toHaveText(...)` assertion'ı DOM metnini kontrol ediyor (CSS truncation DOM'u değiştirmez, sadece görsel kesme) — bozulmamalı, ama değişiklik sonrası doğrulanmalı.** | low |

**Not (görsel regresyon):** `OnboardingScreen.tsx` rendered bir web UI
dosyası — `verify` adımında gate 12 (`vision-test`/gerçek ekran görüntüsü)
bu task için de aktif çalışmalı.

## New Files
(Yok — CAVEMAN: task #251'in emsalini (gömülü `<style>` + class) takip
ederek aynı dosyada çözülüyor, ayrı bir tooltip component/dosyası açılmıyor.)

## Dependencies
- Task #251'de kurulan `.onboarding-primary-btn` CSS class deseni — bu
  task'ın yeni class'ı (`.onboarding-path` gibi) aynı `<style>` bloğu
  içinde, aynı isimlendirme konvansiyonuyla (`onboarding-*` öneki)
  eklenmeli (red-team'in #251'de bıraktığı "isimlendirme konvansiyonu
  netleşmeli" notunun karşılığı — bu task onu fiilen kurar).
- `selectedFolder` state'i ve `{selectedFolder && ...}` guard'ı (task #250)
  aynen korunuyor, sadece içindeki render mantığı değişiyor.

## Migration Required?
Hayır — DB/şema ile ilgisi yok, salt frontend görsel/erişilebilirlik
değişikliği.

## Risks
(atdd.md'den taşındı, plan aşamasında somutlaştırıldı)
- `truncateWindowsPath` kaldırılınca `OnboardingScreen.test.tsx`'in import
  satırı (satır 5) da güncellenecek — kod-copilot bunu unutursa TypeScript
  derleme hatası verir (`tsc --noEmit` build gate'i bunu yakalar).
- `ui/e2e/onboarding.spec.ts:34`'teki `toHaveText` assertion'ı teorik olarak
  bozulmamalı (DOM metni aynı kalıyor) ama gerçek Playwright koşumuyla
  doğrulanmadan varsayılmamalı.

## Open Questions
(Yok — atdd.md ve mevcut kod okuması tüm belirsizlikleri kapattı.)
