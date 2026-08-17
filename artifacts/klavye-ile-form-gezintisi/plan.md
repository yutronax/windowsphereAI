# Plan — klavye-ile-form-gezintisi
_Reference: atdd.md_

## Files to Modify
| File | Why | Risk |
|------|-----|------|
| ui/src/components/onboarding/OnboardingScreen.tsx | İki yeni `useRef` (`chooseFolderButtonRef: HTMLButtonElement`, `requestTextareaRef: HTMLTextAreaElement`) eklenip ilgili elementlere bağlanacak. `selected-folder-path` `<p>`'ye `onKeyDown` eklenip Enter'da `handleContinueClick()` çağrılacak (AC-3, AC-4) — bu, native buton davranışına sahip olmayan TEK odaklanabilir non-button eleman. `handleContinueClick` içinde `isRequestEmpty` `true` olduğunda `requestTextareaRef.current?.focus()` çağrılacak (AC-4). `chooseFolder` içinde `isFolderInvalid` `true` olduğunda (invoke `false` döner veya reddedilirse) `chooseFolderButtonRef.current?.focus()` çağrılacak (AC-5). "Klasör Seç" ve "Devam" butonlarına YENİ bir `onKeyDown` eklenmez — ikisi de zaten native `<button>` elementi, tarayıcı Enter'da otomatik olarak kendi `onClick`'ini tetikler (AC-3'ün Devam-butonu kısmı ve AC-6 bu native davranışa dayanıyor, ek kod gerektirmiyor — atdd.md Assumptions). `.focus()` çağrıları senkron yapılabilir çünkü hem buton hem textarea DOM'da HER ZAMAN mevcut (koşullu render edilmiyor, sadece `disabled`/`className` koşullu) — atdd.md'nin Risks bölümündeki "commit sonrası focus" endişesi bu yüzden geçerli değil, `useEffect` gerekmiyor. | medium |
| ui/src/components/onboarding/OnboardingScreen.test.tsx | Yeni testler: (a) textarea'da Enter'ın submit tetiklemediği (AC-2, regresyon-koruması), (b) `selected-folder-path` odaklıyken Enter — form geçerliyse `onContinue` çağrılır (AC-3), form geçersizse (boş istek) hata gösterilip odak textarea'ya gider (AC-4), (c) erişilemez klasör sonrası `document.activeElement`'in "Klasör Seç" butonu olduğu (AC-5). "Devam"/"Klasör Seç" butonlarının Enter'da native tetiklenmesi jsdom'da güvenilir simüle edilemediği için (tarayıcının varsayılan Enter→click eylemi jsdom'da uygulanmıyor) bu iki senaryo unit'te DEĞİL, sadece e2e'de test edilecek — atdd.md Unknowns'ta bu netleştirildi. | low |
| ui/e2e/onboarding.spec.ts | Gerçek tarayıcıda: (a) `page.keyboard.press('Tab')` ile tam sıra doğrulaması (AC-1), (b) "Devam" butonu odaklıyken `page.keyboard.press('Enter')` ile submit (AC-3, native davranış — bu ortamda gerçekten test edilebilir), (c) "Klasör Seç" butonu odaklıyken Enter'ın hâlâ dialog açtığı (AC-6, regresyon), (d) hata sonrası odak taşımanın gerçek tarayıcıda da doğrulanması (AC-4, AC-5). | low |

## New Files
Yok — mevcut dosyalara ekleme yapılıyor.

## Dependencies
- Mevcut `handleContinueClick`/`chooseFolder` fonksiyonlarının imzası değişmiyor, içlerine ek satırlar ekleniyor — Saga #255/#256'daki mantık (boş istek kontrolü, klasör erişilebilirlik kontrolü) korunuyor, üzerine odak taşıma ekleniyor.
- `selected-folder-path` `<p>`'nin mevcut `onFocus`/`onBlur`/`onMouseEnter`/`onMouseLeave` (tooltip için, Saga öncesi task) handler'ları KORUNUYOR, sadece yeni bir `onKeyDown` ekleniyor — birbirini ezmeyecek şekilde ayrı prop.
- CSS'e dokunulmuyor — mevcut `:focus-visible` odak halkası stilleri zaten var, yeni bir görsel stil gerekmiyor (atdd.md Benchmark bölümüyle uyumlu).

## Migration Required?
No — DB/schema değişikliği yok, saf frontend state/ref/odak mantığı.

## Risks
- (atdd.md'den taşındı, ÇÖZÜLDÜ) Hata sonrası `.focus()`'un React commit döngüsüyle zamanlaması: yukarıda açıklandığı gibi hedef elementler koşulsuz render edildiği için `ref.current` her zaman geçerli — `useEffect` gerekmiyor, risk ortadan kalktı.
- (atdd.md'den taşındı, plan ile netleşti) "Klasör Seç"/"Devam" butonlarının native Enter davranışına güvenme riski: unit testler bunu kapsamayacak (jsdom sınırlaması), sadece e2e kapsayacak — bu, test stratejisinin unit/e2e dağılımını etkiliyor ama atdd.md'nin 70/30 hedefiyle hâlâ uyumlu (AC-1/AC-3-buton/AC-6 e2e ağırlıklı, AC-2/AC-3-path/AC-4/AC-5 unit ağırlıklı).
- `selected-folder-path`'e yeni `onKeyDown` eklenmesi, mevcut `onFocus`/tooltip davranışıyla çakışmamalı — Enter'a basmak zaten önce elementi focus'a getirmiş olacağından (tooltip zaten görünür), submit tetiklenmesi tooltip görünürlüğünü etkilememeli. Implementasyon sırasında test edilecek.

## Open Questions
Yok — atdd.md'deki 10 soru-cevap ve yukarıdaki native-buton-davranışı netleştirmesi (Assumptions/Unknowns çözümü) planı tamamlamaya yetti.

## Not
`OnboardingScreen.tsx` bir React component'i (rendered web UI) — ancak bu task'ın odağı DOM state'i (`document.activeElement`, odak sırası) olduğu için, `verify` adımında gate 12'nin (`vision-test`/ekran görüntüsü) katkısı sınırlı: odak DOM'da test edilebilir bir durum, görsel olarak "focus ring" zaten var olan CSS ile aynı görünür. Yine de regresyon kontrolü için bir tur önerilir (atdd.md Benchmark ile uyumlu).
