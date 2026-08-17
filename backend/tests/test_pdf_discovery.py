from backend.pdf_discovery import discover_pdf_files


def test_discover_pdf_files_returns_empty_list_for_nonexistent_folder(tmp_path):
    assert discover_pdf_files(tmp_path / "does-not-exist") == []


def test_discover_pdf_files_returns_empty_list_for_folder_with_no_pdfs(tmp_path):
    (tmp_path / "a.txt").write_text("merhaba")

    assert discover_pdf_files(tmp_path) == []


def test_discover_pdf_files_finds_pdf_files_case_insensitively(tmp_path):
    (tmp_path / "a.pdf").write_bytes(b"%PDF-1.4 fake")
    (tmp_path / "b.PDF").write_bytes(b"%PDF-1.4 fake")

    files = discover_pdf_files(tmp_path)

    assert sorted(f.filename for f in files) == ["a.pdf", "b.PDF"]


def test_discover_pdf_files_ignores_non_pdf_files(tmp_path):
    (tmp_path / "a.pdf").write_bytes(b"%PDF-1.4 fake")
    (tmp_path / "b.txt").write_text("merhaba")

    files = discover_pdf_files(tmp_path)

    assert [f.filename for f in files] == ["a.pdf"]


def test_discover_pdf_files_does_not_recurse_into_subfolders(tmp_path):
    (tmp_path / "a.pdf").write_bytes(b"%PDF-1.4 fake")
    subfolder = tmp_path / "alt-klasor"
    subfolder.mkdir()
    (subfolder / "b.pdf").write_bytes(b"%PDF-1.4 fake")

    files = discover_pdf_files(tmp_path)

    assert [f.filename for f in files] == ["a.pdf"]


def test_discover_pdf_files_sets_created_at_as_a_non_blank_iso_timestamp(tmp_path):
    (tmp_path / "a.pdf").write_bytes(b"%PDF-1.4 fake")

    files = discover_pdf_files(tmp_path)

    assert files[0].createdAt.strip() != ""
    assert "T" in files[0].createdAt


def test_discover_pdf_files_returns_results_sorted_by_filename(tmp_path):
    (tmp_path / "c.pdf").write_bytes(b"%PDF-1.4 fake")
    (tmp_path / "a.pdf").write_bytes(b"%PDF-1.4 fake")
    (tmp_path / "b.pdf").write_bytes(b"%PDF-1.4 fake")

    files = discover_pdf_files(tmp_path)

    assert [f.filename for f in files] == ["a.pdf", "b.pdf", "c.pdf"]
