# Plan — tauri-plugin-fs-entegrasyonu
_Reference: atdd.md_

## Files to Modify
| File | Why | Risk |
|------|-----|------|
| package.json | AC-2: `@tauri-apps/plugin-fs` npm bağımlılığı eklenir; `dev`/`build` script'lerinin yanına `tauri`/`tauri dev`/`tauri build` script'leri eklenir (Tauri CLI'nin standart konvansiyonu — `npm run tauri dev` ile scaffold'un `beforeDevCommand`'ı `vite`'ı otomatik tetikler). | low |
| ui/src/components/onboarding/OnboardingScreen.tsx | AC-3: `invoke<boolean>('plugin:fs|exists', { path })` çağrısının gerçek `@tauri-apps/plugin-fs` API sözleşmesiyle (parametre adı/tipi) uyumlu olduğu doğrulanacak; gerekirse düzeltilecek. | medium |
| ui/src/components/onboarding/OnboardingScreen.test.tsx | AC-3/AC-6: `vi.mock('@tauri-apps/api/core', ...)` sözleşmesi, AC-3'te yapılan gerçek-API düzeltmesiyle senkron kalmalı; mevcut `invokeTauriCommand` assert'leri (`toHaveBeenCalledWith('plugin:fs|exists', { path: ... })`, satır 316/382) TAM OLARAK bu sözleşmeyi doğruluyor — kod değişirse bu assert'ler de güncellenmeli. | low |

