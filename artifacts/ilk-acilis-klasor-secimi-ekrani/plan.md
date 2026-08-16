# Plan — ilk-acilis-klasor-secimi-ekrani
_Reference: atdd.md_

## Bağlam
Proje sıfırdan yazılıyor — `windows-ai-files/` şu an yalnızca `docs/` ve
`artifacts/` içeriyor, kod yok. Bu yüzden bu plan hem bu task'ın kendi
dosyalarını hem de onun çalışması için gereken **minimum** proje iskeletini
kapsıyor (eldeki eski proje `referans/windows-ai-files-eski/` sadece
konvansiyon referansı için incelendi, kod kopyalanmadı — eski `config.py`
whitelist'i statik/proje-köküne göredir, yeni tasarımdaki "kullanıcı seçtiği
klasör" davranışıyla örtüşmüyor, bu yüzden yeniden yazılıyor).

## Files to Modify
(Yok — proje boş, değiştirilecek mevcut dosya yok.)

## New Files

| File | Purpose | Risk |
|------|---------|------|
| `src-tauri/Cargo.toml` | Tauri v2 Rust proje tanımı | low |
| `src-tauri/tauri.conf.json` | Tauri pencere/sidecar yapılandırması (backend'i sidecar olarak tanımlar) | medium — Tauri v2 sidecar API'si bu projede ilk kez kullanılıyor (bkz. atdd.md Risks) |
| `src-tauri/src/main.rs` | Tauri giriş noktası — pencereyi açar, FastAPI backend'i sidecar süreç olarak başlatır | medium |
| `backend/main.py` | FastAPI uygulaması — `/api/health` endpoint'i (sidecar hazır olduğunu bildirmek için) | low |
| `backend/config.py` | İlk-kurulum tespiti: kullanıcı config dosyasının (`%APPDATA%/windows-ai-files/config.json`) var/yok olmasına bakar | low |
| `backend/schemas.py` | `SetupConfig` (seçilen klasör yolu) için Pydantic modeli | low |
| `ui/src/main.tsx` | React giriş noktası | low |
| `ui/src/App.tsx` | Backend health-check'i bekleyen, sonra `OnboardingScreen`/ana sohbete yönlendiren kök bileşen | medium |
| `ui/src/components/onboarding/OnboardingScreen.tsx` | AC-1, AC-2, AC-3'ü karşılayan klasör seçimi ekranı (native Tauri dialog API çağrısı, seçilen yolu gösterme, "Devam" butonu state'i) | medium |
| `ui/src/components/onboarding/OnboardingScreen.test.tsx` | Unit testler (%20 payı) — path kısaltma yardımcı fonksiyonu, buton disabled/enabled state mantığı | low |
| `ui/src/lib/backendHealth.ts` | Health-check polling yardımcı fonksiyonu (AC-4, timeout davranışı) | medium — timeout süresi henüz kullanıcıyla teyit edilmedi (bkz. Open Questions) |
| `ui/src/lib/backendHealth.test.ts` | Unit testler — polling/timeout mantığı | low |
| `ui/e2e/onboarding.spec.ts` | E2E testler (%50 payı) — AC-1..AC-5 uçtan uca (Playwright + Tauri driver ya da mock backend ile) | medium |
| `backend/tests/test_config.py` | Integration testler (%30 payı) — ilk-kurulum tespiti, config dosyası okuma/yazma | low |

## Dependencies
- Tauri v2 `@tauri-apps/plugin-dialog` — native klasör seçme dialogu için
  (DESIGN_DECISIONS.md D2 kararına bağlı).
- Tauri v2 sidecar API (`tauri-plugin-shell` veya eşdeğeri) — FastAPI
  backend'i alt süreç olarak başlatmak için (D3 kararına bağlı).
- `backend/config.py`, ilerleyen task'larda (#256, #258) SessionContext ve
  ALLOWED_PATHS kurulumunun temelini oluşturacağı için buradaki dosya
  formatı (JSON şeması) sonraki task'ları etkiler — burada kurulan şema
  değişirse onlar da güncellenmeli.

## Migration Required?
Hayır — bu task SQLite/SQLAlogy şemasına dokunmuyor. İlk-kurulum tespiti
basit bir JSON config dosyasıyla yapılıyor (DESIGN_DECISIONS.md D4'teki
SQLite kararı genel uygulama verisi içindir — undo/analiz geçmişi gibi.
Sadece "hangi klasöre izin var" bilgisi bu aşamada SQLite'a taşınmıyor,
Saga task #258'de SessionContext kurulurken yeniden değerlendirilecek).

## Risks
- (atdd.md'den) Tauri dialog API'sinin Windows'ta native davranışı henüz
  doğrulanmadı — bu, projenin ilk somut Tauri entegrasyonu.
- Sidecar başlatma mantığı (`main.rs`) ile FastAPI'nin `127.0.0.1:8000`'de
  gerçekten ayağa kalkması arasındaki zamanlama, health-check polling
  mantığının (AC-4) doğru çalışmasına bağlı — bu iki taraf ayrı dillerde
  (Rust/Python) yazıldığı için entegrasyon riski var.

## Open Questions
1. **Backend health-check timeout süresi** — atdd.md'de "10sn varsayım,
   teyit edilmedi" olarak işaretlenmişti. Koda yazmadan önce netleşmeli.
2. **Config dosyası tam konumu** — `%APPDATA%/windows-ai-files/config.json`
   öneriliyor (Windows standart konvansiyonu), ama atdd.md'de "Unknowns"
   olarak bırakılmıştı, onay gerekiyor.
