# Plan — klasör path kök sürücü normalize edge-case'i

## Dosya Değişiklikleri

### ui/src/components/onboarding/OnboardingScreen.tsx
- `chooseFolder` içindeki tek satır:
  ```ts
  const normalizedPath = folder.replace(/[\\/]+$/, '');
  ```
  şu mantıkla değiştirilir:
  ```ts
  const normalizedPath = /^[A-Za-z]:[\\/]+$/.test(folder)
    ? `${folder[0]}:\\`
    : folder.replace(/[\\/]+$/, '');
  ```
  - `^[A-Za-z]:[\\/]+$` — TÜM string sadece "harf + `:` + bir veya daha fazla
    slash/backslash" ise (yani path'in TAMAMI bir sürücü kökü) özel dal
    devreye girer, tek bir kanonik `X:\` üretir.
  - Aksi halde (kök OLMAYAN her path, ör. `C:\Users\...`) mevcut
    `.replace(/[\\/]+$/, '')` davranışı DEĞİŞMEDEN çalışır.
  - `D:` gibi trailing slash'siz çıplak sürücü harfi bu regex'e uymaz (sonda
    `[\\/]+` yok), dokunulmaz kalır — AC-5 ile tutarlı.

## Test Dosyaları
- `ui/src/components/onboarding/OnboardingScreen.test.tsx`'e yeni `describe`
  bloğu veya mevcut "AC-4" testinin yanına 4 yeni test (AC1-4, davranış
  sözleşmesi satır 1/2/4 + regresyon olarak satır 3 zaten mevcut testte var):
  1. `C:\` seçilince `plugin:fs|exists`'e `C:\` gönderilir, gösterilen path `C:\`.
  2. `C:/` seçilince `plugin:fs|exists`'e `C:\` gönderilir.
  3. `C:\\\\` seçilince `plugin:fs|exists`'e `C:\` gönderilir.
  4. Mevcut AC-4 testi (`C:\Users\Yusuf\Belgeler\` → `C:\Users\Yusuf\Belgeler`) kırılmadan geçer (regresyon).

## Uygulama Sırası
1. Kırmızı: yukarıdaki 3 yeni testi yaz, mevcut buggy koda karşı FAIL ettiğini doğrula.
2. Yeşil: `chooseFolder`'daki tek satırı değiştir, testleri tekrar çalıştır.
3. Tüm `OnboardingScreen.test.tsx` dosyasını çalıştır — regresyon yok.
4. Bağımsız red-team incelemesi.
5. Commit.

## Bağımlılık
Yok.

## Riskler
Regex'in `folder[0]` kullanımı Unicode sürücü harfi varsayımıyla (ASCII
A-Z/a-z) sınırlı — Windows sürücü harfleri zaten her zaman ASCII, risk yok.
