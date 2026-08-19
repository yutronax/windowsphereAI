# Saga #328: zip-temel-operasyonlar (TEST-FIRST / red step) -
# `backend/zip_ops.py` (create_zip/add_to_zip/extract_zip/merge_zips/
# list_zip_entries) henuz YOK. Bu testler simdilik KIRMIZI kalmali
# (ModuleNotFoundError/ImportError - beklenen red durumu).
# Referans: artifacts/zip-temel-operasyonlar/atdd.md (AC-1, AC-2, AC-3/AC-S1,
# AC-4, AC-5, AC-6), plan.md (New Files tablosu - fonksiyon imzaları).
# Desen test_excel_rows.py/test_pdf_pages.py ile AYNI (tempfile+atomik-
# replace, kaynak asla değişmez, geçersiz/eksik girdide hiçbir dosya
# yazılmaz).

import zipfile
from pathlib import Path

import pytest

from backend.zip_ops import (
    add_to_zip,
    create_zip,
    extract_zip,
    list_zip_entries,
    merge_zips,
)


def _write_source_files(root: Path, names: list[str], content: bytes = b"data") -> list[Path]:
    paths = []
    for name in names:
        path = root / name
        path.write_bytes(content)
        paths.append(path)
    return paths


def _write_zip(path: Path, entries: dict[str, bytes]) -> None:
    with zipfile.ZipFile(path, "w") as zf:
        for name, data in entries.items():
            zf.writestr(name, data)


# ---------------------------------------------------------------------------
# create_zip(source_paths, destination_path)
# ---------------------------------------------------------------------------


def test_create_zip_writes_exactly_the_given_source_files(tmp_path):
    # AC-1: verilen dosyalar zip'e tam olarak girer, kaynaklar değişmez.
    sources = _write_source_files(tmp_path, ["a.pdf", "b.xlsx"])
    destination = tmp_path / "arsiv.zip"

    create_zip(sources, destination)

    assert destination.exists()
    with zipfile.ZipFile(destination) as zf:
        assert sorted(zf.namelist()) == ["a.pdf", "b.xlsx"]
    for source in sources:
        assert source.exists()


def test_create_zip_raises_and_creates_no_file_when_a_source_is_missing(tmp_path):
    existing = _write_source_files(tmp_path, ["a.pdf"])[0]
    missing = tmp_path / "yok.pdf"
    destination = tmp_path / "arsiv.zip"

    with pytest.raises(Exception):
        create_zip([existing, missing], destination)

    assert not destination.exists()


# ---------------------------------------------------------------------------
# add_to_zip(source_path, files_to_add, destination_path)
# ---------------------------------------------------------------------------


def test_add_to_zip_writes_old_content_plus_new_files_to_a_new_zip_and_leaves_source_untouched(tmp_path):
    # AC-4: YENİ dosyaya kaynağın TÜM eski içeriği + yeni dosya yazılır,
    # kaynak zip DEĞİŞMEZ.
    source_zip = tmp_path / "kaynak.zip"
    _write_zip(source_zip, {"a.pdf": b"eski-a", "b.xlsx": b"eski-b"})
    original_bytes = source_zip.read_bytes()

    new_file = _write_source_files(tmp_path, ["c.docx"], content=b"yeni-c")[0]
    destination = tmp_path / "eklendi.zip"

    add_to_zip(source_zip, [new_file], destination)

    assert destination.exists()
    with zipfile.ZipFile(destination) as zf:
        assert sorted(zf.namelist()) == ["a.pdf", "b.xlsx", "c.docx"]
        assert zf.read("a.pdf") == b"eski-a"
        assert zf.read("b.xlsx") == b"eski-b"
        assert zf.read("c.docx") == b"yeni-c"
    assert source_zip.read_bytes() == original_bytes


