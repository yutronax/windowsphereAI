# Saga #329: image-kirpma-thumbnail (TEST-FIRST / red step) -
# `backend/image_ops.py` (crop_image/create_thumbnail) henuz YOK. Bu
# testler simdilik KIRMIZI kalmali (ModuleNotFoundError/ImportError -
# EXCEL_FILTER/EXCEL_CREATE'in red-step testleriyle AYNI desen).
# Referans: artifacts/image-kirpma-thumbnail/atdd.md (AC-1, AC-3, AC-4,
# AC-6, AC-7), plan.md (crop_image/create_thumbnail imzalari, "img.crop()
# sessizce hata vermez, sinir kontrolu ELLE yapilmali" riski).

import pytest
from PIL import Image

from backend.image_ops import create_thumbnail, crop_image


def _write_image(path, width: int, height: int, color: str = "red") -> None:
    Image.new("RGB", (width, height), color=color).save(path)


# ---------------------------------------------------------------------------
# crop_image(source_path, box, destination_path)
# ---------------------------------------------------------------------------


def test_crop_image_writes_the_exact_cropped_area_to_destination(tmp_path):
    # AC-1: verilen box TAM olarak kirpilir, kaynak degismez.
    source = tmp_path / "kaynak.png"
    destination = tmp_path / "kirpilmis.png"
    _write_image(source, 200, 200)
    original_bytes = source.read_bytes()

    crop_image(source, (10, 10, 100, 100), destination)

    assert destination.exists()
    with Image.open(destination) as cropped:
        assert cropped.size == (90, 90)
    assert source.read_bytes() == original_bytes


def test_crop_image_raises_and_writes_no_file_when_box_exceeds_source_bounds(tmp_path):
    # AC-3: kaynak sinirlarini asan bir box - Pillow'un img.crop() KENDISI
    # hata vermez (sessizce siyah/bos alanla doldurur), bu yuzden bu
    # kontrolun crop_image ICINDE, img.crop() cagrilmadan ONCE ELLE
    # yapildigini dogrular (plan.md Risks). Kaynak 200x200 iken box
    # (0,0,500,500) GERCEKTEN sinir disi.
    source = tmp_path / "kaynak.png"
    destination = tmp_path / "kirpilmis.png"
    _write_image(source, 200, 200)

    with pytest.raises(Exception):
        crop_image(source, (0, 0, 500, 500), destination)

    assert not destination.exists()


def test_crop_image_raises_and_writes_no_file_when_box_has_non_positive_width(tmp_path):
    # x1 <= x0 gecersiz geometri.
    source = tmp_path / "kaynak.png"
    destination = tmp_path / "kirpilmis.png"
    _write_image(source, 200, 200)

    with pytest.raises(Exception):
        crop_image(source, (100, 10, 50, 100), destination)

    assert not destination.exists()


def test_crop_image_raises_and_writes_no_file_when_box_has_non_positive_height(tmp_path):
    # y1 <= y0 gecersiz geometri.
    source = tmp_path / "kaynak.png"
    destination = tmp_path / "kirpilmis.png"
    _write_image(source, 200, 200)

    with pytest.raises(Exception):
        crop_image(source, (10, 100, 100, 50), destination)

    assert not destination.exists()


def test_crop_image_raises_and_writes_no_file_when_source_is_missing(tmp_path):
    # AC-7: kaynak yok.
    source = tmp_path / "yok.png"
    destination = tmp_path / "kirpilmis.png"

    with pytest.raises(Exception):
        crop_image(source, (10, 10, 100, 100), destination)

    assert not destination.exists()


def test_crop_image_raises_and_writes_no_file_when_source_is_corrupt(tmp_path):
    # AC-7: kaynak bozuk (Pillow acamiyor).
    source = tmp_path / "bozuk.png"
    destination = tmp_path / "kirpilmis.png"
    source.write_bytes(b"not a real image")

    with pytest.raises(Exception):
        crop_image(source, (10, 10, 100, 100), destination)

    assert not destination.exists()


# ---------------------------------------------------------------------------
# create_thumbnail(source_path, max_width, max_height, destination_path)
# ---------------------------------------------------------------------------


def test_create_thumbnail_shrinks_preserving_aspect_ratio_without_stretching(tmp_path):
    # AC-4: kaynak 400x200 (2:1 oran), max_width=100, max_height=100 iken
    # oran KORUNARAK kucultulur - cikti TAM 100x100 OLMAMALI (esnetme
    # YOK), her iki boyut da 100'u ASMAMALI. Beklenen: 100x50.
    source = tmp_path / "kaynak.png"
    destination = tmp_path / "kucuk.png"
    _write_image(source, 400, 200)
    original_bytes = source.read_bytes()

    create_thumbnail(source, 100, 100, destination)

    assert destination.exists()
    with Image.open(destination) as thumb:
        width, height = thumb.size
        assert width <= 100
        assert height <= 100
        assert (width, height) == (100, 50)
        assert (width, height) != (100, 100)
    assert source.read_bytes() == original_bytes


def test_create_thumbnail_raises_and_writes_no_file_when_max_width_is_zero(tmp_path):
    source = tmp_path / "kaynak.png"
    destination = tmp_path / "kucuk.png"
    _write_image(source, 400, 200)

    with pytest.raises(Exception):
        create_thumbnail(source, 0, 100, destination)

    assert not destination.exists()


def test_create_thumbnail_raises_and_writes_no_file_when_max_height_is_negative(tmp_path):
    source = tmp_path / "kaynak.png"
    destination = tmp_path / "kucuk.png"
    _write_image(source, 400, 200)

    with pytest.raises(Exception):
        create_thumbnail(source, 100, -10, destination)

    assert not destination.exists()


def test_create_thumbnail_raises_and_writes_no_file_when_source_is_missing(tmp_path):
    # AC-7.
    source = tmp_path / "yok.png"
    destination = tmp_path / "kucuk.png"

    with pytest.raises(Exception):
        create_thumbnail(source, 100, 100, destination)

    assert not destination.exists()


def test_create_thumbnail_raises_and_writes_no_file_when_source_is_corrupt(tmp_path):
    # AC-7: kaynak bozuk (Pillow acamiyor).
    source = tmp_path / "bozuk.png"
    destination = tmp_path / "kucuk.png"
    source.write_bytes(b"not a real image")

    with pytest.raises(Exception):
        create_thumbnail(source, 100, 100, destination)

    assert not destination.exists()
