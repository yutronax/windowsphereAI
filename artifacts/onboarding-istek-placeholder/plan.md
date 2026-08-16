# Plan — onboarding-istek-placeholder
_Reference: atdd.md_

## Files to Modify
| File | Why | Risk |
|------|-----|------|
| `ui/src/components/onboarding/OnboardingScreen.tsx` | AC-1: `request-textarea`'ya `placeholder="Bu klasördeki PDF'leri tarihe göre sırala"` eklenir; `.onboarding-textarea` CSS bloğuna `::placeholder { color: #9CA3AF; }` eklenir (AC-2/AC-3 native tarayıcı davranışı, kod değişikliği gerektirmez). | low |
| `ui/src/components/onboarding/OnboardingScreen.test.tsx` | Mevcut `request textarea (onboarding-istek-metin-kutusu)` describe bloğuna AC-1 (placeholder metni + `::placeholder` rengi) ve AC-2/AC-3 (yazınca kaybolma/silince geri gelme — native davranış, jsdom'da `::placeholder` üzerinden değil `.placeholder` attribute + `.value` üzerinden doğrulanır) için yeni testler eklenir. | low |
| `ui/e2e/onboarding.spec.ts` | AC-2/AC-3 gerçek tarayıcıda placeholder'ın yazınca kaybolup silince geri geldiğini doğrulayan Playwright testleri eklenir; AC-4 mevcut focus/blur testlerinin (satır 132-156) placeholder eklenmesinden sonra da geçtiği teyit edilir (regresyon, yeni test gerekmez — mevcut testler zaten çalışıyor). | low |

## New Files
Yok — mevcut üç dosyaya ek yapılıyor, yeni dosya gerekmiyor.

## Dependencies
- `requestText` state'i ve `onboarding-textarea` class'ı #253'te (`onboarding-istek-metin-kutusu`) zaten kuruldu — bu task sadece `placeholder` attribute'u ve `::placeholder` CSS kuralı ekliyor, state yönetimine dokunmuyor.
- Testler mevcut `describe('request textarea (onboarding-istek-metin-kutusu)')` (unit, satır 121) ve ilgili e2e `test.describe('first-run folder onboarding')` bloklarının (satır 132-156) konvansiyonlarını takip etmeli — `getComputedStyle`/`toHaveCSS` ile stil, `fireEvent.change`/`page.keyboard.type` ile davranış doğrulaması.
- jsdom `::placeholder` pseudo-element stilini `getComputedStyle` ile doğrudan okumaz — unit test seviyesinde placeholder rengi doğrulaması sınırlı olabilir; asıl renk doğrulaması e2e (Playwright, gerçek tarayıcı) seviyesinde yapılmalı. Bu, atdd.md'nin test_strategy'sindeki e2e ağırlığının (%65) gerekçesiyle zaten tutarlı.

## Migration Required?
Hayır — DB/schema değişikliği yok, salt frontend görsel değişiklik.

## Risks
- atdd.md'den taşınan: Yok (dar kapsamlı, tek component, saf görsel değişiklik).
- Yeni bulunan: jsdom'un `::placeholder` pseudo-class rengini `getComputedStyle` ile raporlamaması — unit/integration testinde placeholder metnini ve `placeholder` attribute değerini doğrulamak mümkün, ama rengi (`#9CA3AF`) sadece e2e katmanında (Playwright gerçek tarayıcı) güvenilir şekilde doğrulanabilir. `code-copilot`/`test-copilot` bu ayrımı bilerek test yazmalı.

## Open Questions
Yok.

## Not
`OnboardingScreen.tsx` bir React component (`.tsx`) — bu değişiklik `verify`
adımında gate 11'in (`vision-test`) aktif çalışması gerektiği anlamına
gelir (N/A değil).