def test_add_to_zip_raises_and_creates_no_destination_when_source_zip_is_missing(tmp_path):
    source_zip = tmp_path / "yok.zip"
    new_file = _write_source_files(tmp_path, ["c.docx"])[0]
    destination = tmp_path / "eklendi.zip"

    with pytest.raises(Exception):
        add_to_zip(source_zip, [new_file], destination)

    assert not destination.exists()


def test_add_to_zip_raises_and_creates_no_destination_when_source_zip_is_corrupt(tmp_path):
    source_zip = tmp_path / "bozuk.zip"
    corrupt_bytes = b"not a real zip"
    source_zip.write_bytes(corrupt_bytes)
    new_file = _write_source_files(tmp_path, ["c.docx"])[0]
    destination = tmp_path / "eklendi.zip"

    with pytest.raises(Exception):
        add_to_zip(source_zip, [new_file], destination)

    assert not destination.exists()
    assert source_zip.read_bytes() == corrupt_bytes


# ---------------------------------------------------------------------------
# extract_zip(source_path, destination_folder, allowed_root)
# ---------------------------------------------------------------------------


def test_extract_zip_writes_content_into_the_given_destination_folder(tmp_path):
    # AC-2: içerik kullanıcının BELİRTTİĞİ klasöre çıkarılır (zip ADINDAN
    # türetilen bir klasöre DEĞİL).
    source_zip = tmp_path / "arsiv.zip"
    _write_zip(source_zip, {"a.pdf": b"icerik-a", "alt/b.xlsx": b"icerik-b"})
    destination_folder = tmp_path / "cikti"

    extract_zip(source_zip, destination_folder, allowed_root=tmp_path)

    assert (destination_folder / "a.pdf").read_bytes() == b"icerik-a"
    assert (destination_folder / "alt" / "b.xlsx").read_bytes() == b"icerik-b"


def test_extract_zip_raises_and_extracts_nothing_when_source_is_missing(tmp_path):
    source_zip = tmp_path / "yok.zip"
    destination_folder = tmp_path / "cikti"

    with pytest.raises(Exception):
        extract_zip(source_zip, destination_folder, allowed_root=tmp_path)

    assert not destination_folder.exists()


def test_extract_zip_raises_and_extracts_nothing_when_source_is_corrupt(tmp_path):
    source_zip = tmp_path / "bozuk.zip"
    source_zip.write_bytes(b"not a real zip")
    destination_folder = tmp_path / "cikti"

    with pytest.raises(Exception):
        extract_zip(source_zip, destination_folder, allowed_root=tmp_path)

    assert not destination_folder.exists()


# --- extract_zip: zip-slip (AC-3/AC-S1) - "tüm-ya-da-hiç" ön-tarama garantisi.
# Test zip'inin İLK girişi MEŞRU (`legit.txt`), İKİNCİ girişi KÖTÜ NİYETLİ -
# çıkarma sonrası MEŞRU dosyanın BİLE diskte olmadığı doğrulanır (ön-tarama
# TÜM girişleri gerçek çıkarmadan ÖNCE kontrol etmeli).


def test_extract_zip_rejects_posix_style_relative_escape_and_extracts_nothing(tmp_path):
    source_zip = tmp_path / "kotu.zip"
    _write_zip(source_zip, {"legit.txt": b"mesru", "../../evil.txt": b"kotu"})
    destination_folder = tmp_path / "cikti"

    with pytest.raises(Exception):
        extract_zip(source_zip, destination_folder, allowed_root=tmp_path)

    assert not (destination_folder / "legit.txt").exists()
    assert not (tmp_path / "evil.txt").exists()


def test_extract_zip_rejects_absolute_windows_path_and_extracts_nothing(tmp_path):
    source_zip = tmp_path / "kotu.zip"
    _write_zip(source_zip, {"legit.txt": b"mesru", r"C:\Windows\evil.txt": b"kotu"})
    destination_folder = tmp_path / "cikti"

    with pytest.raises(Exception):
        extract_zip(source_zip, destination_folder, allowed_root=tmp_path)

    assert not (destination_folder / "legit.txt").exists()


