# SETUP.md — windows-ai-files

## Frontend
```bash
npm install
npx playwright install --with-deps chromium   # e2e testler için, bir kez
npm run dev      # geliştirme sunucusu (sadece tarayıcı, Tauri API'leri çalışmaz)
npm run build    # tsc --noEmit + vite build
npx vitest run    # unit/component testler
npx playwright test   # e2e testler
```

## Masaüstü kabuğu (Tauri v2)
Gerçek masaüstü penceresinde çalıştırmak (`invoke('plugin:fs|exists', ...)`
gibi native çağrıların GERÇEKTEN çalışması) için Visual Studio Build Tools
2022 (C++ workload) gerekir — Rust/cargo tek başına yeterli değil:
```bash
winget install --id Microsoft.VisualStudio.2022.BuildTools --silent \
  --accept-package-agreements --accept-source-agreements \
  --override "--add Microsoft.VisualStudio.Workload.VCTools --includeRecommended --quiet --wait"
```
Sonra derleme/çalıştırma komutlarını **VS Developer ortamında** çalıştır
(aksi halde `link.exe` olarak Git for Windows'un kendi `link.exe`'si —
coreutils hardlink aracı, Microsoft linker'ı DEĞİL — bulunur ve anlamsız
"extra operand" hatalarına yol açar):
```bash
# cmd/PowerShell'de VS Developer ortamını yükle, sonra:
npm run tauri:dev     # gerçek Tauri penceresi (dev)
npm run tauri:build   # .exe/installer (bu projede henüz doğrulanmadı)
```
`src-tauri/icons/` şu an düz renkli YER TUTUCU ikonlar içeriyor (gerçek
marka/logo tasarımı ayrı bir görev).

## Backend
Proje kendi `.venv`'ini henüz içermiyor — `../.venv` (Yazılım_müh kökü) üzerinden çalıştırılabilir:
```bash
"../.venv/Scripts/python.exe" -m pytest backend/tests/ -v
```
Gerekli paketler: `fastapi`. Proje kendi `requirements.txt`/`pyproject.toml`'unu henüz tanımlamıyor (ayrı bir task).

`WORD_TO_PDF` operasyonu (Saga #339) için LibreOffice gerekir, `soffice`
PATH'te bulunabilir olmalı:
```bash
winget install --id TheDocumentFoundation.LibreOffice --silent \
  --accept-package-agreements --accept-source-agreements
```
LibreOffice'in `program\` klasörünü (varsayılan
`C:\Program Files\LibreOffice\program`) PATH'e ekle — `backend/word_to_pdf.py`
sabit bir yola hardcode ETMEZ, sadece `shutil.which("soffice")` ile arar.
İlk `soffice` çalıştırması profil oluşturma nedeniyle ~30sn sürebilir;
sonraki çağrılar hızlıdır.

## Ortam Değişkenleri
- `APPDATA` (Windows, otomatik) — ilk-kurulum config dosyası (`%APPDATA%/windows-ai-files/config.json`) için zorunlu, `backend/config.py` bunsuz `RuntimeError` fırlatır.
- Backend sabit olarak `127.0.0.1:8000`'de çalışacak şekilde varsayılıyor (bkz. `docs/DESIGN_DECISIONS.md` D3); henüz yapılandırılabilir değil.

## Bilinen Sınırlamalar
- `.exe`/installer paketleme (`tauri build`) bu projede henüz DOĞRULANMADI —
  sadece `tauri dev` (geliştirme penceresi) doğrulandı, ayrı bir görev.
- CI/CD pipeline'ına Tauri build adımı eklenmedi.
- Backend hâlâ ayrı bir FastAPI process olarak `BACKEND_ORIGIN` sabit
  URL'i üzerinden çağrılıyor (sidecar değil) — bu değişmedi.
- `npm audit`, vite/vitest zincirinde bir dev-server-only güvenlik açığı raporluyor (Saga task #278) — bilinçli olarak ertelendi.
