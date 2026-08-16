# Code Diff — ilk-acilis-klasor-secimi-ekrani
_Codex (gpt-5.6-terra) tarafından yazıldı (GREEN adımı)._

## Oluşturulan Dosyalar

| Dosya | Amaç |
|---|---|
| `ui/src/components/onboarding/OnboardingScreen.tsx` | AC-1..AC-4: klasör seçimi ekranı + `truncateWindowsPath` yardımcı fonksiyonu |
| `ui/src/lib/backendHealth.ts` | AC-4: `waitForBackendHealth` polling/timeout mantığı |
| `ui/src/App.tsx` | AC-5: `/api/config`'e göre onboarding↔ana ekran yönlendirmesi |
| `ui/src/main.tsx` | React giriş noktası |
| `backend/config.py` | AC-5: `%APPDATA%/windows-ai-files/config.json` ilk-kurulum tespiti |
| `backend/main.py` | FastAPI `/api/health`, `/api/config` endpoint'leri |

## Acceptance Criteria Kapsamı
- **AC-1** ✅ — `OnboardingScreen` her zaman render edilir, `backendStatus==='ready'` iken "Klasör Seç" etkin.
- **AC-2** ✅ — `chooseFolder()` native dialog'dan string dönerse state'e alır, `selected-folder-path` testid'i ile gösterir, Devam etkinleşir.
- **AC-3** ✅ — dialog `null` dönerse (`typeof folder === 'string'` kontrolü) state değişmez, Devam disabled kalır.
- **AC-4** ✅ — `backendStatus==='starting'` iken tüm etkileşim disabled + "Başlatılıyor…"; `backend_timeout`'ta hata metni + Tekrar Dene → `onRetry` (App.tsx'te `checkBackend`'i tekrar tetikliyor).
- **AC-5** ✅ — `App.tsx` mount'ta `/api/config`'i çeker; 200 → `main-chat-screen` testid'li placeholder, 404/hata → `OnboardingScreen`.

## CAVEMAN İncelemesi (Codex özetinden + Read doğrulaması)
- 6 dosya eklendi, hepsi AC'lerle doğrudan bağlantılı, gerekçesiz dosya yok.
- Yeni soyutlama/yardımcı fonksiyon yok (`truncateWindowsPath` hariç — test
  dosyası tarafından doğrudan import ediliyor, zorunlu).
- TODO/FIXME/placeholder yok.
- `onContinue={() => {}}` App.tsx'te bilinçli no-op — Devam'ın backend'e
  gönderilmesi ayrı bir Saga task'ının (#258) kapsamı, burada icat edilmedi.

## Bilinen Sınırlamalar
- **Test/tooling scaffold henüz yok**: `package.json`, `vite.config`,
  `vitest` kurulumu, `backend`'in pytest tarafından import edilebilir bir
  paket olması (namespace package ya da `conftest.py`/`pytest.ini` ile
  proje kökünün `sys.path`'e eklenmesi) — bu çağrının kasıtlı kapsamı
  dışında bırakıldı (bkz. plan.md, Tauri/Rust iskeleti de aynı şekilde
  ayrı bırakıldı). `verify` adımı bu eksikliği netleştirecek.
- `App.tsx`'teki "ana sohbet ekranı" yalnızca `data-testid="main-chat-screen"`
  içeren bir placeholder — gerçek sohbet arayüzü ayrı Saga epic'i (#24).

## Sıradaki Adım
`verify` — gerçek test çalıştırması ve kalite kapıları (bu adımda tooling
eksikliği netleşirse, ayrı bir küçük "proje iskeleti" task'ı gerekebilir).
