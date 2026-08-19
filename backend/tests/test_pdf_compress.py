# Saga #322: pdf-sikistirma (red step) - backend/pdf_compress.py henuz
# eklenmedi, bu dosyanin TAMAMI import asamasinda basarisiz olmali
# (ModuleNotFoundError) - beklenen kirmizi durum. code-copilot
# `compress_pdf(source_path, destination_path) -> bool`'u
# backend/pdf_compress.py'ye ekledikten sonra bu testler calisir hale
# gelmeli.
#
# `compress_pdf(source_path: Path, destination_path: Path) -> bool` -
# atdd.md/plan.md'de tasarlanan imza ve davranistir (bkz.
# artifacts/pdf-sikistirma/plan.md, New Files tablosu):
# - Gercek sikisma saglanirsa (sonuc < kaynak boyutu) destination_path'e
#   atomik yazilir, `True` doner.
# - "Buyume korumasi": sonuc boyutu >= kaynak boyutu ise destination_path'e
#   HICBIR SEY yazilmaz, `False` doner (hata DEGIL).
# - Kaynak acilamiyorsa (bozuk PDF / dosya yok) exception firlatir
#   (yakalanmaz - orchestrator PlanApplicationError'a cevirir).
# Desen test_pdf_pages.py ile AYNI (tempfile+atomik-replace, kaynak asla
# degismez, gecersiz/basarisiz durumda hicbir dosya yazilmaz).

import pytest
from pypdf import PdfWriter

from backend.pdf_compress import compress_pdf


def _write_compressible_pdf(path, page_count: int = 5) -> None:
    # Gercek bir sikisma senaryosu uretmek icin reportlab ile
    # SIKISTIRILMAMIS (pageCompression=0) content stream'leri olan,
    # ayni buyuk metin blogunu tekrar tekrar ciren birden fazla sayfa
    # uretiyoruz. pypdf'in `compress_content_streams()` (flate encode)
    # bu tekrarlanan, sikistirilmamis content stream'lerde belirgin bir
    # boyut kucultmesi saglamali.
    from reportlab.pdfgen import canvas

    c = canvas.Canvas(str(path), pageCompression=0)
    repeated_line = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA "
    for _ in range(page_count):
        y = 780
        for _ in range(60):
            c.drawString(20, y, repeated_line)
            y -= 10
            if y < 20:
                break
        c.showPage()
    c.save()


def _write_minimal_pdf(path) -> None:
    # Tek bos sayfa - zaten minimal boyutta, sikistirmadan
    # kazanilacak bir sey yok (buyume korumasi tetiklenmeli).
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    with open(path, "wb") as f:
        writer.write(f)
    writer.close()


def _write_broken_pdf(path) -> None:
    (path).write_bytes(b"this is not a pdf at all")


# --- compress_pdf: happy path (AC-1) ---


def test_compress_pdf_returns_true_and_writes_a_smaller_destination_file(tmp_path):
    source = tmp_path / "source.pdf"
    destination = tmp_path / "compressed.pdf"
    _write_compressible_pdf(source)
    original_size = source.stat().st_size

    result = compress_pdf(source, destination)

    assert result is True
    assert destination.exists()
    assert destination.stat().st_size < original_size


def test_compress_pdf_does_not_modify_the_source_file(tmp_path):
    source = tmp_path / "source.pdf"
    destination = tmp_path / "compressed.pdf"
    _write_compressible_pdf(source)
    original_bytes = source.read_bytes()

    compress_pdf(source, destination)

    assert source.read_bytes() == original_bytes


# --- compress_pdf: buyume korumasi (AC-2/AC-5) ---


def test_compress_pdf_returns_false_and_writes_no_file_when_already_minimal(tmp_path):
    source = tmp_path / "source.pdf"
    destination = tmp_path / "compressed.pdf"
    _write_minimal_pdf(source)

    result = compress_pdf(source, destination)

    assert result is False
    assert not destination.exists()


def test_compress_pdf_does_not_modify_the_source_file_on_growth_protection(tmp_path):
    source = tmp_path / "source.pdf"
    destination = tmp_path / "compressed.pdf"
    _write_minimal_pdf(source)
    original_bytes = source.read_bytes()

    compress_pdf(source, destination)

    assert source.read_bytes() == original_bytes


# --- compress_pdf: bozuk/gecersiz kaynak (AC-3) ---


def test_compress_pdf_raises_for_a_missing_source_file(tmp_path):
    source = tmp_path / "does_not_exist.pdf"
    destination = tmp_path / "compressed.pdf"

    with pytest.raises(Exception):
        compress_pdf(source, destination)

    assert not destination.exists()


def test_compress_pdf_raises_for_an_invalid_pdf_source(tmp_path):
    source = tmp_path / "broken.pdf"
    destination = tmp_path / "compressed.pdf"
    _write_broken_pdf(source)

    with pytest.raises(Exception):
        compress_pdf(source, destination)

    assert not destination.exists()
