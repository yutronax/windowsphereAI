"""Saga #320: REDACT operasyonu icin kirmizi (red) adim testleri.

`backend.pdf_redact` modulu ve `redact_pdf_page` fonksiyonu HENUZ YOK - bu
testler simdilik ImportError/ModuleNotFoundError ile KIRMIZI kalmali. Amac,
`pdf_ocr.py`'nin modul-seviyesi stiliyle AYNI dogrudanligi korurken,
REDACT'in "metin gercekten kaybolmus mu" garantisini gercek, cikarilabilir
metin iceren PDF'lerle (sahte `b"%PDF-1.4 fake"` bayti degil) kanitlamak.

`reportlab` bu venv'de KURULU DEGIL (kontrol edildi) - bu yuzden gercek
metin iceren PDF'ler, standart PDF nesne modeli (Catalog/Pages/Page/
content-stream) dogrudan bayt olarak el ile insa edilerek uretiliyor
(`_build_pdf_bytes`). `pypdf.PdfReader(...).extract_text()` bu el yapimi
PDF'lerden metni basariyla cikarabiliyor (deneysel dogrulandi)."""

import io
from pathlib import Path

import pytest
from pypdf import PdfReader

from backend.models import OperationType, PlanStep, RedactionRegion


def _build_pdf_bytes(page_texts: list[str]) -> bytes:
    """`reportlab` olmadan, gercek cikarilabilir metin iceren minimal bir
    PDF'i el ile (dogrudan PDF nesne sozdizimiyle) insa eder. Her sayfa
    icin AYRI bir content stream ve AYNI Helvetica fontu paylasilir."""
    n = len(page_texts)
    font_obj = 3
    first_page_obj = 4
    first_content_obj = 4 + n

    objects: dict[int, bytes] = {}
    objects[1] = b"<< /Type /Catalog /Pages 2 0 R >>"
    kids = " ".join(f"{first_page_obj + i} 0 R" for i in range(n))
    objects[2] = f"<< /Type /Pages /Kids [{kids}] /Count {n} >>".encode()
    objects[3] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"

    for i in range(n):
        page_num = first_page_obj + i
        content_num = first_content_obj + i
        objects[page_num] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 300] "
            f"/Resources << /Font << /F1 {font_obj} 0 R >> >> "
            f"/Contents {content_num} 0 R >>"
        ).encode()

    for i, text in enumerate(page_texts):
        content_num = first_content_obj + i
        escaped = text.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")
        stream = f"BT /F1 24 Tf 20 150 Td ({escaped}) Tj ET".encode()
        objects[content_num] = (
            f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream"
        )

    out = bytearray()
    out += b"%PDF-1.4\n"
    offsets: dict[int, int] = {}
    for obj_num in sorted(objects):
        offsets[obj_num] = len(out)
        out += f"{obj_num} 0 obj\n".encode()
        out += objects[obj_num]
        out += b"\nendobj\n"

    xref_offset = len(out)
    max_obj = max(objects)
    out += f"xref\n0 {max_obj + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for obj_num in range(1, max_obj + 1):
        out += f"{offsets.get(obj_num, 0):010d} 00000 n \n".encode()
    out += b"trailer\n"
    out += f"<< /Size {max_obj + 1} /Root 1 0 R >>\n".encode()
    out += b"startxref\n"
    out += f"{xref_offset}\n".encode()
    out += b"%%EOF"
    return bytes(out)


def _write_pdf_with_text(path: Path, page_texts: list[str]) -> None:
    path.write_bytes(_build_pdf_bytes(page_texts))


SENSITIVE_TEXT = "12345678901"