def test_extract_zip_rejects_unc_path_and_extracts_nothing(tmp_path):
    source_zip = tmp_path / "kotu.zip"
    _write_zip(source_zip, {"legit.txt": b"mesru", r"\\server\share\evil.txt": b"kotu"})
    destination_folder = tmp_path / "cikti"

    with pytest.raises(Exception):
        extract_zip(source_zip, destination_folder, allowed_root=tmp_path)

    assert not (destination_folder / "legit.txt").exists()


# ---------------------------------------------------------------------------
# merge_zips(source_paths, destination_path)
# ---------------------------------------------------------------------------


def test_merge_zips_writes_all_entries_of_both_source_zips_to_a_new_zip(tmp_path):
    # AC-5: YENİ zip TÜM kaynak zip'lerin TÜM girişlerini içerir, kaynaklar
    # değişmez.
    zip_a = tmp_path / "a.zip"
    zip_b = tmp_path / "b.zip"
    _write_zip(zip_a, {"a1.txt": b"a1", "a2.txt": b"a2"})
    _write_zip(zip_b, {"b1.txt": b"b1"})
    original_a = zip_a.read_bytes()
    original_b = zip_b.read_bytes()
    destination = tmp_path / "birlesik.zip"

    merge_zips([zip_a, zip_b], destination)

    with zipfile.ZipFile(destination) as zf:
        assert sorted(zf.namelist()) == ["a1.txt", "a2.txt", "b1.txt"]
        assert zf.read("a1.txt") == b"a1"
        assert zf.read("b1.txt") == b"b1"
    assert zip_a.read_bytes() == original_a
    assert zip_b.read_bytes() == original_b


def test_merge_zips_raises_and_creates_no_destination_when_a_source_is_missing(tmp_path):
    zip_a = tmp_path / "a.zip"
    _write_zip(zip_a, {"a1.txt": b"a1"})
    missing_zip = tmp_path / "yok.zip"
    destination = tmp_path / "birlesik.zip"

    with pytest.raises(Exception):
        merge_zips([zip_a, missing_zip], destination)

    assert not destination.exists()


def test_merge_zips_raises_and_creates_no_destination_when_a_source_is_corrupt(tmp_path):
    zip_a = tmp_path / "a.zip"
    _write_zip(zip_a, {"a1.txt": b"a1"})
    corrupt_zip = tmp_path / "bozuk.zip"
    corrupt_zip.write_bytes(b"not a real zip")
    destination = tmp_path / "birlesik.zip"

    with pytest.raises(Exception):
        merge_zips([zip_a, corrupt_zip], destination)

    assert not destination.exists()


# ---------------------------------------------------------------------------
# list_zip_entries(source_path)
# ---------------------------------------------------------------------------


def test_list_zip_entries_returns_name_and_size_for_each_entry(tmp_path):
    # AC-5b: girişlerin ad/boyut bilgisi döner, dosya sistemi hiç değişmez.
    source_zip = tmp_path / "arsiv.zip"
    _write_zip(source_zip, {"a.pdf": b"1234567890", "b.xlsx": b"12"})

    entries = list_zip_entries(source_zip)

    by_name = {entry["name"]: entry for entry in entries}
    assert set(by_name.keys()) == {"a.pdf", "b.xlsx"}
    assert by_name["a.pdf"]["size"] == 10
    assert by_name["b.xlsx"]["size"] == 2


def test_list_zip_entries_raises_when_source_is_missing(tmp_path):
    source_zip = tmp_path / "yok.zip"

    with pytest.raises(Exception):
        list_zip_entries(source_zip)


def test_list_zip_entries_raises_when_source_is_corrupt(tmp_path):
    source_zip = tmp_path / "bozuk.zip"
    source_zip.write_bytes(b"not a real zip")

    with pytest.raises(Exception):
        list_zip_entries(source_zip)