## New Files
| File | Purpose |
|------|---------|
| src-tauri/Cargo.toml | AC-1: Tauri v2 Rust paketi manifest'i (`tauri`, `tauri-plugin-fs` bağımlılıkları). |
| src-tauri/tauri.conf.json | AC-1: uygulama meta verisi + `build.beforeDevCommand`/`build.devUrl`/`build.frontendDist` — `vite.config.ts`'in dev server'ına (varsayılan port 5173) ve `vite build` çıktısına (varsayılan `dist/`) işaret etmeli. `dist/` klasörü zaten kökte var (mevcut vite build çıktısı) — çakışma olup olmadığı kontrol edilmeli (aşağıda Open Questions). |
| src-tauri/src/main.rs | AC-1/AC-2: `tauri::Builder::default().plugin(tauri_plugin_fs::init())...run(...)` — `plugin:fs|exists` komutunu gerçekten kayıt eder. |
| src-tauri/Cargo.lock | `cargo` tarafından otomatik üretilir (scaffold sırasında). |
| src-tauri/capabilities/*.json veya tauri.conf.json içindeki `app.security.capabilities` | Tauri v2 zorunlu izin modeli: `fs:allow-exists` (veya benzeri) permission'ının capability dosyasına eklenmesi gerekiyor — AKSİ HALDE komut kayıtlı olsa bile izin reddi (`invoke` reject) alınır. Bu, atdd.md'nin AC-2'sinin bir parçası ama görev açıklamasında açıkça anılmamıştı, plan aşamasında Tauri v2 dokümantasyonundan çıkarıldı. |

## Dependencies
- `vite.config.ts` (satır 1-20): `defineConfig` içinde `test` bloğu var ama
  ayrı bir `server.port` tanımı YOK — Vite'ın varsayılanı (5173) geçerli.
  `tauri.conf.json`'ın `build.devUrl`'i bu varsayılanla eşleşmeli
  (`http://localhost:5173`), aksi halde `tauri dev` boş/yanlış sayfa açar.
- `index.html` (satır 10): `<script type="module" src="/ui/src/main.tsx">`
  — vite'ın kök `index.html`'i kullandığını doğruluyor, Tauri scaffold'un
  `frontendDist` ayarı proje kökünü (`.`) veya vite'ın build çıktısını
  (`dist/`) hedeflemeli; `dist/` klasörü zaten var (mevcut vite build
  çıktısı, muhtemelen eski/manuel bir build) — scaffold bunu EZMEMELİ,
  sadece referans almalı.
- `OnboardingScreen.test.tsx` (satır 8-33): `vi.mock('@tauri-apps/plugin-dialog')` ve
  `vi.mock('@tauri-apps/api/core')` zaten TAM olarak `open()` ve
  `invoke('plugin:fs|exists', {path})` sözleşmesini test ediyor (17
  test, satır 308-415 "invalid folder rejection" describe bloğu özellikle
  bu akışı kapsıyor, TOCTOU koruması ve reject-as-inaccessible testi
  dahil) — bu testler AC-3'ün "regresyonsuz PASS" kriterinin doğrudan
  kanıtı, yeniden yazılmasına gerek yok, sadece gerçek API sözleşmesiyle
  hizalanması gerekiyorsa güncellenir.
- `@tauri-apps/api` (^2.11.1) ve `@tauri-apps/plugin-dialog` (^2.2.0) zaten
  `package.json`'da — versiyon uyumu için `@tauri-apps/plugin-fs` da v2
  serisinden (^2.x) seçilmeli.
- Rust toolchain: bu oturumda `rustup default stable` ile zaten kuruldu
  (1.97.1) — scaffold için ek kurulum gerekmiyor.

## Migration Required?
Hayır — şema/veri değişikliği yok, sadece yeni bir native kabuk katmanı
ekleniyor.

## Risks
- (atdd.md'den taşındı) vite 8 / `@vitejs/plugin-react@4.7.0` peer-range
  uyarısı — AC-5 ile native build'de gerçek soruna yol açıp açmadığı
  doğrulanacak.
- (atdd.md'den taşındı) `tauri.conf.json`'ın `frontendDist`/`devUrl`
  ayarlarının `vite.config.ts` ile uyumu — yukarıda Dependencies'te
  netleştirildi (port 5173 varsayılan, `dist/` build çıktısı).
- **Yeni (plan aşamasında bulundu):** Tauri v2'nin capability/permission
  sistemi (yukarıdaki New Files tablosunda not edildi) atdd.md'de
  anılmamıştı — `fs:allow-exists` izni capability dosyasına eklenmezse,
  Cargo tarafında plugin kayıtlı olsa bile `invoke` reddedilir ve AC-2/AC-4
  hâlâ karşılanmaz. Bu, AC-2'nin doğal bir alt-adımı olarak ele alınacak,
  ayrı bir AC gerekmiyor ama code-copilot'un GÖZ ARDI ETMEMESİ gerekiyor.
- Kök dizindeki mevcut `dist/` klasörü (muhtemelen eski/manuel bir vite
  build çıktısı) ile Tauri scaffold'un `frontendDist` beklentisi çakışırsa
  scaffold bunu sessizce ezebilir — code-copilot bu klasörü SİLMEDEN/
  EZMEDEN önce içeriğinin gerçekten yeniden-üretilebilir (build artifact)
  olduğunu teyit etmeli.

## Not: Görsel/UI dosyası dokunuluyor
`OnboardingScreen.tsx` bir rendered web UI (.tsx) dosyası — ancak atdd.md
bu görevi salt IPC-sözleşme uyumu olarak sınırladı (görsel/CSS değişikliği
YOK, sadece `invoke` çağrısının parametreleri değişebilir). `verify`
adımında gate 11 (`vision-test`) bu nedenle muhtemelen N/A kalacak (görsel
regresyon riski yok), ama `verify` bunu körlemesine N/A işaretlemek yerine
gerekçesiyle değerlendirmeli.

## Open Questions
Yok — atdd.md'deki kullanıcı onaylarıyla (Tauri v2, manuel smoke test,
gerçek API'ye göre kod düzelt, paketleme/CI/backend-iletişim kapsam dışı)
kapsam net. Capability/permission bulgusu bir risk olarak yukarıda not
edildi, ayrı bir kullanıcı kararı gerektirmiyor (AC-2'nin doğal parçası).