def test_redact_pdf_page_removes_the_sensitive_text_from_the_target_page(tmp_path):
    from backend.pdf_redact import redact_pdf_page

    pdf_path = tmp_path / "kimlik.pdf"
    _write_pdf_with_text(
        pdf_path,
        [
            f"TC Kimlik No: {SENSITIVE_TEXT} gizli belge",
            "ikinci sayfa - alakasiz metin",
        ],
    )

    # Sayfa 1 (200x300'luk MediaBox'in cogunu kaplayan buyuk bir bolge) -
    # metnin GERCEKTE nerede oldugunu bilmeden dahi tum sayfayi karartmak
    # yeterli, cunku amac "cikarilabilir metin tamamen yok olmus mu?".
    region = RedactionRegion(page=1, x0=0, y0=0, x1=300, y1=300)

    result_bytes = redact_pdf_page(pdf_path, 1, [region])

    assert isinstance(result_bytes, bytes)
    reader = PdfReader(io.BytesIO(result_bytes))
    assert len(reader.pages) == 1
    extracted = reader.pages[0].extract_text()
    assert SENSITIVE_TEXT not in extracted


def test_redact_pdf_page_raises_file_not_found_error_for_nonexistent_path(tmp_path):
    from backend.pdf_redact import redact_pdf_page

    missing_path = tmp_path / "does-not-exist.pdf"
    region = RedactionRegion(page=1, x0=0, y0=0, x1=100, y1=100)

    with pytest.raises(FileNotFoundError):
        redact_pdf_page(missing_path, 1, [region])


def test_redact_pdf_page_raises_value_error_for_non_pdf_extension(tmp_path):
    from backend.pdf_redact import redact_pdf_page

    wrong_ext_path = tmp_path / "not-a-pdf.txt"
    wrong_ext_path.write_text("merhaba")
    region = RedactionRegion(page=1, x0=0, y0=0, x1=100, y1=100)

    with pytest.raises(ValueError):
        redact_pdf_page(wrong_ext_path, 1, [region])


def test_redact_pdf_page_raises_value_error_when_page_number_exceeds_page_count(tmp_path):
    from backend.pdf_redact import redact_pdf_page

    pdf_path = tmp_path / "kisa.pdf"
    _write_pdf_with_text(pdf_path, ["tek sayfa"])
    region = RedactionRegion(page=5, x0=0, y0=0, x1=100, y1=100)

    with pytest.raises(ValueError):
        redact_pdf_page(pdf_path, 5, [region])


# --- Red-team bulgusu 1 (KOORDINAT UZAYI): regions PDF NOKTA uzayinda,
# sol-alt kokenli olmali - eski implementasyon bunlari dogrudan piksel
# uzayinda (sol-ust kokenli) ciziyordu, bu da caller sozlesmeye (docstring)
# uyunca kutuyu YANLIS yere/boyuta koyardi. ---


