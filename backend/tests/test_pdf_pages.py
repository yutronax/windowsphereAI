# Saga #321: pdf-sayfa-araligi-secimi (red step) - backend/pdf_pages.py
# henuz eklenmedi, bu dosyanin TAMAMI import asamasinda basarisiz olmali
# (ModuleNotFoundError) - beklenen kirmizi durum. code-copilot
# `parse_page_spec`/`extract_pdf_pages`/`delete_pdf_pages`'i
# backend/pdf_pages.py'ye ekledikten sonra bu testler calisir hale gelmeli.
#
# `parse_page_spec(page_spec: str, page_count: int) -> list[int]` (1-indexed
# donus), `extract_pdf_pages(source_path, page_spec, destination_path)`,
# `delete_pdf_pages(source_path, page_spec, destination_path)` -
# atdd.md/plan.md'de tasarlanan isimlerdir (bkz.
# artifacts/pdf-sayfa-araligi-secimi/plan.md, New Files tablosu).
# Desen test_excel_filter.py ile AYNI (tempfile+atomik-replace, kaynak asla
# degismez, gecersiz girdide hicbir dosya yazilmaz).

import pytest
from pypdf import PdfReader, PdfWriter

from backend.pdf_pages import extract_pdf_pages, delete_pdf_pages, parse_page_spec


def _write_pdf(path, page_count: int) -> None:
    # Her sayfaya AYIRT EDICI bir genislik veriliyor (100+i, i=0-indexed
    # sayfa sirasi) - bu sayede testler sadece sayfa SAYISINI degil, hangi
    # sayfalarin (KIMLIK+SIRA) secildigini de dogrulayabilir (red-team
    # bulgu 1, Saga #321).
    writer = PdfWriter()
    for i in range(page_count):
        writer.add_blank_page(width=100 + i, height=100 + i)
    with open(path, "wb") as f:
        writer.write(f)


# --- parse_page_spec: mixed discrete + range list (AC-1/AC-2 girdisi) ---


def test_parse_page_spec_returns_mixed_discrete_and_range_pages_in_order():
    result = parse_page_spec("1,3,5-9", page_count=10)

    assert result == [1, 3, 5, 6, 7, 8, 9]


# --- parse_page_spec: whitespace normalize (AC-6) ---


def test_parse_page_spec_trims_whitespace_and_matches_unspaced_equivalent():
    spaced = parse_page_spec(" 1, 3 , 5-9 ", page_count=10)
    unspaced = parse_page_spec("1,3,5-9", page_count=10)

    assert spaced == unspaced == [1, 3, 5, 6, 7, 8, 9]


# --- parse_page_spec: reversed range is an error (AC-3) ---


def test_parse_page_spec_raises_value_error_for_reversed_range():
    with pytest.raises(ValueError):
        parse_page_spec("9-5", page_count=10)


# --- parse_page_spec: out-of-document page number is an error (AC-4) ---


def test_parse_page_spec_raises_value_error_for_page_number_beyond_document():
    with pytest.raises(ValueError):
        parse_page_spec("1,3,8", page_count=5)


# --- parse_page_spec: duplicate pages are silently deduplicated (AC-7) ---


def test_parse_page_spec_deduplicates_repeated_pages_preserving_order():
    result = parse_page_spec("1,1,3", page_count=10)

    assert result == [1, 3]


# --- parse_page_spec: empty spec is an error ---


def test_parse_page_spec_raises_value_error_for_empty_string():
    with pytest.raises(ValueError):
        parse_page_spec("", page_count=10)


def test_parse_page_spec_raises_value_error_for_blank_string():
    with pytest.raises(ValueError):
        parse_page_spec("   ", page_count=10)


# --- extract_pdf_pages: happy path (AC-1) ---


