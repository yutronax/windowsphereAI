# Code Diff — bos-istek-engelleme
_Reference: atdd.md, plan.md, test_diff.md_

> **Not:** Codex kotası dolu (bkz. proje hafızası "Codex Kotası Tükendi",
> 2026-09-15'e kadar); bu task'ta implementasyon istisnai olarak Claude
> tarafından yazıldı, kullanıcının 2026-08-16 talimatına dayanarak (`saga`
> skill Bölüm C override'ı). Bağımsız `red-team` subagent doğrulaması ayrıca
> çalıştırılacak/çalıştırıldı — commit öncesi pazarlıksız adım.

## Değiştirilen Dosya
`ui/src/components/onboarding/OnboardingScreen.tsx`

### Eklenen state ve handler'lar
- `isRequestEmpty` (`useState<boolean>`) — hata görünür mü kontrolü.
- `handleRequestTextChange(value)` — `requestText`'i günceller; hata gösteriliyorsa
  ve yeni değer trim edilince boş değilse hatayı anında temizler (AC-4).
- `handleContinueClick()` — `requestText.trim() === ''` ise `isRequestEmpty(true)`
  yapıp `return`; `onContinue()` çağrılmaz. Aksi halde doğrudan `onContinue()`
  çağrılır (AC-1, AC-2, AC-3, AC-6).

### CSS (mevcut `<style>` bloğuna eklendi)
```css
.onboarding-textarea.has-error {
  border-color: #DC2626;
}
.onboarding-textarea.has-error:focus {
  border-color: #DC2626;
  box-shadow: 0 0 0 3px rgba(220, 38, 38, 0.1);
}
.onboarding-error-message {
  color: #DC2626;
  font-size: 14px;
  margin-top: 4px;
}
```
`.has-error:focus` kuralı ayrıca eklendi çünkü `.onboarding-textarea:focus` ile
`.onboarding-textarea.has-error` aynı CSS özgüllüğüne (0,2,0) sahip — sadece
sonradan tanımlanan kural kazanır, bu kırılgan bir sıralama bağımlılığı
yaratır. `.has-error:focus` (0,3,0 özgüllük) bu belirsizliği ortadan kaldırıp
hatalı durumda focus olsa bile kırmızı kenarlığın kalmasını garantiler
(plan.md'deki Risk maddesiyle uyumlu).

### JSX değişiklikleri
- `textarea`'nın `className`'i koşullu: `isRequestEmpty ? 'onboarding-textarea has-error' : 'onboarding-textarea'`.
- `onChange`, `setRequestText` yerine `handleRequestTextChange` çağırıyor.
- `isRequestEmpty` true iken, textarea'dan hemen sonra `aria-live="polite"`
  container içinde `<p className="onboarding-error-message">Devam etmek için
  bir istek yazın.</p>` render ediliyor (AC-5).
- "Devam" butonunun `onClick`'i `onContinue` yerine `handleContinueClick`.
  `disabled` koşulu (`!isReady || !selectedFolder`) DEĞİŞMEDİ — plan.md'de
  belirtildiği gibi klasör seçimi bu task'ın kapsamı dışı.

## Değiştirilmeyen Dosyalar (plan.md ile tutarlı)
- `App.tsx` — `onContinue={() => {}}` no-op olarak kaldı, bu task kapsamında değil.
- Backend (`backend/`) — client-side validasyon, hiçbir API/route değişmedi.

## Doğrulama
- `npx vitest run ui/src/components/onboarding/OnboardingScreen.test.tsx` → 21/21 geçti.
- `npx playwright test ui/e2e/onboarding.spec.ts` → 16/16 geçti.
- `npx tsc --noEmit` → hatasız (temiz derleme).
