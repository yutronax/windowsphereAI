# SETUP.md — windows-ai-files

## Frontend
```bash
npm install
npx playwright install --with-deps chromium   # e2e testler için, bir kez
npm run dev      # geliştirme sunucusu
npm run build    # tsc --noEmit + vite build
npx vitest run    # unit/component testler
npx playwright test   # e2e testler
```

## Backend
Proje kendi `.venv`'ini henüz içermiyor — `../.venv` (Yazılım_müh kökü) üzerinden çalıştırılabilir:
```bash
"../.venv/Scripts/python.exe" -m pytest backend/tests/ -v
```
Gerekli paketler: `fastapi`. Proje kendi `requirements.txt`/`pyproject.toml`'unu henüz tanımlamıyor (ayrı bir task).

## Ortam Değişkenleri
- `APPDATA` (Windows, otomatik) — ilk-kurulum config dosyası (`%APPDATA%/windows-ai-files/config.json`) için zorunlu, `backend/config.py` bunsuz `RuntimeError` fırlatır.
- Backend sabit olarak `127.0.0.1:8000`'de çalışacak şekilde varsayılıyor (bkz. `docs/DESIGN_DECISIONS.md` D3); henüz yapılandırılabilir değil.

## Bilinen Sınırlamalar
- Tauri/Rust iskeleti (`src-tauri/`) henüz yok — frontend şu an sadece `vite dev`/Playwright ile test ediliyor, gerçek Tauri sidecar entegrasyonu ayrı bir task.
- `npm audit`, vite/vitest zincirinde bir dev-server-only güvenlik açığı raporluyor (Saga task #278) — bilinçli olarak ertelendi.
