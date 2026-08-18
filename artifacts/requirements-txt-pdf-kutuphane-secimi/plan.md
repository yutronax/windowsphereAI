# Plan — requirements.txt + PDF Kütüphane Seçimi (Saga #303)

## Değişecek dosyalar
- `requirements.txt` (YENİ) — proje kökünde, backend'in gerçek
  bağımlılıklarını pinlenmiş sürümlerle listeler.

## Yeni bağımlılık
- `pypdf==6.13.3` (ortamda zaten kurulu, sadece dosyaya ekleniyor).

## Adımlar
1. `pip freeze` çıktısından gerçek kurulu sürümleri oku (fastapi,
   uvicorn, sqlalchemy, openai, pydantic, pytest, pytest-mock, pypdf).
2. `requirements.txt` yaz.
3. Temiz bir geçici venv'de `pip install -r requirements.txt` ile
   gerçekten kurulabildiğini doğrula (smoke test).
4. `AI_DEVLOG.md`'ye pypdf/PyMuPDF kararının gerekçesini (AGPL lisans
   riski) kaydet.

## Riskler
Yok — saf bir dosya-oluşturma task'ı, davranış değişikliği içermiyor.
