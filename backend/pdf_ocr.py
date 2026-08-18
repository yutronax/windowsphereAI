from pathlib import Path


def _pdf_to_images(pdf_path: Path) -> list:
    """PDF'in sayfalarını görüntülere çevirir (Saga #306). pdf2image lazy
    import edilir; Poppler kurulu değilse sadece bu fonksiyon çağrıldığında
    hata verir, modül import edilirken değil."""
    from pdf2image import convert_from_path

    return convert_from_path(str(pdf_path))


def _run_ocr_engine(image) -> str:
    """Tek bir sayfa görüntüsü üzerinde OCR çalıştırır (Saga #306).
    pytesseract lazy import edilir, Tesseract kurulu değilse sadece
    çağrıldığında hata verir."""
    import pytesseract

    return pytesseract.image_to_string(image, lang="tur+eng")


def ocr_pdf_file(pdf_path: Path) -> list[str]:
    """`pdf_path` PDF dosyasını OCR'dan geçirip her sayfanın metnini
    sırasıyla döner (Saga #306). Dosya yoksa `FileNotFoundError`, uzantı
    `.pdf` değilse `ValueError` fırlatır."""
    if not pdf_path.exists():
        raise FileNotFoundError(f"Dosya bulunamadi: {pdf_path}")

    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError(f"Gecersiz dosya uzantisi, .pdf bekleniyor: {pdf_path}")

    images = _pdf_to_images(pdf_path)

    return [_run_ocr_engine(image).strip() for image in images]
