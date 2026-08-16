# Plan — bos-istek-engelleme
_Reference: atdd.md_

## Files to Modify
| File | Why | Risk |
|------|-----|------|
| ui/src/components/onboarding/OnboardingScreen.tsx | `requestText` boş/whitespace-only iken "Devam" tıklamasında `onContinue` çağrılmasını engelleyecek bir `isRequestEmpty` local state + submit handler eklenecek; textarea'ya koşullu `#DC2626` kenarlık class'ı ve altına `aria-live="polite"` içeren hata mesajı satırı eklenecek. Mevcut `.onboarding-textarea:focus` kuralıyla çakışmaması için hata durumunda kenarlık rengi `!important` yerine daha spesifik bir `.onboarding-textarea.has-error` selector'ıyla önceliklendirilecek (bkz. atdd.md Risks). | medium |
| ui/src/components/onboarding/OnboardingScreen.test.tsx | AC-2..AC-6 için yeni `describe` bloğu: boş/whitespace submit, hata temizleme (input değişince anında kaybolma), tekrar boş bırakınca hatanın yeniden görünmesi, `aria-live="polite"` varlığı. | low |
| ui/e2e/onboarding.spec.ts | Gerçek tarayıcıda: klasör seçili + boş/whitespace istekle "Devam"a basınca kırmızı kenarlık + mesajın DOM'da görünmesi, yazmaya başlayınca kaybolması (AC-2, AC-3, AC-4). | low |

## New Files
Yok — mevcut üç dosyaya ekleme yapılıyor, yeni component/dosya gerekmiyor.

## Dependencies
- `OnboardingScreen.tsx`'in mevcut `requestText`/`useState` state mimarisiyle tutarlı kalınacak (yeni bir `isSubmitted`/`isRequestEmpty` state'i aynı component içinde).
- `App.tsx:27`'deki `onContinue={() => {}}` no-op olarak KALACAK — bu plan `onContinue`'nun içeriğini değiştirmiyor, sadece boş/whitespace durumunda çağrılmamasını sağlıyor (atdd.md Kapsam Dışı ile uyumlu).
- Var olan test pattern'leri birebir izlenecek: `screen.getByTestId('request-textarea')`, `screen.getByRole('button', { name: /devam/i })`, `fireEvent.change`/`fireEvent.click` (unit); `page.getByTestId(...)`, `page.getByRole(...)` (e2e).
- Mevcut `.onboarding-textarea:focus` (border `#2563EB`) ve default border (`#E5E7EB`) kurallarıyla yeni `has-error` kuralının çakışmaması gerekiyor — CSS'te error class'ı focus'tan sonra tanımlanıp `!important` KULLANILMADAN selector özgüllüğüyle (örn. `.onboarding-textarea.has-error`) çözülecek; hata varken focus olursa da kırmızı kenarlık öncelikli kalmalı (kullanıcı hâlâ hatalı durumda olduğunu görmeli).

## Migration Required?
No — DB/schema değişikliği yok, saf frontend state + CSS değişikliği.

## Risks
- (atdd.md'den taşındı) Hata kenarlığı ile mevcut focus/blur kenarlık renkleri arasındaki CSS önceliği — yukarıda "Dependencies"te çözüm yaklaşımı belirtildi, code-copilot bunu uygularken doğrulamalı (hem hatalı+focus'lu hem hatalı+focus'suz durumlar test edilmeli).
- `App.tsx`'teki `onContinue={() => {}}` no-op olduğu için, code-copilot'un "geçerliyse çağrılsın" AC-1 davranışını test ederken gerçek bir mock `onContinue` fonksiyonu (`vi.fn()`) kullanması gerekiyor — `App.tsx`'e dokunulmayacak.

## Open Questions
Yok — atdd.md'deki 10 soru-cevap ve CSS önceliği konusundaki varsayım (Dependencies bölümü) planı netleştirmeye yetti, code-copilot'a sorulacak açık bir soru kalmadı.

## Not
`OnboardingScreen.tsx` bir React component'i (rendered web UI) — bu, `verify` adımında gate 11'in (`vision-test`) N/A değil AKTİF çalışacağı anlamına gelir; kırmızı kenarlık (#DC2626) rengi ve mesaj konumu ekran görüntüsüyle doğrulanmalı.
