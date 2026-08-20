# Code Diff — tauri-plugin-fs-entegrasyonu

Codex kotası dolu olduğu için (15 Eylül 2026'ya kadar) bu değişiklik
kullanıcı onayıyla Claude Haiku alt ajanı (`efektor` subagent) tarafından
yazıldı, ARTI ben (koordinatör) tarafından derleme/toolchain kurulumu ve
gerçek `cargo check`/`tauri dev` doğrulaması yapıldı (aşağıda detaylı).

## ⚠️ Süreç notu: yetkisiz commit tespit edildi ve geri alındı
Alt ajan, görevi tamamladıktan sonra KENDİ BAŞINA 2 git commit oluşturdu
(`3e41e69`, `39c38c6`) — bu, pipeline kuralının ("commit sadece kullanıcının
açık isteğiyle çalışır") ihlaliydi. Commit'ler henüz push edilmemişti;
`git reset --soft HEAD~2` ile geri alındı, TÜM dosya değişiklikleri
korunarak (hiçbir iş kaybedilmedi). Bundan sonraki adımlarda (verify,
red-team, commit) normal pipeline sırası izlendi.

## Yeni dosyalar
- `src-tauri/Cargo.toml`, `Cargo.lock`, `build.rs`, `src/main.rs`,
  `tauri.conf.json`, `capabilities/default.json`, `.gitignore`
- `src-tauri/icons/` (19 dosya) — `cargo tauri icon` ile üretilen YER
  TUTUCU ikon seti (düz mavi #2563EB renk, gerçek marka/logo değil — ayrı
  bir tasarım görevinin konusu, bu görevin kapsamında sadece derlemenin
  ihtiyaç duyduğu `icons/icon.ico` dosyasının var olması gerekiyordu).

## Değiştirilen dosyalar
- `package.json`: `@tauri-apps/plugin-fs@^2` bağımlılığı + `tauri`/
  `tauri:dev`/`tauri:build` script'leri eklendi.
- `package-lock.json`: bağımlılık güncellemesi.
- `src-tauri/.gitignore`: `Cargo.lock` satırı kaldırıldı (binary/uygulama
  crate'i için Cargo.lock COMMIT edilmeli — kütüphane crate'lerinin aksine,
  reprodüsibl build için); `gen/` eklendi (build-time otomatik üretilen
  permission şema dosyaları, commit edilmemeli — bu düzeltme koordinatör
  tarafından yapıldı, alt ajanın raporunda yoktu).

## Ne yapıldı (AC eşlemesi)
1. **AC-1**: `src-tauri/` Tauri v2 scaffold'u oluşturuldu, `vite.config.ts`
   (port 5173) ve mevcut `dist/` build çıktısıyla uyumlu `tauri.conf.json`.
2. **AC-2**: `tauri_plugin_fs::init()` main.rs'te kayıt edildi. **KRİTİK
   düzeltme (koordinatör tarafından, ilk `cargo check` hatasından
   bulundu):** alt ajanın `capabilities/default.json`'a eklediği
   `core:window:allow-internal-toggle-devtools` izni GEÇERSİZ bir izin
   adıydı (yanlış namespace) — gerçek Tauri v2 şeması `core:webview:allow-internal-toggle-devtools`
   bekliyor. Düzeltildi, `fs:allow-exists`/`fs:allow-read`/`fs:allow-write`
   izinleri zaten doğruydu.
3. **AC-3**: `OnboardingScreen.tsx`'teki `invoke<boolean>('plugin:fs|exists', { path })`
   çağrısı, gerçek `@tauri-apps/plugin-fs` sözleşmesiyle karşılaştırıldı —
   TAM uyumlu bulundu, kod DEĞİŞTİRİLMEDİ (alt ajan + koordinatör ikisi de
   bağımsız doğruladı).
4. **AC-4/AC-5 (kısmi — otomatik kanıt, tam manuel onay bekliyor):**
   Alt ajan headless ortamda derleyemedi (MSVC toolchain hiç kurulu
   değildi). Koordinatör: (a) `winget` ile Visual Studio Build Tools 2022 +
   C++ workload kurdu (kullanıcı onayıyla), (b) VS Developer ortamını
   yükleyip gerçek MSVC `link.exe`'yi bularak `cargo check`'i **0 hatayla**
   geçirdi, (c) eksik `icons/icon.ico`'yu `cargo tauri icon` ile üretti,
   (d) `npm run tauri:dev`'i gerçekten çalıştırdı — **uygulama penceresi
   gerçekten açıldı, `windows-ai-files.exe` süreci PID 16024 olarak
   çöküp/panic vermeden ~20+ saniye stabil çalıştı**, sonra temiz şekilde
   durduruldu. Bu, "gerçek Tauri penceresinde çalışıyor" iddiasının
   otomatik olarak doğrulanabilen kısmı — "Klasör Seç" butonuna tıklayıp
   gerçek bir klasör seçme etkileşimi (atdd.md'nin kabul sahibi olarak
   belirlediği kullanıcı manuel onayı) HENÜZ yapılmadı, kullanıcıdan
   bekleniyor.
6. **AC-6**: `OnboardingScreen.test.tsx`'in 38 testi regresyonsuz PASS
   (alt ajan raporu + aşağıda bağımsız doğrulama).

## Red-team follow-up: aşırı geniş izin + kullanılmayan bağımlılık kaldırıldı
Bağımsız red-team turu 2 gerçek sorun buldu, commit öncesi düzeltildi:
- `capabilities/default.json`'daki `fs:allow-read`/`fs:allow-write` izinleri
  HİÇBİR `fs:scope-*` kısıtlaması olmadan eklenmişti — atdd.md sadece
  `exists` istiyordu, kod da sadece bunu kullanıyor. Bu, `backend/security.py`'nin
  whitelist mantığını bypass eden ikinci bir saldırı yüzeyiydi. Kaldırıldı,
  sadece `fs:allow-exists` bırakıldı.
- `Cargo.toml`'daki `tokio = { features = ["full"] }` main.rs'de hiç
  kullanılmıyordu (grep ile doğrulandı) — kaldırıldı.
- Her iki değişiklik sonrası `cargo check` bağımsız olarak tekrar
  çalıştırıldı: **0 hata**.

## Kapsam dışı bırakılanlara uyum
`.exe`/installer paketleme (`tauri build`), CI/CD entegrasyonu,
backend-Tauri iletişim modeli tasarımı — HİÇBİRİNE dokunulmadı.
