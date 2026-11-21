# Windows AI Files

Windows için doğal dil istekleriyle dosya işlemlerini planlamayı ve yönetmeyi amaçlayan, geliştirme aşamasında bir masaüstü uygulaması. React arayüzü Tauri ile masaüstünde çalışır; Python/FastAPI arka ucu yerel HTTP üzerinden ayrı bir süreç olarak çalıştırılır.

## İşlevler

- Klasör seçimi, dosya arama ve işlem planı oluşturma.
- Dosya taşıma, kopyalama, yeniden adlandırma ve silme; işlem geçmişi ve desteklenen işlemler için geri alma.
- PDF, Excel, Word, görsel ve ZIP işlemleri için backend modülleri.
- Seçilen klasör sınırları içinde yol doğrulaması ve işlem önizlemesi.

## Mimari

React + TypeScript arayüzü → Tauri masaüstü kabuğu → `127.0.0.1:8000` üzerindeki FastAPI servisi → dosya sistemi ve SQLite işlem geçmişi. Plan üretimi için OpenAI uyumlu bir API yapılandırılabilir.

## Geliştirme ortamı

Windows, Python 3.11+, Node.js, Rust ve Tauri için Visual Studio C++ Build Tools gerekir. Bazı belge özellikleri ek sistem bağımlılıkları gerektirir; [SETUP.md](SETUP.md) dosyasına bakın.

PowerShell'de depo kökünden:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt -r requirements-dev.txt
npm ci
```

İlk terminalde backend'i başlatın:

```powershell
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

İkinci terminalde masaüstü geliştirme uygulamasını başlatın:

```powershell
npm run tauri:dev
```

Plan üretimi için backend sürecinde `PLAN_LLM_API_KEY`, isteğe bağlı olarak `PLAN_LLM_BASE_URL` ayarlanmalıdır. Anahtarı depoya eklemeyin. Tarayıcıda `npm run dev` arayüzü açar, ancak Tauri'ye özgü yerel API'leri çalıştırmaz.

## Testler

```powershell
python -m pytest backend/tests -v
npx vitest run
npm run build
```

Uçtan uca testler için Playwright ve Chromium kurulumu gerekir: `npx playwright install chromium`, ardından `npm run test:e2e`.

## Durum ve sınırlamalar

Proje geliştirme aşamasındadır. Backend otomatik başlatılan bir sidecar değildir; ayrı çalıştırılmalıdır. Kurulum paketi üretimi henüz doğrulanmamıştır. Tasarım belgesi hedeflenen mimariyi de içerir ve mevcut davranışın tamamını temsil etmeyebilir. Komutlar bu README hazırlanırken temiz bir Windows ortamında doğrulanmamıştır.
