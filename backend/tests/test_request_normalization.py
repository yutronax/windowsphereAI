import pytest

from backend.request_normalization import normalize_request_text, normalize_selected_folder


def test_strips_leading_and_trailing_whitespace():
    assert normalize_request_text("  PDF'leri sırala  ") == "PDF'leri sırala"


def test_leaves_an_already_trimmed_string_unchanged():
    assert normalize_request_text("PDF'leri sırala") == "PDF'leri sırala"


def test_raises_for_whitespace_only_text():
    with pytest.raises(ValueError):
        normalize_request_text("   ")


def test_raises_for_empty_text():
    with pytest.raises(ValueError):
        normalize_request_text("")


def test_preserves_internal_whitespace():
    assert normalize_request_text("  PDF'leri   tarihe göre sırala  ") == "PDF'leri   tarihe göre sırala"


def test_raises_for_tab_and_newline_only_text():
    with pytest.raises(ValueError):
        normalize_request_text("\t\n  \n\t")


def test_raises_for_unicode_whitespace_only_text():
    # U+00A0 non-breaking space, U+3000 ideographic space — Python's str.strip()
    # treats both as whitespace (red-team-requested edge case, Saga #268).
    with pytest.raises(ValueError):
        normalize_request_text("\u00a0\u3000")


def test_normalize_selected_folder_trims_whitespace():
    assert normalize_selected_folder("  C:\\Belgeler  ") == "C:\\Belgeler"


def test_normalize_selected_folder_raises_for_blank():
    with pytest.raises(ValueError):
        normalize_selected_folder("   ")
