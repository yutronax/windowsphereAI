# PDF OCR — Dosya Değişiklik Planı

## Yeni Dosyalar
1. `backend/pdf_ocr.py`
   - `_pdf_to_images(pdf_path: Path) -> list[Image]` — `pdf2image.convert_from_path` sarmalayıcısı, izole (testte mock'lanır).
   - `_run_ocr_engine(image) -> str` — `pytesseract.image_to_string(image, lang="tur+eng")` sarmalayıcısı, izole (testte mock'lanır).
   - `ocr_pdf_file(pdf_path: Path) -> list[str]` — public API: uzantı/varlık kontrolü yapar, `_pdf_to_images` ile görüntüleri alır, her biri için `_run_ocr_engine` çağırır, `str.strip()` uygulayıp sırayla listeye ekler. `backend/pdf_discovery.py`'nin docstring/stil paternini takip eder (Saga numarası referansı, Türkçe yorum).

2. `backend/tests/test_pdf_ocr.py`
   - `pdf_discovery.py`'nin test dosyasıyla aynı stil (pytest, `unittest.mock.patch`, `tmp_path` fixture).
   - Senaryolar: başarılı çok sayfalı OCR (mock'lu), dosya yok → `FileNotFoundError`, yanlış uzantı → `ValueError`, boş sayfa listesi → `[]`, `_pdf_to_images` istisnası yukarı taşınır, OCR sonucu strip edilir.

## Değişecek Dosyalar
- `requirements.txt` — ekle: `pytesseract==0.3.13`, `pdf2image==1.17.0`, `Pillow==11.0.0` (mevcut sabitlenmiş versiyon stiliyle tutarlı `==` pinleme).

## Kapsam DIŞI (bilinçli, ATDD'de belgelendi)
- `backend/models.py` / `backend/orchestrator.py` / `backend/plan_generation.py` içine yeni `OperationType.OCR` eklenmesi — bu görev sadece çekirdek OCR fonksiyonunu sağlıyor, orchestrator entegrasyonu ayrı bir takip task'ı.
- Gerçek Tesseract/Poppler binary kurulumu — sistem bağımlılığı, packaging/devops kapsamında.

## Bağımlılık Riski
`pdf2image` paketi import edilebilir olması için sistemde Poppler gerekmez (sadece çalışma zamanında `convert_from_path` çağrıldığında gerekir) — bu yüzden `_pdf_to_images` mock'landığı sürece testler Poppler kurulu olmadan da çalışır. Aynısı `pytesseract` + Tesseract için geçerli.