def test_extract_pdf_pages_writes_selected_pages_in_original_order(tmp_path):
    source = tmp_path / "source.pdf"
    destination = tmp_path / "extracted.pdf"
    _write_pdf(source, 10)

    extract_pdf_pages(source, "1,3,5-9", destination)

    assert destination.exists()
    reader = PdfReader(str(destination))
    assert len(reader.pages) == 7
    # Sadece SAYIYI degil, HANGI sayfalarin ORIJINAL sirayla secildigini de
    # dogrula: "1,3,5-9" -> 0-indexed [0,2,4,5,6,7,8] -> width [100,102,
    # 104,105,106,107,108] (red-team bulgu 1, Saga #321).
    assert [p.mediabox.width for p in reader.pages] == [100, 102, 104, 105, 106, 107, 108]


def test_extract_pdf_pages_does_not_modify_the_source_file(tmp_path):
    source = tmp_path / "source.pdf"
    destination = tmp_path / "extracted.pdf"
    _write_pdf(source, 10)
    original_bytes = source.read_bytes()

    extract_pdf_pages(source, "1,3,5-9", destination)

    assert source.read_bytes() == original_bytes


def test_extract_pdf_pages_writes_no_file_when_page_spec_is_invalid(tmp_path):
    source = tmp_path / "source.pdf"
    destination = tmp_path / "extracted.pdf"
    _write_pdf(source, 10)

    with pytest.raises(ValueError):
        extract_pdf_pages(source, "9-5", destination)

    assert not destination.exists()


def test_extract_pdf_pages_writes_no_file_when_page_spec_is_out_of_document_range(tmp_path):
    source = tmp_path / "source.pdf"
    destination = tmp_path / "extracted.pdf"
    _write_pdf(source, 5)

    with pytest.raises(ValueError):
        extract_pdf_pages(source, "1,3,8", destination)

    assert not destination.exists()


# --- delete_pdf_pages: happy path (AC-2) ---


def test_delete_pdf_pages_writes_remaining_pages_in_original_order(tmp_path):
    source = tmp_path / "source.pdf"
    destination = tmp_path / "remaining.pdf"
    _write_pdf(source, 10)

    delete_pdf_pages(source, "1,3,5-9", destination)

    assert destination.exists()
    reader = PdfReader(str(destination))
    # 10 sayfadan [1,3,5,6,7,8,9] silinince [2,4,10] kalir -> 3 sayfa.
    assert len(reader.pages) == 3
    # Sadece SAYIYI degil, kalan sayfalarin DOGRU KIMLIKTE ve ORIJINAL
    # sirada oldugunu da dogrula: [2,4,10] -> 0-indexed [1,3,9] -> width
    # [101,103,109] (red-team bulgu 1, Saga #321).
    assert [p.mediabox.width for p in reader.pages] == [101, 103, 109]


def test_delete_pdf_pages_does_not_modify_the_source_file(tmp_path):
    source = tmp_path / "source.pdf"
    destination = tmp_path / "remaining.pdf"
    _write_pdf(source, 10)
    original_bytes = source.read_bytes()

    delete_pdf_pages(source, "1,3,5-9", destination)

    assert source.read_bytes() == original_bytes


# --- delete_pdf_pages: deleting all pages is an error (AC-5) ---


def test_delete_pdf_pages_raises_value_error_when_all_pages_are_deleted(tmp_path):
    source = tmp_path / "source.pdf"
    destination = tmp_path / "remaining.pdf"
    _write_pdf(source, 3)

    with pytest.raises(ValueError):
        delete_pdf_pages(source, "1-3", destination)

    assert not destination.exists()


def test_delete_pdf_pages_writes_no_file_when_page_spec_is_invalid(tmp_path):
    source = tmp_path / "source.pdf"
    destination = tmp_path / "remaining.pdf"
    _write_pdf(source, 10)

    with pytest.raises(ValueError):
        delete_pdf_pages(source, "9-5", destination)

    assert not destination.exists()


def test_delete_pdf_pages_writes_no_file_when_page_spec_is_out_of_document_range(tmp_path):
    source = tmp_path / "source.pdf"
    destination = tmp_path / "remaining.pdf"
    _write_pdf(source, 5)

    with pytest.raises(ValueError):
        delete_pdf_pages(source, "1,3,8", destination)

    assert not destination.exists()
