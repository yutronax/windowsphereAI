from io import BytesIO
from pathlib import Path


def redact_pdf_page(pdf_path: Path, page_number: int, regions: list) -> bytes:
    """`pdf_path` icindeki `page_number` (1-indexed) sayfasini rasterize
    edip `regions` listesindeki her dikdortgen uzerine opak siyah bir kutu
    cizer, sonucu TEK SAYFALIK bir PDF'in bayt icerigi olarak doner (Saga
    #320). Dosya yoksa `FileNotFoundError`, uzantı `.pdf` degilse veya
    `page_number` gercek sayfa sayisini asiyorsa `ValueError` firlatir.

    `pdf2image`/`PIL` lazy import edilir (pdf_ocr.py'nin AYNI stili) -
    Poppler kurulu degilse sadece bu fonksiyon cagrildiginda hata verir,
    modul import edilirken degil."""
    if not pdf_path.exists():
        raise FileNotFoundError(f"Dosya bulunamadi: {pdf_path}")

    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError(f"Gecersiz dosya uzantisi, .pdf bekleniyor: {pdf_path}")

    from pypdf import PdfReader

    reader = PdfReader(str(pdf_path))
    page_count = len(reader.pages)
    if page_number > page_count:
        raise ValueError(
            f"Sayfa numarasi ({page_number}) gercek sayfa sayisini ({page_count}) asiyor: {pdf_path}"
        )

    # PDF sayfasinin GERCEK nokta-uzayi (72 DPI) genislik/yuksekligini
    # rasterize etmeden ONCE al - regions.x0/y0/x1/y1 PDF nokta uzayinda,
    # sol-alt kokenli (RedactionRegion docstring sozlesmesi) geldigi icin,
    # bunlari piksel uzayina (sol-ust kokenli) donusturmek icin olcek
    # faktoru burada hesaplanir (bkz. Saga #320 red-team bulgusu 1).
    page = reader.pages[page_number - 1]
    page_width_pt = float(page.mediabox.width)
    page_height_pt = float(page.mediabox.height)

    # Red-team bulgusu 2: gercek sayfa sinirlarina karsi bolge dogrulamasi -
    # cizmeden ONCE, kucuk bir tolerans (float yuvarlama) ile.
    epsilon = 0.5
    for region in regions:
        if region.x1 > page_width_pt + epsilon or region.y1 > page_height_pt + epsilon:
            raise ValueError(
                f"Bolge (page={region.page}, x1={region.x1}, y1={region.y1}) sayfanin "
                f"gercek boyutlarini asiyor (page_width_pt={page_width_pt}, "
                f"page_height_pt={page_height_pt}): {pdf_path}"
            )

    from pdf2image import convert_from_path
    from PIL import ImageDraw

    images = convert_from_path(str(pdf_path), first_page=page_number, last_page=page_number)
    image = images[0]
    image_width_px, image_height_px = image.size

    scale_x = image_width_px / page_width_pt
    scale_y = image_height_px / page_height_pt

    draw = ImageDraw.Draw(image)
    for region in regions:
        # PDF nokta uzayi (sol-alt kokenli) -> piksel uzayi (sol-ust
        # kokenli): x dogrudan olceklenir, y ters cevrilir
        # (image_height_px - y * scale_y).
        px_x0 = region.x0 * scale_x
        px_x1 = region.x1 * scale_x
        px_y0 = image_height_px - (region.y1 * scale_y)
        px_y1 = image_height_px - (region.y0 * scale_y)
        draw.rectangle([px_x0, px_y0, px_x1, px_y1], fill="black")

    buffer = BytesIO()
    image.save(buffer, format="PDF")
    return buffer.getvalue()
