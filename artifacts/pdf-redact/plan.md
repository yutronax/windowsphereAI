# PDF Redact — Değişiklik Planı (Saga #320)

## 1. `backend/models.py`

- `OperationType` enum'una `REDACT = "Karart"` eklenir (MERGE/SPLIT/OCR ile
  aynı Türkçe deger deseni).
- Yeni `RedactionRegion(BaseModel)`:
  - `page: int` (1-tabanli, >=1)
  - `x0: float`, `y0: float`, `x1: float`, `y1: float` (piksel koordinati,
    rasterize edilmis goruntu uzerinde; sol-ust orijin)
  - `field_validator`: `page >= 1`, tum koordinatlar `>= 0`
  - `model_validator`: `x1 > x0` ve `y1 > y0` (sifir/negatif alan yasak)
- `PlanStep`'e iki yeni alan:
  - `redactionRegions: list[RedactionRegion] | None = None`
  - `redactedFileName: str | None = None`
  - Ikisi de SADECE `operationType == REDACT` oldugunda dolu olmali, diger
    turlerde `None` kalmali (MERGE'in `mergedFileName` deseniyle AYNI).
- Yeni `model_validator(mode="after")` `redact_fields_only_for_redact`:
  - REDACT ise: `redactedFileName` bos/whitespace olamaz, path ayraci
    icermez, kaynak `fileNames`'le (normcase) cakismaz; `redactionRegions`
    None veya bos olamaz (en az 1 bolge); `fileNames` TAM 1 eleman
    (SPLIT/OCR ile ayni desen, ayri bir validator yerine BURADA
    birlestirilecek VEYA ayri `file_names_length_exactly_one_for_redact`
    validator'u SPLIT/OCR'la ayni desende eklenecek).
- Diger operationType'larda `redactionRegions`/`redactedFileName` verilirse
  reddedilir (MERGE/RENAME desenindeki "else: raise" ile ayni).

## 2. `backend/pdf_redact.py` (yeni modul, `pdf_ocr.py` ile AYNI stil)

- Path validasyonu YOK (orchestrator.py'de merkezi kalir).
- `_pdf_page_to_image(pdf_path: Path, page_number: int)`  — pdf2image ile
  SADECE tek sayfayi rasterize eder (`first_page`/`last_page` parametreleri
  pdf2image'da mevcut — tum PDF'i cevirmek gereksiz).
- `_draw_redaction_boxes(image, regions: list[RedactionRegion])` — PIL
  `ImageDraw` ile her bolge icin opak siyah dikdortgen cizer, DEGISTIRILMIS
  goruntuyu doner (lazy `from PIL import Image, ImageDraw`).
- `_image_to_pdf_page_bytes(image) -> bytes` — goruntuyu tek sayfalik bir
  PDF'e cevirir (PIL `Image.save(..., format="PDF")` ile, ek bagimlilik
  gerektirmez).
- `redact_pdf_page(pdf_path: Path, page_number: int, regions: list[RedactionRegion]) -> bytes`
  — yukaridaki adimlari birlestirir, karartilmis TEK sayfanin PDF byte'ini
  doner. Dosya yoksa `FileNotFoundError`, `.pdf` degilse `ValueError`,
  `page_number` gercek sayfa sayisini asarsa `ValueError` (orchestrator
  bunu `PlanApplicationError`e cevirir).
- Modul ocr_pdf_file ile AYNI docstring/yorum stili (Saga #320 referansi).

## 3. `backend/orchestrator.py`

- Import: `from backend.pdf_redact import redact_pdf_page`
- `OperationType.REDACT`, `_SUPPORTED_OPERATION_TYPES`'a eklenir.
- Yeni `_forward_redact(source_path, page_number, regions, destination_path)`:
  MERGE/SPLIT'in gecici-dosya + atomik `Path.replace` desenini izler —
  `pypdf.PdfReader(source_path)` ile TUM sayfalari okur, hedef
  `page_number - 1` indeksini `redact_pdf_page`'den gelen tek-sayfalik PDF
  ile DEGISTIRIR (o sayfayi `PdfWriter`e eklerken orijinal yerine yeni
  sayfa page'ini kullanir), digerlerini OLDUGU GIBI kopyalar, TEK bir
  `PdfWriter.write` ile gecici dosyaya yazar, sonra atomik `replace`.
  `page_number` gercek sayfa sayisini asarsa `PlanApplicationError`.
- `apply_plan` icinde MERGE/SPLIT'e benzer ozel dal: `step.operationType == OperationType.REDACT`
  - `is_path_allowed` + `validate_plan_paths` (zaten dosya seviyesinde tum
    `pdf_files` icin calisiyor) kaynak dosyayi kapsar; `redactedFileName`
    icin `_validate_single_path` cagrisi `validate_plan_paths`'e eklenir
    (MERGE'in `mergedFileName` kontrolu ile AYNI yerde, `security.py`
    icinde).
  - Yeni `validate_redact_destinations` (security.py, `validate_merge_destinations`
    ile AYNI desen) — plan genelinde REDACT/MERGE/RENAME hedefleri
    birbiriyle cakismaz.
  - Tek `FileOperation` kaydi (`source_path`=kaynak, `destination_path`=
    `redactedFileName`, `backup_path`=`destination_path` — MERGE'in "COPY
    semantigiyle rollback: sadece hedefi sil" deseniyle AYNI).
  - Sonuc: `applied.append(operation)`, `continue`.
  - Rollback: `_ROLLBACK_OPERATIONS[OperationType.REDACT] = _rollback_copy`
    (MERGE/SPLIT ile AYNI — kaynak hic degismedi).
- `apply_plan`'in target_dir olusturma blogundaki hariç-tutma listesine
  `OperationType.REDACT` eklenir (MERGE/SPLIT gibi allowed_root KOKUNE
  yazar, dated alt klasor yok).
- Sonuc/uyari: `apply_plan`'in donus degeri `Transaction` oldugu icin
  kullaniciya gosterilecek `warning` metni `backend/main.py`'deki plan
  uygulama endpoint yanitina (ApplyPlanResponse benzeri) eklenecek — bu
  REDACT adimi VARSA sabit bir uyari string'i eklenir. (Kapsam: sadece
  REDACT step'i icin `TransactionApplyResponse`e opsiyonel `warnings: list[str]`
  alani eklenir, main.py'de step'ler taranip REDACT varsa uyari eklenir.)

## 4. `backend/security.py`

- `validate_plan_paths` icine REDACT icin `_validate_single_path(allowed_root / step.redactedFileName, ...)`
  eklenir (MERGE'deki `mergedFileName` satiriyla AYNI blok).
- Yeni `validate_redact_destinations` fonksiyonu, `validate_merge_destinations`
  ile AYNI mantik (bilinen dosya muafiyeti + plan-geneli cakisma kontrolu,
  artik REDACT hedeflerini de `all_destinations` listesine katar).

## 5. Testler

- `backend/tests/test_pdf_redact.py` (yeni) — `redact_pdf_page` modul
  seviyesinde: gercek pypdf ile uretilmis PDF + reportlab/pypdf ile
  eklenmis GERCEK metin (ornegin `pypdf` `PageObject.add_transformation`
  degil, dogrudan bir metin katmanı olan test PDF'i - eger reportlab
  mevcutsa kullanilir, degilse pypdf'in `PdfWriter.add_blank_page` +
  harici bir kucuk PDF sabit-metin fixture'i) uzerinde: (a) donen PDF
  byte'inin `extract_text()`'inde orijinal metin YOK, (b) sayfa disi
  page_number -> ValueError, (c) olmayan dosya -> FileNotFoundError.
- `backend/tests/test_orchestrator.py`'ye REDACT bolumu eklenir (MERGE/
  SPLIT bolumleriyle AYNI stil, `_redact_step` helper): basarili redaksiyon
  + boyut buyumesi + digerlerinin sayfalarinin extract_text ile hala
  okunabilir olmasi + kaynak dokunulmamis + allowed_root disi red + rollback
  (sonraki step patlarsa cikti dosyasi silinmis olmali) + `redactedFileName`
  cakismasi.

## 6. AI_DEVLOG.md

- KVKK/guvenlik notu ile REDACT ozelligi eklenir (rasterize+opak kutu,
  metin katmaninin fiziksel olarak yok edildigi vurgulanir).
