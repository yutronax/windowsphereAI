---
task_slug: klasor-path-kok-surucu-normalize
jira_id: null
saga_task_id: null
priority: low
coverage_target: 80
performance_target: null
memory_target: null
test_strategy:
  unit: 100
  integration: 0
  e2e: 0
affected_modules:
  - ui/src/components/onboarding/OnboardingScreen.tsx (chooseFolder path normalize)
---

# ATDD — klasör path kök sürücü normalize edge-case'i

## Jira Kaynağı
Yok — Saga #256'nın (gecersiz-klasor-reddi) devlog notundan taşınan, o zaman
düzeltilmemiş bir "known low-severity" bulgu.

## Persona
Windows kullanıcısı, onboarding ekranında bir sürücünün KÖKÜNÜ (ör. `C:\`,
`D:\`) çalışma klasörü olarak seçen kişi.

## Hedef (Neden)
`OnboardingScreen.tsx:35`'teki `folder.replace(/[\\/]+$/, '')` TÜM trailing
slash/backslash'leri koşulsuz siler. Windows path semantiğinde `C:\` (sürücü
KÖKÜ, mutlak) ile `C:` (sürücüdeki GEÇERLİ ÇALIŞMA DİZİNİ, sürücüye-göreli)
FARKLI anlamlara gelir. Kullanıcı sürücü kökünü seçtiğinde normalize
`C:\` → `C:`'ye indirger — bu, `plugin:fs|exists` çağrısına ve backend'e
gönderilen `selectedFolder`'a yanlış (drive-relative, mutlak DEĞİL) bir path
sızdırır.

## User Story
As a Windows kullanıcısı
I want bir sürücünün kökünü (`C:\`) çalışma klasörü olarak seçtiğimde bunun
`C:` olarak (anlamı değişecek şekilde) normalize edilmemesini
So that seçtiğim klasörün gerçekten seçtiğim mutlak kök olduğundan emin
olabileyim

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. [Critical] Given kullanıcı `C:\` (tek harf + `:` + tek backslash) seçer,
   When path normalize edilir, Then sonuç `C:\` olarak KALIR (backslash
   silinmez), `plugin:fs|exists`'e `C:\` gönderilir.
2. [Critical] Given kullanıcı `C:/` (forward slash varyantı) seçer, When
   normalize edilir, Then sonuç `C:\` (Windows kanonik backslash formuna)
   normalize edilir — çıplak `C:` DEĞİL.
3. [High] Given kullanıcı `C:\Users\Yusuf\Belgeler\` (kök OLMAYAN, alt
   klasörlü bir path, sonda backslash) seçer, When normalize edilir, Then
   mevcut davranış KORUNUR — sonuç `C:\Users\Yusuf\Belgeler` (trailing
   backslash silinir, mevcut regresyon testi AC-4 kırılmaz).
4. [High] Given kullanıcı `C:\\\\` (birden fazla ardışık backslash, sürücü
   kökü) seçer, When normalize edilir, Then sonuç tek bir `C:\`'ye indirgenir
   (ne çıplak `C:`, ne fazladan backslash).
5. [Medium] Given kullanıcı `D:` gibi backslash'siz çıplak bir sürücü harfi
   döndüren bir path seçer (nadir ama `open()` diyaloğundan teorik olarak
   mümkün), When normalize edilir, Then dokunulmaz KALIR (zaten normalize
   edilecek trailing slash yok, davranış değişmez — bu AC'nin amacı `C:\`'yi
   YANLIŞLIKLA `C:`'ye indirgemeyi önlemek, `C:`'yi `C:\`'ye ÇEVİRMEK değil;
   kapsam dışı).

## Davranış Sözleşmesi
| # | Girdi (`open()` dönüşü) | Normalize sonucu | Değişti mi? |
|---|---|---|---|
| 1 | `C:\` | `C:\` | EVET (önceden `C:` oluyordu — bug) |
| 2 | `C:/` | `C:\` | EVET (önceden `C:` oluyordu — bug) |
| 3 | `C:\Users\Yusuf\Belgeler\` | `C:\Users\Yusuf\Belgeler` | HAYIR (mevcut davranış) |
| 4 | `C:\\\\` (çoklu backslash, kök) | `C:\` | EVET (önceden `C:` oluyordu — bug) |
| 5 | `C:\Users\Yusuf\Belgeler` (zaten temiz) | `C:\Users\Yusuf\Belgeler` | HAYIR |
| 6 | `D:` (trailing slash yok, çıplak sürücü) | `D:` | HAYIR (dokunulmaz, kapsam dışı) |
| 7 | `c:\` (küçük harf sürücü) | `c:\` | EVET — regex `[A-Za-z]` case-insensitive, aynı düzeltme dalı geçerli (red-team ile doğrulandı, ayrı test eklenmedi) |
| 8 | `""` / `"\"` (boş string / sadece backslash, sürücü harfi yok) | dokunulmaz (eski `.replace` dalına düşer: `""` → `""`, `"\"` → `""`) | HAYIR — zararsız, `chooseFolder` zaten `typeof folder !== 'string'` kontrolünden sonra çalışır, `open()` pratikte bu girdiyi üretmez |

## Test Strategy
100% unit/component — `OnboardingScreen.test.tsx`'e yeni testler, `open()`
mock'unun döndürdüğü path varyasyonlarıyla `plugin:fs|exists`'e hangi path'in
gönderildiği ve `selected-folder-path` testid'inin içeriği doğrulanır. Mevcut
AC-4 testi (satır 374-383) regresyon testi olarak KIRILMAMALI.

## Benchmark
Coverage Target: 80% (mevcut dosya coverage'ı zaten yüksek, yeni satırlar
tam kapsanmalı). Performans/bellek hedefi yok (saf string işlemi).

## Kapsam Dışı
- Case-insensitive/symlink normalize (devlog'un "kapsamlı path normalization
  yapılmadı" notunda zaten bilinçli olarak kapsam dışı bırakılmıştı, bu task
  ona dokunmuyor).
- UNC path'ler (`\\server\share`) — ayrı bir edge-case, bu task'ın kapsamında
  değil.
- Backend tarafı (`backend/security.py`) path normalize'ı — bu SADECE
  frontend'in `plugin:fs|exists`'e ve `/api/session`'a gönderdiği string'i
  düzeltiyor, backend zaten kendi `Path.resolve()`'unu kullanıyor.

## Rollback Beklentisi
Geçerli değil — salt frontend string normalize mantığı, dosya sistemi
yazmıyor.

## Risks
Yok — saf, yan etkisiz bir string dönüşümü.

## Assumptions
`open({ directory: true })` (Tauri dialog) her zaman ya tam kök (`C:\`) ya da
`\`/`/` içermeyen normal bir path döndürür; regex tabanlı bu düzeltme
yalnızca "sürücü harfi + `:` + (opsiyonel ardışık slash/backslash)" özel
durumunu diğer trailing-slash temizleme davranışından ayırır.

## Unknowns
Yok.
