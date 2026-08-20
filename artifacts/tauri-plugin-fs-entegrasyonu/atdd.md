---
task_slug: tauri-plugin-fs-entegrasyonu
jira_id: null
saga_task_id: 279
priority: critical
coverage_target: null
performance_target: null
memory_target: null
test_strategy:
  unit: 70
  integration: 20
  e2e: 10
affected_modules:
  - src-tauri/ (yeni)
  - package.json
  - ui/src/components/onboarding/OnboardingScreen.tsx
  - ui/src/components/onboarding/OnboardingScreen.test.tsx
---

# ATDD — tauri-plugin-fs-entegrasyonu

## Jira Kaynağı
Jira'ya bağlı değil — yerel görev (Saga #279, epic #23 "MVP: Kullanıcı
girişi ve ilk kayıt akışı" altında, RELEASE-BLOCKER, kritik öncelik).

## Persona
Uygulamayı masaüstünde ilk kez açan son kullanıcı (muhasebeci/avukat
segmenti) — klasör seçme ekranıyla karşılaşan kişi. Ayrıca bu görevi
inceleyen red-team/geliştirici.

## Hedef (Neden)
`backend/security.py`'nin whitelist mantığından bağımsız olarak,
frontend'in `OnboardingScreen.tsx`'i `invoke('plugin:fs|exists', {path})`
çağrısını yapıyor ama proje bunu karşılayacak gerçek bir Tauri arka ucuna
(`src-tauri/` + `@tauri-apps/plugin-fs`) hiç sahip değil. Şu an sadece
`vite dev` ile tarayıcıda çalışıyor — bu hem `@tauri-apps/plugin-dialog`'un
`open()` fonksiyonunu (klasör seçme) hem `invoke('plugin:fs|exists', ...)`'i
gerçek bir Tauri penceresi olmadan sessizce çalışmaz hale getiriyor. 2026-08-17
tarihli bağımsız red-team incelemesi bunu HIGH severity işaretledi: paketlenip
gerçek kullanıcıya ulaşırsa, komut Rust tarafında kayıtlı olmadığı için HER
klasör "erişilemez" reddedilir — onboarding kalıcı bir çıkmaz sokak olur,
mevcut mock-tabanlı testler yeşil kaldığı için bu hiçbir CI sinyalinde
görünmez.

## User Story
As a masaüstü uygulamasını ilk açan kullanıcı
I want klasör seçme ekranının gerçek bir Tauri penceresinde gerçekten
çalışmasını
So that onboarding akışı gerçek kullanıma çıktığında çalışmayan bir
çıkmaz sokağa dönüşmesin

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. [Critical] Given proje kök dizini, When `tauri init` (Tauri v2) ile
   scaffold çalıştırılır, Then `src-tauri/` klasörü (Cargo.toml,
   tauri.conf.json, src/main.rs) oluşur ve mevcut `ui/` frontend'ini
   (vite build çıktısını) doğru şekilde referans alır.
