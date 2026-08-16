# Code Diff — onboarding-istek-placeholder

> **Not:** Codex CLI kotası dolu olduğu için (bkz. test_diff.md), kullanıcı
> onayıyla implementasyon istisnai olarak Claude tarafından yazıldı.

## `ui/src/components/onboarding/OnboardingScreen.tsx`

1. `request-textarea`'ya `placeholder="Bu klasördeki PDF'leri tarihe göre sırala"` attribute'u eklendi (AC-1).
2. `.onboarding-textarea` CSS bloğuna yeni bir kural eklendi:
   ```css
   .onboarding-textarea::placeholder {
     color: #9CA3AF;
   }
   ```
   (AC-1 — düşük kontrast rengi)

Değişiklik 2 satır ekleme (CSS kuralı) + 1 satır ekleme (attribute), mevcut
`requestText` state yönetimine ve diğer JSX'e dokunulmadı. AC-2/AC-3
(yazınca kaybolma / silince tekrar görünme) tarayıcının native
`placeholder` davranışıyla otomatik sağlanıyor, ek kod gerekmedi.

## Doğrulama
- `npm run build` (tsc --noEmit + vite build): temiz, hata yok.
- Görsel doğrulama: dev server'da (`http://127.0.0.1:4173`) manuel
  ekran görüntüsü alındı — placeholder metni görünür ve gerçek yazılan
  metinden belirgin şekilde daha soluk (gri) renkte.