def test_redact_pdf_page_places_the_black_box_at_the_correct_pdf_point_location(tmp_path):
    """`_build_pdf_bytes` her sayfa icin 300x300 pt'lik bir MediaBox
    uretiyor. Sayfanin ALT-SOL kosesine yakin, KUCUK bir bolge seciyoruz
    (PDF nokta uzayi, y=0 sayfanin ALTI). Eski (hatali) implementasyon bu
    koordinatlari HAM piksel olarak yorumlardi - image cok daha buyuk
    oldugu icin (pdf2image varsayilan 200 DPI, 72'ye karsi ~2.78x olcek),
    bu da kutuyu goruntunun SOL-UST kosesine (sayfanin USTUNE, YANLIS
    yere) cizerdi. Dogru implementasyon kutuyu goruntunun ALT-SOL
    kosesine cizmeli - iki konum GERCEKTEN farkli piksel bolgeleri, bu
    yuzden bu test eski koda karsi BASARISIZ olurdu."""
    from backend.pdf_redact import redact_pdf_page

    pdf_path = tmp_path / "buyuk.pdf"
    _write_pdf_with_text(pdf_path, ["arka plan metni yok sayilir"])

    # PDF nokta uzayinda, sayfanin ALT-SOL kosesine yakin kucuk bir bolge
    # (sayfa 300x300 pt, y0/y1 kucuk = PDF'in ALTI).
    region = RedactionRegion(page=1, x0=10, y0=10, x1=40, y1=40)

    result_bytes = redact_pdf_page(pdf_path, 1, [region])

    # `redact_pdf_page`'in ciktisi, PIL'in image.save(format="PDF")'iyle
    # tek bir goruntu XObject'i iceren bir PDF - bunu `pdf2image` ile
    # YENIDEN rasterize etmek (farkli/varsayilan bir DPI ile) piksel
    # olceklerini bozar. Bunun yerine `pypdf` ile GOMULU goruntuyu
    # DOGRUDAN cikariyoruz - bu, redact_pdf_page'in orijinal rasterize
    # ettigi goruntuyle (hicbir ikinci-rasterizasyon olceklemesi olmadan)
    # AYNI piksel dizisidir.
    result_reader = PdfReader(io.BytesIO(result_bytes))
    embedded_image = next(iter(result_reader.pages[0].images)).image.convert("RGB")
    image_width_px, image_height_px = embedded_image.size
    result_image = embedded_image

    # DOGRU konum: bolge (x0=10,y0=10,x1=40,y1=40 pt) olceklenip
    # dikey-cevrilip goruntuye cizilince, ortasi yaklasik
    # (25*scale, image_height - 25*scale) piksel civarinda olur -
    # goruntunun ALT-SOL bolgesinde, KESINLIKLE kutunun icinde kalan bir
    # nokta seciliyor.
    scale = image_width_px / 300.0
    correct_pixel = (int(25 * scale), image_height_px - int(25 * scale))
    assert result_image.getpixel(correct_pixel) == (0, 0, 0)

    # ESKI (HATALI) konum: ham piksel yorumuyla kutunun cizilecegi yer
    # (dogrudan x0=10..x1=40, y0=10..y1=40 piksel, hic olcekleme/donusum
    # OLMADAN) - goruntunun SOL-UST kosesine yakin - BOYANMAMIS (arka
    # plan beyaz) kalmali, cunku dogru implementasyon kutuyu ORAYA
    # cizmiyor.
    old_buggy_pixel = (25, 25)
    assert result_image.getpixel(old_buggy_pixel) != (0, 0, 0)


def test_redact_pdf_page_raises_value_error_when_region_exceeds_real_page_bounds(tmp_path):
    """Red-team bulgusu 2: bolge, sayfanin GERCEK (mediabox) boyutlarini
    asarsa `ImageDraw.rectangle`'in sessizce kirpmasina izin verilmemeli -
    `redact_pdf_page` cizmeden ONCE acik bir `ValueError` firlatmali."""
    from backend.pdf_redact import redact_pdf_page

    pdf_path = tmp_path / "kucuk_sayfa.pdf"
    _write_pdf_with_text(pdf_path, ["tek sayfa"])  # MediaBox 300x300 pt

    # x1=350 > gercek sayfa genisligi (300pt).
    region = RedactionRegion(page=1, x0=0, y0=0, x1=350, y1=100)

    with pytest.raises(ValueError, match=r"(?i)sayfa"):
        redact_pdf_page(pdf_path, 1, [region])


# --- Model-seviyesi testler: RedactionRegion / PlanStep.redactionRegions ---
# (backend/models.py henuz OperationType.REDACT / RedactionRegion /
# PlanStep.redactionRegions / PlanStep.redactedFileName tanimlamiyor - bu
# testler AttributeError ile KIRMIZI kalmali.)


def test_redaction_region_rejects_x1_not_greater_than_x0():
    with pytest.raises(Exception):
        RedactionRegion(page=1, x0=100, y0=0, x1=50, y1=100)


def test_redaction_region_rejects_y1_not_greater_than_y0():
    with pytest.raises(Exception):
        RedactionRegion(page=1, x0=0, y0=100, x1=100, y1=50)


def test_plan_step_rejects_empty_redaction_regions_list_for_redact():
    with pytest.raises(Exception):
        PlanStep(
            order=0,
            operationType=OperationType.REDACT,
            targetFolder="2026-08",
            affectedFileCount=1,
            fileNames=["gizli.pdf"],
            redactionRegions=[],
            redactedFileName="gizli_karartilmis.pdf",
        )
