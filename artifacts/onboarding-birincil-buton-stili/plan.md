# Plan — onboarding-birincil-buton-stili
_Reference: atdd.md_

## Bağlam
Proje henüz bir CSS framework/dosya konvansiyonu seçmedi — `ui/src` altında
hiçbir `.css` dosyası yok (`find ui/src -iname "*.css"` boş döndü).
`OnboardingScreen.tsx`'teki "Klasör Seç" butonu şu an düz
`<button type="button" onClick={chooseFolder} disabled={!isReady}>` —
hiçbir stil yok.

## Files to Modify
| File | Why | Risk |
|------|-----|------|
| `ui/src/components/onboarding/OnboardingScreen.tsx` | "Klasör Seç" butonuna AC-1..AC-4'ü karşılayan stil eklenecek (inline style objesi — proje henüz CSS dosyası konvansiyonu seçmediği için, atdd.md Assumptions) | low — mevcut davranış (onClick, disabled mantığı) değişmiyor, sadece görsel katman ekleniyor |
| `ui/src/components/onboarding/OnboardingScreen.test.tsx` | AC-1, AC-2, AC-3 için computed-style doğrulayan yeni testler eklenecek, mevcut testler bozulmamalı | low |
| `ui/e2e/onboarding.spec.ts` | AC-4, AC-5 için gerçek tarayıcıda hover/active/kontrast doğrulaması eklenecek | low |

**Not (görsel regresyon):** `OnboardingScreen.tsx` bir rendered web UI
dosyası — `verify` adımında gate 12 (`vision-test`) bu task için aktif
çalışmalı, N/A geçilmemeli.

## New Files
(Yok — CAVEMAN minimalizm: proje henüz CSS dosyası konvansiyonu seçmediği
için ayrı bir `.css`/`.module.css` dosyası açmak yerine mevcut dosyaya
inline style eklemek yeterli ve daha az dosya/karmaşıklık demek.)

## Dependencies
Yok — bu değişiklik hiçbir başka modülü çağırmıyor, sadece JSX içindeki
`<button>` elementinin `style` prop'unu genişletiyor. `chooseFolder`/`isReady`
mantığı aynen korunuyor.

## Migration Required?
Hayır — DB/şema ile ilgisi yok, salt frontend görsel değişiklik.

## Risks
(atdd.md'den aynen taşındı) Bu task'ın seçtiği stil yöntemi sonraki stil
task'larına (Devam düğmesi, metin kutusu — #253/#254/#255) emsal oluşturacak.

**Gerçekleşen uygulama notu (red-team sonrası eklendi):** Saf inline `style`
prop'u değil, component içine gömülü bir `<style>` bloğu + `.onboarding-primary-btn`
CSS class'ı kullanıldı — çünkü `:hover`/`:active`/`:focus-visible` gibi gerçek
pseudo-class davranışları saf inline style ile mümkün değil. **Sonraki stil
task'ları (#253/#254/#255) bu emsali (gömülü `<style>` + class) takip
etmeli**, sadece "inline style" varsayımını kullanmamalı. CSS class adları
için henüz bir isimlendirme konvansiyonu (`onboarding-*` öneki gibi)
netleşmedi — #253'e kadar kararlaştırılmalı (red-team bulgusu, düşük risk
ama birikimli).

## Open Questions
(Yok — atdd.md tüm kararları netleştirdi, plan aşamasında yeni bir belirsizlik
çıkmadı.)
