from unittest.mock import patch

import pytest

from backend.pdf_ocr import ocr_pdf_file


def test_ocr_pdf_file_returns_text_per_page_in_order(tmp_path):
    pdf_path = tmp_path / "test.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 fake")

    fake_images = ["sayfa-1-img", "sayfa-2-img", "sayfa-3-img"]

    with patch("backend.pdf_ocr._pdf_to_images", return_value=fake_images) as mock_to_images, \
            patch(
                "backend.pdf_ocr._run_ocr_engine",
                side_effect=["birinci sayfa metni", "ikinci sayfa metni", "ucuncu sayfa metni"],
            ) as mock_ocr:
        result = ocr_pdf_file(pdf_path)

    mock_to_images.assert_called_once_with(pdf_path)
    assert result == ["birinci sayfa metni", "ikinci sayfa metni", "ucuncu sayfa metni"]
    assert mock_ocr.call_count == 3


def test_ocr_pdf_file_raises_file_not_found_error_for_nonexistent_path(tmp_path):
    missing_path = tmp_path / "does-not-exist.pdf"

    with pytest.raises(FileNotFoundError):
        ocr_pdf_file(missing_path)


def test_ocr_pdf_file_raises_value_error_for_non_pdf_extension(tmp_path):
    wrong_ext_path = tmp_path / "not-a-pdf.txt"
    wrong_ext_path.write_text("merhaba")

    with pytest.raises(ValueError):
        ocr_pdf_file(wrong_ext_path)


def test_ocr_pdf_file_returns_empty_list_for_zero_page_pdf(tmp_path):
    pdf_path = tmp_path / "empty.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 fake")

    with patch("backend.pdf_ocr._pdf_to_images", return_value=[]), \
            patch("backend.pdf_ocr._run_ocr_engine") as mock_ocr:
        result = ocr_pdf_file(pdf_path)

    assert result == []
    mock_ocr.assert_not_called()


def test_ocr_pdf_file_propagates_exception_from_pdf_to_images(tmp_path):
    pdf_path = tmp_path / "corrupt.pdf"
    pdf_path.write_bytes(b"bozuk-icerik-degil-gercek-pdf")

    with patch("backend.pdf_ocr._pdf_to_images", side_effect=RuntimeError("PDF acilamiyor")):
        with pytest.raises(RuntimeError):
            ocr_pdf_file(pdf_path)


def test_ocr_pdf_file_strips_whitespace_from_ocr_text(tmp_path):
    pdf_path = tmp_path / "test.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 fake")

    with patch("backend.pdf_ocr._pdf_to_images", return_value=["tek-sayfa-img"]), \
            patch("backend.pdf_ocr._run_ocr_engine", return_value="  hello  \n"):
        result = ocr_pdf_file(pdf_path)

    assert result == ["hello"]