2. [Critical] Given `src-tauri/`, When `@tauri-apps/plugin-fs` hem npm
   (`package.json`) hem Cargo (`src-tauri/Cargo.toml`) tarafında eklenir
   ve Rust tarafında kayıt edilir (`tauri::Builder` içinde
   `.plugin(tauri_plugin_fs::init())`), Then `plugin:fs|exists` komutu
   gerçek bir Tauri penceresinde çağrılabilir hale gelir (artık "kayıtlı
   değil" hatası vermez).
3. [Critical] Given `OnboardingScreen.tsx`'teki
   `invoke<boolean>('plugin:fs|exists', { path })` çağrısı, When gerçek
   `@tauri-apps/plugin-fs` API'sinin dönüş tipi/parametre imzasıyla
   karşılaştırılır, Then uyuşmazlık varsa kod gerçek API'ye göre düzeltilir
   VE `OnboardingScreen.test.tsx`'teki `vi.mock` sözleşmesi de aynı
   şekilde güncellenir (davranış — var/yok bilgisi — değişmez, sadece
   çağrı sözleşmesi doğrulanır/düzeltilir).
4. [Critical] Given `npm run dev` yerine gerçek `tauri dev` ile açılan bir
   masaüstü penceresi, When kullanıcı "Klasör Seç" butonuna tıklayıp
   gerçek bir klasör seçer, Then klasörün yolu ekranda görünür VE
   erişilebilirlik kontrolü gerçek dosya sisteminden doğru sonuç döner
   (var olan klasör → kabul, olmayan/erişilemeyen klasör → "Seçilen
   klasöre erişilemiyor" mesajı) — bu, kullanıcının kendi gözlemiyle
   (ekran görüntüsü/log) manuel olarak onayladığı adımdır.
5. [High] Given vite 5→8 ve vitest 2→4 yükseltmesi (Saga #278), When
   gerçek `tauri dev` build'i çalıştırılır, Then bu yükseltmenin native
   Tauri webview'de sorunsuz çalıştığı (derleme hatası/runtime hatası
   yok) doğrulanır.
6. [Medium] Given mevcut `OnboardingScreen.test.tsx`'teki mock-tabanlı
   testler, When AC-3'teki düzeltmeler sonrası çalıştırılır, Then hepsi
   regresyonsuz PASS kalır.

## Davranış Sözleşmesi (hangi durumda ne döner)
| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path: gerçek Tauri penceresinde var olan bir klasör seçilir | `invoke('plugin:fs|exists', ...)` → `true` | `selectedFolder` state'i set edilir, `isFolderInvalid=false` | Klasör yolu ekranda görünür, "Devam" butonu aktif olur | AC-4 |
| 2 | Girdi geçersiz: seçilen klasör silinmiş/erişilemez | `invoke(...)` → `false` | `isFolderInvalid=true` | "Seçilen klasöre erişilemiyor. Lütfen başka bir klasör seçin." mesajı, buton disable | AC-4 |
| 3 | Kaynak yok: plugin-fs Rust tarafında kayıtlı DEĞİL (bu görev tamamlanmadan önceki mevcut durum) | `invoke(...)` reddedilir (Promise reject) | Mevcut `catch { isAccessible = false }` bloğu yakalar | Aynı "erişilemiyor" mesajı gösterilir — kullanıcı için "gerçekten yok" ile "plugin kayıtlı değil" ayırt edilmez (kullanıcı onayı: bu MEVCUT davranış, bu görev DEĞİŞTİRMİYOR) | AC-2 (bu durumun bir daha oluşmaması AC-2'nin amacı) |
| 4 | Yetkisiz erişim | Uygulanmıyor — tek kullanıcılı masaüstü uygulaması, OS-seviyesi dosya izinleri `plugin:fs|exists`'in kendi hata yakalamasına (case 3 ile aynı yol) düşer, ayrı bir AC gerektirmiyor. | — | — | — |
| 5 | Dış bağımlılık hatası (ağ/DB/API) | Uygulanmıyor — bu görev salt yerel Tauri IPC + dosya sistemi, ağ/DB/API çağrısı yok. | — | — | — |
| 6 | Zaman aşımı | Uygulanmıyor — `invoke` senkron IPC round-trip, ayrı bir timeout mekanizması bu görevin kapsamında değil (mevcut kodda da yok). | — | — | — |
| 7 | **Kısmi başarı**: scaffold kuruldu ama plugin-fs Cargo tarafında kayıt edilmedi (yarım kalmış entegrasyon) | `invoke('plugin:fs|exists', ...)` yine reddedilir — case 3 ile AYNI davranışa düşer, "yarı başarı" görünümü yok | Case 3 ile aynı | Case 3 ile aynı ("erişilemiyor" mesajı) | AC-2 |
| 8 | **Hiçbir şey yapılamadı ama hata da yok** | Olanaksız — `invoke` ya `true`/`false` çözer ya reject eder, üçüncü sessiz bir dal yok; mevcut kod zaten bunu `try/catch` ile kapsıyor. | — | — | — |

Kısmi başarı: 7. satırda tanımlı — scaffold/plugin kurulumu yarım kalırsa
kullanıcı "gerçekten erişilemez" ile "altyapı eksik" arasındaki farkı
göremez, ama bu MEVCUT (görev öncesi de var olan) davranış, kullanıcı
onayıyla bu görevin kapsamında değiştirilmiyor — AC-2/AC-4 zaten bu
durumun (yarım kalmış kurulum) hiç YAŞANMAMASINI garanti ediyor.
Hiçbir şey yapılamadı ama hata da yok: Olanaksız — case 8'de açıklandığı
gibi `invoke` her zaman resolve veya reject eder.
Boş sonuç ↔ hata ayrımı: Uygulanmıyor — `plugin:fs|exists` bir boolean
döndürür (var/yok), "boş sonuç" kavramı yok; "yok" (case 2) ile "plugin
kayıtlı değil" (case 3) kullanıcıya AYNI mesajla gösteriliyor — bu ayrım
şu an yapılmıyor ve kullanıcı onayıyla bu görevin kapsamı dışında
bırakıldı (Assumptions'a not edildi).

## Test Strategy
Unit: 70% — `OnboardingScreen.test.tsx`'teki mevcut `vi.mock`-tabanlı
testler, AC-3'teki gerçek API sözleşmesine göre güncellenir, hepsi
regresyonsuz geçmeli.
Integration: 20% — `src-tauri/`'de `plugin:fs|exists` komutunun gerçekten
kayıtlı olduğunu doğrulayan bir kontrol (ör. `tauri.conf.json`/Rust kod
incelemesi + `cargo check`).
E2E: 10% — manuel `tauri dev` smoke test (AC-4), kullanıcının kendi
gözlemiyle onaylanır. Otomatik native-webview e2e (tauri-driver/WebDriver)
bu görevin kapsamı DIŞINDA (kullanıcı onayı — kapsam çok büyürdü).

## Benchmark / Başarı Ölçütü
Coverage Target: Belirtilmedi (kullanıcı onayı — bu bir altyapı/entegrasyon
görevi, sayısal coverage hedefi yerine ikili başarı ölçütü kullanılıyor).
Diğer ölçülebilir kriterler:
- `tauri dev` ile açılan gerçek pencerede klasör seçimi ÇALIŞIYOR (evet/hayır,
  kullanıcı manuel onayı).
- Mevcut `OnboardingScreen.test.tsx` suite'i regresyonsuz PASS.
- `cargo check` (src-tauri/) hatasız tamamlanır.
- vite 8/vitest 4 yükseltmesinin native build'i bozmadığı doğrulanır (AC-5).

## Kapsam Dışı
- `.exe`/installer paketleme akışının (`tauri build`) kurulması — ayrı bir
  paketleme görevi/epic'in konusu (kullanıcı onayı).
- CI/CD pipeline'ına Tauri build adımı ekleme — bu görev yerel geliştirme
  ortamını kapsıyor (kullanıcı onayı).
- Backend-Tauri iletişim modelinin (sidecar process vb.) yeniden
  tasarlanması — şu an backend ayrı bir FastAPI process olarak
  `BACKEND_ORIGIN` sabit URL'i üzerinden çağrılıyor, bu görev bu modeli
  DEĞİŞTİRMİYOR, sadece mevcut modelin Tauri penceresinde de çalıştığını
  doğruluyor (kullanıcı onayı).
- Otomatik native-webview e2e test altyapısı (tauri-driver) kurulumu —
  manuel smoke test yeterli kabul edildi (kullanıcı onayı).
- "Plugin kayıtlı değil" ile "klasör gerçekten yok" durumlarını kullanıcıya
  ayrı mesajlarla gösterme — mevcut davranış korunuyor (kullanıcı onayı,
  bkz. Davranış Sözleşmesi case 2 vs 3).

## Etkilenen Dosyalar/Modüller (bilinen)
- `src-tauri/` (yeni: Cargo.toml, tauri.conf.json, src/main.rs)
- `package.json` (yeni Cargo/npm bağımlılığı: `@tauri-apps/plugin-fs`, zaten
  `@tauri-apps/api`/`@tauri-apps/plugin-dialog` mevcut)
- `ui/src/components/onboarding/OnboardingScreen.tsx`
- `ui/src/components/onboarding/OnboardingScreen.test.tsx`

## Rollback Beklentisi
Uygulanmıyor — bu bir altyapı ekleme görevi, mevcut çalışan davranışı
(hiçbiri, çünkü şu an gerçek Tauri'de hiç çalışmıyor) bozmuyor. Sorun
çıkarsa standart `git revert` yeterli, runtime rollback mekanizması
gerektirmez.

## Risks
- (görev açıklamasından) vite 8 ile `@vitejs/plugin-react@4.7.0` arasında
  `npm ls` ELSPROBLEMS/invalid uyarısı var — AC-5 ile bu riskin native
  build'de gerçek bir soruna yol açıp açmadığı doğrulanacak.
- Tauri v2 scaffold'unun mevcut `ui/` klasör yapısıyla (frontend zaten
  ayrı bir kök dizinde) doğru entegre olması gerekiyor — `tauri.conf.json`'ın
  `frontendDist`/`devUrl` ayarlarının `vite.config.ts`'teki port/build
  çıktısıyla uyumlu olması plan aşamasında doğrulanmalı.

## Assumptions
- "Plugin kayıtlı değil" ile "klasör gerçekten erişilemez" durumlarının
  kullanıcıya aynı mesajla gösterilmesi kabul edilebilir bir sınırlama
  olarak varsayıldı (kullanıcı onayladı, ayrı bir hata mesajı istemedi).
- Rust toolchain (cargo/rustc) bu oturumda `rustup default stable` ile
  zaten kuruldu (1.97.1) — plan/code-copilot adımlarının bunu yeniden
  kurmasına gerek yok.

## Unknowns
- `tauri.conf.json`'ın `frontendDist`/`devUrl` değerlerinin `vite.config.ts`
  ile tam olarak nasıl eşleşeceği — plan aşamasında `vite.config.ts`
  okunarak netleştirilecek.

## Sorular ve Cevaplar (ham kayıt)
1. Tauri sürümü? → v2 (package.json'daki mevcut paketlerle uyumlu).
2. Smoke test kapsamı? → Manuel `tauri dev` + elle klasör seçimi, otomatik
   native-e2e kapsam dışı.
3. Mock/gerçek API uyuşmazlığı olursa ne olur? → Gerçek API'ye göre kod
   düzeltilir, mock da güncellenir.
4. Kapsam dışı bırakılacaklar? → .exe paketleme, CI/CD entegrasyonu,
   backend-Tauri iletişim modeli tasarımı.
5. Plugin kayıtlı değilse davranış? → Mevcut catch bloğu yeterli,
   isAccessible=false, ayrı bir hata mesajı yok.
6. Kabul kriteri sahibi? → Kullanıcı manuel smoke test'i görüp onaylar.
7. Test stratejisi oranı? → unit %70 / integration %20 / e2e-manuel %10.
8. Benchmark/coverage hedefi? → Sayısal hedef yok, "gerçekten çalışıyor"
   ikili kanıtı yeterli.
9. Persona/Hedef/Happy path/Bağımlılıklar → Saga #279 görev açıklamasından
   (kullanıcı mesajından, tekrar sorulmadı).
