"""Tests for backend.file_search module.

Red step (failing): Tests for a function that doesn't exist yet.
This verifies the Behavior-Contract Table from artifacts/file-search-mvp/atdd.md.
"""
import datetime as dt
import os
from pathlib import Path

import pytest

from backend.file_search import search_files
from backend.models import SearchResultItem


class TestSearchFilesNoFilters:
    """Scenario: Hiçbir filtre yok → Klasördeki tüm görünür dosyalar döner."""

    def test_returns_all_visible_files_in_folder(self, tmp_path: Path) -> None:
        """No filters returns all non-hidden files in the folder."""
        # Create test files
        (tmp_path / "report.pdf").write_text("pdf content")
        (tmp_path / "fatura_2024.docx").write_text("docx content")
        (tmp_path / "data.xlsx").write_text("xlsx content")
        (tmp_path / ".hidden").write_text("hidden content")  # Should be excluded
        (tmp_path / ".backup").write_text("backup content")  # Should be excluded

        result = search_files(tmp_path)

        assert len(result) == 3
        filenames = {item.filename for item in result}
        assert filenames == {"report.pdf", "fatura_2024.docx", "data.xlsx"}

    def test_returns_only_files_not_directories(self, tmp_path: Path) -> None:
        """No filters returns files only, not subdirectories."""
        (tmp_path / "file1.pdf").write_text("content")
        (tmp_path / "file2.txt").write_text("content")
        (tmp_path / "subdir").mkdir()  # Should be excluded

        result = search_files(tmp_path)

        assert len(result) == 2
        filenames = {item.filename for item in result}
        assert filenames == {"file1.pdf", "file2.txt"}

    def test_empty_folder_returns_empty_list(self, tmp_path: Path) -> None:
        """Empty folder returns empty list."""
        result = search_files(tmp_path)

        assert result == []

    def test_results_are_sorted(self, tmp_path: Path) -> None:
        """Results are sorted by filename (like discover_pdf_files)."""
        (tmp_path / "zebra.pdf").write_text("z")
        (tmp_path / "apple.pdf").write_text("a")
        (tmp_path / "banana.pdf").write_text("b")

        result = search_files(tmp_path)

        filenames = [item.filename for item in result]
        assert filenames == ["apple.pdf", "banana.pdf", "zebra.pdf"]


class TestSearchFilesNameContains:
    """Scenario: nameContains="fatura" → Adında 'fatura' geçen dosyalar."""

    def test_name_contains_case_insensitive(self, tmp_path: Path) -> None:
        """name_contains filter is case-insensitive."""
        (tmp_path / "fatura_2024.pdf").write_text("a")
        (tmp_path / "FATURA_2025.pdf").write_text("b")
        (tmp_path / "Fatura_2026.docx").write_text("c")
        (tmp_path / "invoice.pdf").write_text("d")

        result = search_files(tmp_path, name_contains="fatura")

        filenames = {item.filename for item in result}
        assert filenames == {"fatura_2024.pdf", "FATURA_2025.pdf", "Fatura_2026.docx"}

    def test_name_contains_substring(self, tmp_path: Path) -> None:
        """name_contains matches anywhere in filename (substring)."""
        (tmp_path / "pre_fatura_post.pdf").write_text("a")
        (tmp_path / "fatura.pdf").write_text("b")
        (tmp_path / "faturabak.txt").write_text("c")
        (tmp_path / "notfatured.pdf").write_text("d")

        result = search_files(tmp_path, name_contains="fatura")

        filenames = {item.filename for item in result}
        assert filenames == {"pre_fatura_post.pdf", "fatura.pdf", "faturabak.txt"}

    def test_name_contains_no_matches(self, tmp_path: Path) -> None:
        """name_contains with no matches returns empty list."""
        (tmp_path / "file1.pdf").write_text("a")
        (tmp_path / "file2.pdf").write_text("b")

        result = search_files(tmp_path, name_contains="fatura")

        assert result == []

    def test_name_contains_hidden_files_still_excluded(self, tmp_path: Path) -> None:
        """name_contains filter still excludes hidden files."""
        (tmp_path / "fatura_2024.pdf").write_text("a")
        (tmp_path / ".fatura_hidden.pdf").write_text("b")

        result = search_files(tmp_path, name_contains="fatura")

        filenames = {item.filename for item in result}
        assert filenames == {"fatura_2024.pdf"}


class TestSearchFilesExtension:
    """Scenario: extension="pdf" or extension=".pdf" → Sadece .pdf dosyaları."""

    def test_extension_without_dot(self, tmp_path: Path) -> None:
        """extension filter works with "pdf" (no dot)."""
        (tmp_path / "file1.pdf").write_text("a")
        (tmp_path / "file2.PDF").write_text("b")
        (tmp_path / "file3.docx").write_text("c")

        result = search_files(tmp_path, extension="pdf")

        filenames = {item.filename for item in result}
        assert filenames == {"file1.pdf", "file2.PDF"}

    def test_extension_with_dot(self, tmp_path: Path) -> None:
        """extension filter works with ".pdf" (with dot)."""
        (tmp_path / "file1.pdf").write_text("a")
        (tmp_path / "file2.PDF").write_text("b")
        (tmp_path / "file3.docx").write_text("c")

        result = search_files(tmp_path, extension=".pdf")

        filenames = {item.filename for item in result}
        assert filenames == {"file1.pdf", "file2.PDF"}

    def test_extension_case_insensitive(self, tmp_path: Path) -> None:
        """extension filter is case-insensitive."""
        (tmp_path / "file1.pdf").write_text("a")
        (tmp_path / "file2.PDF").write_text("b")
        (tmp_path / "file3.Pdf").write_text("c")
        (tmp_path / "file4.txt").write_text("d")

        result = search_files(tmp_path, extension="pdf")

        filenames = {item.filename for item in result}
        assert filenames == {"file1.pdf", "file2.PDF", "file3.Pdf"}

    def test_extension_uppercase_filter(self, tmp_path: Path) -> None:
        """extension filter with uppercase also works."""
        (tmp_path / "file1.pdf").write_text("a")
        (tmp_path / "file2.PDF").write_text("b")

        result = search_files(tmp_path, extension="PDF")

        filenames = {item.filename for item in result}
        assert filenames == {"file1.pdf", "file2.PDF"}

    def test_extension_no_matches(self, tmp_path: Path) -> None:
        """extension filter with no matches returns empty list."""
        (tmp_path / "file1.txt").write_text("a")
        (tmp_path / "file2.docx").write_text("b")

        result = search_files(tmp_path, extension="pdf")

        assert result == []

    def test_extension_filters_out_hidden_files(self, tmp_path: Path) -> None:
        """extension filter still excludes hidden files."""
        (tmp_path / "file1.pdf").write_text("a")
        (tmp_path / ".hidden.pdf").write_text("b")

        result = search_files(tmp_path, extension="pdf")

        filenames = {item.filename for item in result}
        assert filenames == {"file1.pdf"}


class TestSearchFilesModifiedTime:
    """Scenario: modifiedAfter/modifiedBefore → mtime aralıkta olan dosyalar."""

    def test_modified_after_inclusive(self, tmp_path: Path) -> None:
        """modifiedAfter filter includes files at the exact boundary (>=)."""
        base_time = dt.datetime(2024, 1, 15, 12, 0, 0, tzinfo=dt.timezone.utc)
        before_time = dt.datetime(2024, 1, 10, 12, 0, 0, tzinfo=dt.timezone.utc)
        after_time = dt.datetime(2024, 1, 20, 12, 0, 0, tzinfo=dt.timezone.utc)

        # Create files with specific mtimes
        file1 = tmp_path / "file1.pdf"
        file1.write_text("a")
        os.utime(file1, (base_time.timestamp(), base_time.timestamp()))

        file2 = tmp_path / "file2.pdf"
        file2.write_text("b")
        os.utime(file2, (before_time.timestamp(), before_time.timestamp()))

        file3 = tmp_path / "file3.pdf"
        file3.write_text("c")
        os.utime(file3, (after_time.timestamp(), after_time.timestamp()))

        result = search_files(tmp_path, modified_after=base_time)

        filenames = {item.filename for item in result}
        # Should include file1 (at boundary) and file3 (after), exclude file2 (before)
        assert filenames == {"file1.pdf", "file3.pdf"}

    def test_modified_before_inclusive(self, tmp_path: Path) -> None:
        """modifiedBefore filter includes files at the exact boundary (<=)."""
        base_time = dt.datetime(2024, 1, 15, 12, 0, 0, tzinfo=dt.timezone.utc)
        before_time = dt.datetime(2024, 1, 10, 12, 0, 0, tzinfo=dt.timezone.utc)
        after_time = dt.datetime(2024, 1, 20, 12, 0, 0, tzinfo=dt.timezone.utc)

        file1 = tmp_path / "file1.pdf"
        file1.write_text("a")
        os.utime(file1, (base_time.timestamp(), base_time.timestamp()))

        file2 = tmp_path / "file2.pdf"
        file2.write_text("b")
        os.utime(file2, (before_time.timestamp(), before_time.timestamp()))

        file3 = tmp_path / "file3.pdf"
        file3.write_text("c")
        os.utime(file3, (after_time.timestamp(), after_time.timestamp()))

        result = search_files(tmp_path, modified_before=base_time)

        filenames = {item.filename for item in result}
        # Should include file1 (at boundary) and file2 (before), exclude file3 (after)
        assert filenames == {"file1.pdf", "file2.pdf"}

    def test_modified_after_and_before_range(self, tmp_path: Path) -> None:
        """modifiedAfter and modifiedBefore together define an inclusive range."""
        start_time = dt.datetime(2024, 1, 10, 0, 0, 0, tzinfo=dt.timezone.utc)
        middle_time = dt.datetime(2024, 1, 15, 0, 0, 0, tzinfo=dt.timezone.utc)
        end_time = dt.datetime(2024, 1, 20, 0, 0, 0, tzinfo=dt.timezone.utc)
        before_range = dt.datetime(2024, 1, 5, 0, 0, 0, tzinfo=dt.timezone.utc)
        after_range = dt.datetime(2024, 1, 25, 0, 0, 0, tzinfo=dt.timezone.utc)

        file_before = tmp_path / "file_before.pdf"
        file_before.write_text("a")
        os.utime(file_before, (before_range.timestamp(), before_range.timestamp()))

        file_start = tmp_path / "file_start.pdf"
        file_start.write_text("b")
        os.utime(file_start, (start_time.timestamp(), start_time.timestamp()))

        file_middle = tmp_path / "file_middle.pdf"
        file_middle.write_text("c")
        os.utime(file_middle, (middle_time.timestamp(), middle_time.timestamp()))

        file_end = tmp_path / "file_end.pdf"
        file_end.write_text("d")
        os.utime(file_end, (end_time.timestamp(), end_time.timestamp()))

        file_after = tmp_path / "file_after.pdf"
        file_after.write_text("e")
        os.utime(file_after, (after_range.timestamp(), after_range.timestamp()))

        result = search_files(
            tmp_path, modified_after=start_time, modified_before=end_time
        )

        filenames = {item.filename for item in result}
        # Should include start, middle, end (boundaries inclusive), exclude before/after
        assert filenames == {"file_start.pdf", "file_middle.pdf", "file_end.pdf"}

    def test_modified_after_no_matches(self, tmp_path: Path) -> None:
        """modifiedAfter with no matches returns empty list."""
        old_time = dt.datetime(2024, 1, 1, 0, 0, 0, tzinfo=dt.timezone.utc)
        future_time = dt.datetime(2099, 1, 1, 0, 0, 0, tzinfo=dt.timezone.utc)

        file1 = tmp_path / "file1.pdf"
        file1.write_text("a")
        os.utime(file1, (old_time.timestamp(), old_time.timestamp()))

        result = search_files(tmp_path, modified_after=future_time)

        assert result == []

    def test_modified_before_no_matches(self, tmp_path: Path) -> None:
        """modifiedBefore with no matches returns empty list."""
        future_time = dt.datetime(2099, 1, 1, 0, 0, 0, tzinfo=dt.timezone.utc)
        past_time = dt.datetime(1990, 1, 1, 0, 0, 0, tzinfo=dt.timezone.utc)

        file1 = tmp_path / "file1.pdf"
        file1.write_text("a")
        os.utime(file1, (future_time.timestamp(), future_time.timestamp()))

        result = search_files(tmp_path, modified_before=past_time)

        assert result == []


class TestSearchFilesFiltersAndLogic:
    """Scenario: Filtreler AND mantığıyla birleşir."""

    def test_name_contains_and_extension(self, tmp_path: Path) -> None:
        """name_contains and extension filters combine with AND logic."""
        (tmp_path / "fatura_2024.pdf").write_text("a")
        (tmp_path / "fatura_2024.docx").write_text("b")
        (tmp_path / "invoice.pdf").write_text("c")

        result = search_files(tmp_path, name_contains="fatura", extension="pdf")

        filenames = {item.filename for item in result}
        assert filenames == {"fatura_2024.pdf"}

    def test_name_contains_and_modified_after(self, tmp_path: Path) -> None:
        """name_contains and modified_after filters combine with AND logic."""
        base_time = dt.datetime(2024, 1, 15, 0, 0, 0, tzinfo=dt.timezone.utc)
        before_time = dt.datetime(2024, 1, 10, 0, 0, 0, tzinfo=dt.timezone.utc)

        file1 = tmp_path / "fatura_old.pdf"
        file1.write_text("a")
        os.utime(file1, (before_time.timestamp(), before_time.timestamp()))

        file2 = tmp_path / "fatura_new.pdf"
        file2.write_text("b")
        os.utime(file2, (base_time.timestamp(), base_time.timestamp()))

        file3 = tmp_path / "invoice.pdf"
        file3.write_text("c")
        os.utime(file3, (base_time.timestamp(), base_time.timestamp()))

        result = search_files(tmp_path, name_contains="fatura", modified_after=base_time)

        filenames = {item.filename for item in result}
        assert filenames == {"fatura_new.pdf"}

    def test_all_filters_together(self, tmp_path: Path) -> None:
        """All filters together combine with AND logic."""
        base_time = dt.datetime(2024, 1, 15, 0, 0, 0, tzinfo=dt.timezone.utc)
        before_time = dt.datetime(2024, 1, 10, 0, 0, 0, tzinfo=dt.timezone.utc)
        after_time = dt.datetime(2024, 1, 20, 0, 0, 0, tzinfo=dt.timezone.utc)

        # Matches name and extension, wrong date
        file1 = tmp_path / "fatura_2024.pdf"
        file1.write_text("a")
        os.utime(file1, (before_time.timestamp(), before_time.timestamp()))

        # Matches name and date, wrong extension
        file2 = tmp_path / "fatura_2024.docx"
        file2.write_text("b")
        os.utime(file2, (base_time.timestamp(), base_time.timestamp()))

        # Matches all filters
        file3 = tmp_path / "fatura_new.pdf"
        file3.write_text("c")
        os.utime(file3, (base_time.timestamp(), base_time.timestamp()))

        # Matches extension and date, wrong name
        file4 = tmp_path / "invoice.pdf"
        file4.write_text("d")
        os.utime(file4, (after_time.timestamp(), after_time.timestamp()))

        result = search_files(
            tmp_path,
            name_contains="fatura",
            extension="pdf",
            modified_after=base_time,
            modified_before=after_time,
        )

        filenames = {item.filename for item in result}
        assert filenames == {"fatura_new.pdf"}


class TestSearchFilesNonExistentFolder:
    """Scenario: Klasör artık yok → boş liste döner."""

    def test_nonexistent_folder_returns_empty_list(self) -> None:
        """Non-existent folder returns empty list (does not raise)."""
        nonexistent = Path("/nonexistent/folder/that/does/not/exist")
        result = search_files(nonexistent)

        assert result == []

    def test_file_instead_of_folder_returns_empty_list(self, tmp_path: Path) -> None:
        """If path points to a file instead of folder, returns empty list."""
        file_path = tmp_path / "notafolder.txt"
        file_path.write_text("content")

        result = search_files(file_path)

        assert result == []


class TestSearchFilesResultType:
    """Result items must have only: filename, extension, modifiedAt, sizeBytes."""

    def test_result_item_has_correct_fields(self, tmp_path: Path) -> None:
        """Result items have exactly: filename, extension, modifiedAt, sizeBytes."""
        (tmp_path / "test.pdf").write_text("content")

        result = search_files(tmp_path)

        assert len(result) == 1
        item = result[0]

        # Check it's a SearchResultItem
        assert isinstance(item, SearchResultItem)

        # Check all required fields exist
        assert hasattr(item, "filename")
        assert hasattr(item, "extension")
        assert hasattr(item, "modifiedAt")
        assert hasattr(item, "sizeBytes")

        # Check no path-related fields exist
        assert not hasattr(item, "path")
        assert not hasattr(item, "full_path")
        assert not hasattr(item, "absolute_path")

    def test_filename_is_basename_only(self, tmp_path: Path) -> None:
        """Result filename is basename only, no path separators."""
        (tmp_path / "myfile.pdf").write_text("content")

        result = search_files(tmp_path)

        assert result[0].filename == "myfile.pdf"
        # Should not contain any path separators
        assert "/" not in result[0].filename
        assert "\\" not in result[0].filename

    def test_extension_field_present(self, tmp_path: Path) -> None:
        """Result extension field is present and correct."""
        (tmp_path / "document.pdf").write_text("content")
        (tmp_path / "report.xlsx").write_text("content")

        result = search_files(tmp_path)

        extensions = {item.extension for item in result}
        assert ".pdf" in extensions
        assert ".xlsx" in extensions

    def test_modified_at_iso8601_format(self, tmp_path: Path) -> None:
        """Result modifiedAt is ISO 8601 formatted string."""
        base_time = dt.datetime(2024, 1, 15, 12, 30, 45, tzinfo=dt.timezone.utc)
        file1 = tmp_path / "file.pdf"
        file1.write_text("content")
        os.utime(file1, (base_time.timestamp(), base_time.timestamp()))

        result = search_files(tmp_path)

        assert len(result) == 1
        assert result[0].modifiedAt == base_time.isoformat()

    def test_size_bytes_present_and_correct(self, tmp_path: Path) -> None:
        """Result sizeBytes field is present and correct."""
        file1 = tmp_path / "file.txt"
        content = "hello world"
        file1.write_text(content)

        result = search_files(tmp_path)

        assert len(result) == 1
        assert result[0].sizeBytes == len(content.encode("utf-8"))

    def test_size_bytes_large_file(self, tmp_path: Path) -> None:
        """sizeBytes correctly handles larger files."""
        file1 = tmp_path / "largefile.bin"
        # Write 1MB of data
        data = b"x" * (1024 * 1024)
        file1.write_bytes(data)

        result = search_files(tmp_path)

        assert len(result) == 1
        assert result[0].sizeBytes == 1024 * 1024


class TestSearchFilesEdgeCases:
    """Edge cases and corner scenarios."""

    def test_special_characters_in_filename(self, tmp_path: Path) -> None:
        """Files with special characters in name are handled correctly."""
        (tmp_path / "file-2024_01-15.pdf").write_text("a")
        (tmp_path / "report (final).xlsx").write_text("b")
        (tmp_path / "data-2024-01-15.txt").write_text("c")

        result = search_files(tmp_path)

        assert len(result) == 3
        filenames = {item.filename for item in result}
        assert "file-2024_01-15.pdf" in filenames

    def test_file_with_multiple_dots(self, tmp_path: Path) -> None:
        """Files with multiple dots (e.g., 'archive.tar.gz') are handled."""
        (tmp_path / "archive.tar.gz").write_text("a")
        (tmp_path / "backup.2024.01.15.zip").write_text("b")

        result = search_files(tmp_path)

        assert len(result) == 2
        # Extension should be the last part
        ext_map = {item.filename: item.extension for item in result}
        assert ext_map["archive.tar.gz"] == ".gz"
        assert ext_map["backup.2024.01.15.zip"] == ".zip"

    def test_file_with_no_extension(self, tmp_path: Path) -> None:
        """Files with no extension are handled correctly."""
        (tmp_path / "README").write_text("a")
        (tmp_path / "LICENSE").write_text("b")
        (tmp_path / "Makefile").write_text("c")

        result = search_files(tmp_path)

        assert len(result) == 3
        # Files with no extension should have empty string or appropriate value
        ext_map = {item.filename: item.extension for item in result}
        for filename, ext in ext_map.items():
            # Should be consistent (empty string or similar)
            assert ext is not None

    def test_unicode_filename(self, tmp_path: Path) -> None:
        """Files with unicode characters in name are handled."""
        (tmp_path / "Fatura_2024_Türkiye.pdf").write_text("a")
        (tmp_path / "файл.txt").write_text("b")

        result = search_files(tmp_path)

        assert len(result) == 2

    def test_name_contains_with_unicode(self, tmp_path: Path) -> None:
        """name_contains filter works with unicode characters."""
        (tmp_path / "Fatura_2024_Türkiye.pdf").write_text("a")
        (tmp_path / "Invoice_2024.pdf").write_text("b")

        result = search_files(tmp_path, name_contains="Türkiye")

        filenames = {item.filename for item in result}
        assert filenames == {"Fatura_2024_Türkiye.pdf"}

    def test_very_long_filename(self, tmp_path: Path) -> None:
        """Very long filenames are handled correctly."""
        long_name = "a" * 200 + ".pdf"
        (tmp_path / long_name).write_text("content")

        result = search_files(tmp_path)

        assert len(result) == 1
        assert result[0].filename == long_name

    def test_whitespace_only_filename_behavior(self, tmp_path: Path) -> None:
        """Whitespace-only filenames or patterns are handled."""
        # Most filesystems won't allow files with only spaces, but test search behavior
        (tmp_path / "normal.pdf").write_text("a")

        result = search_files(tmp_path, name_contains="   ")

        # Should match any file (substring of "" in every filename)
        # OR should match nothing depending on implementation
        # Either behavior is valid, as long as consistent
        assert isinstance(result, list)

    def test_results_do_not_expose_absolute_path(self, tmp_path: Path) -> None:
        """Result items never expose absolute path (Saga #283 principle)."""
        (tmp_path / "sensitive.pdf").write_text("content")

        result = search_files(tmp_path)

        assert len(result) == 1
        item = result[0]

        # filename should NOT contain the temp path
        assert str(tmp_path) not in item.filename
        # modifiedAt is ISO string, shouldn't contain path
        assert "/" not in item.modifiedAt or "T" in item.modifiedAt  # ISO format check


# --- Saga #314: dosya-icerik-arama-encoding-timeout (RED STEP) ---
# Asagidaki testler `search_files()`in henuz VAR OLMAYAN `content_contains`
# parametresini kullanir. Bu testlerin su an TypeError (beklenmeyen keyword
# argument) ile KIRMIZI olmasi BEKLENEN ve DOGRU davranistir (atdd.md AC-1..9).


class TestSearchFilesContentContainsEncoding:
    """AC-1 [Critical]: utf-8/latin-1/cp1254 encoding'lerinde content_contains
    eslesmesi dogru bulunmali."""

    def test_content_contains_matches_utf8_file(self, tmp_path: Path) -> None:
        file1 = tmp_path / "utf8_fatura.txt"
        file1.write_text("fatura no 12345 - odendi", encoding="utf-8")

        result = search_files(tmp_path, content_contains="fatura no 12345")

        filenames = {item.filename for item in result}
        assert filenames == {"utf8_fatura.txt"}

    def test_content_contains_matches_latin1_file(self, tmp_path: Path) -> None:
        # "ödenmiş" içindeki "ş" latin-1 (ISO-8859-1) ile temsil edilemez —
        # bu yüzden latin-1 dalını gerçekten kapsayan, latin-1'in
        # kodlayabildiği Batı Avrupa karakterli bir örnek kullanılıyor.
        file1 = tmp_path / "latin1_fatura.txt"
        file1.write_bytes("fatura no 12345 - café résumé".encode("latin-1"))

        result = search_files(tmp_path, content_contains="fatura no 12345")

        filenames = {item.filename for item in result}
        assert filenames == {"latin1_fatura.txt"}

    def test_content_contains_matches_cp1254_file(self, tmp_path: Path) -> None:
        file1 = tmp_path / "cp1254_fatura.txt"
        file1.write_bytes("fatura no 12345 - şirket ödemesi".encode("cp1254"))

        result = search_files(tmp_path, content_contains="fatura no 12345")

        filenames = {item.filename for item in result}
        assert filenames == {"cp1254_fatura.txt"}

    def test_content_contains_all_three_encodings_together(self, tmp_path: Path) -> None:
        (tmp_path / "a_utf8.txt").write_text(
            "fatura no 12345 kaydı", encoding="utf-8"
        )
        (tmp_path / "b_latin1.txt").write_bytes(
            "fatura no 12345 kaydi".encode("latin-1")
        )
        (tmp_path / "c_cp1254.txt").write_bytes(
            "fatura no 12345 şirket".encode("cp1254")
        )
        (tmp_path / "d_nomatch.txt").write_text("alakasiz icerik", encoding="utf-8")

        result = search_files(tmp_path, content_contains="fatura no 12345")

        filenames = {item.filename for item in result}
        assert filenames == {"a_utf8.txt", "b_latin1.txt", "c_cp1254.txt"}

    def test_content_contains_no_match_returns_empty_list(self, tmp_path: Path) -> None:
        """Davranis Sozlesmesi satir 8: hicbir sey bulunamadi ama hata yok."""
        (tmp_path / "file1.txt").write_text("baska bir icerik", encoding="utf-8")

        result = search_files(tmp_path, content_contains="fatura no 12345")

        assert result == []

    def test_content_contains_case_insensitive(self, tmp_path: Path) -> None:
        (tmp_path / "file1.txt").write_text("FATURA NO 12345", encoding="utf-8")

        result = search_files(tmp_path, content_contains="fatura no 12345")

        filenames = {item.filename for item in result}
        assert filenames == {"file1.txt"}


class TestSearchFilesContentContainsSkipsUnreadable:
    """AC-3 [High]: binary/10MB+ dosyalar sessizce atlanir, hata firlamaz.
    AC-5 [Medium]: okuma izni olmayan dosya atlanir, arama devam eder."""

    def test_binary_file_is_skipped_without_error(self, tmp_path: Path) -> None:
        binary_file = tmp_path / "app.exe"
        binary_file.write_bytes(bytes(range(256)) * 4)
        text_file = tmp_path / "notes.txt"
        text_file.write_text("fatura no 12345", encoding="utf-8")

        result = search_files(tmp_path, content_contains="fatura no 12345")

        filenames = {item.filename for item in result}
        assert filenames == {"notes.txt"}
        assert "app.exe" not in filenames

    def test_large_file_over_10mb_is_skipped(self, tmp_path: Path) -> None:
        big_file = tmp_path / "big.txt"
        # 10MB + biraz fazlası, içeriğinde arama metni geçse bile atlanmalı
        content = ("fatura no 12345 " + "x" * 1024).encode("utf-8")
        repeat = (10 * 1024 * 1024 // len(content)) + 2
        big_file.write_bytes(content * repeat)
        small_file = tmp_path / "small.txt"
        small_file.write_text("fatura no 12345", encoding="utf-8")

        result = search_files(tmp_path, content_contains="fatura no 12345")

        filenames = {item.filename for item in result}
        assert filenames == {"small.txt"}
        assert "big.txt" not in filenames

    @pytest.mark.skipif(
        os.name == "nt",
        reason=(
            "Windows NTFS'te os.chmod(path, 0o000) dosya sahibinin okuma "
            "erişimini POSIX gibi engellemiyor; bu yüzden Windows'ta atlanır "
            "(Unix'te çalışır)."
        ),
    )
    def test_permission_denied_file_is_skipped(self, tmp_path: Path) -> None:
        readable = tmp_path / "readable.txt"
        readable.write_text("fatura no 12345", encoding="utf-8")
        denied = tmp_path / "denied.txt"
        denied.write_text("fatura no 12345", encoding="utf-8")

        try:
            os.chmod(denied, 0o000)
            result = search_files(tmp_path, content_contains="fatura no 12345")
        finally:
            # Cleanup sırasında tmp_path silinebilmesi için izinleri geri ver
            os.chmod(denied, 0o644)

        filenames = {item.filename for item in result}
        assert "readable.txt" in filenames
        assert "denied.txt" not in filenames


class TestSearchFilesContentContainsTimeout:
    """AC-2 [Critical]: arama 10 saniyeyi asarsa partial=True ile (kısmi
    sonuçlar) kesilir, hata firlamaz. `search_files` şu an partial bilgisini
    döndürecek bir mekanizmaya sahip değil (ne dönüş tipi ne de parametre) —
    bu test hem timeout mantığının hem de partial sinyalinin (fonksiyon
    imzasında/dönüş değerinde) VAR OLMASINI bekler."""

    def test_search_times_out_and_returns_partial_flag(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        for i in range(50):
            (tmp_path / f"file_{i}.txt").write_text(
                "fatura no 12345", encoding="utf-8"
            )

        import time as time_module

        real_monotonic = time_module.monotonic
        call_count = {"n": 0}

        def fake_monotonic():
            # İlk çağrıdan sonra zamanı 11 saniye ileri attır, bu yüzden
            # global 10sn timeout hemen tetiklenir.
            call_count["n"] += 1
            if call_count["n"] <= 1:
                return real_monotonic()
            return real_monotonic() + 11

        monkeypatch.setattr(time_module, "monotonic", fake_monotonic)

        result, partial = search_files(
            tmp_path, content_contains="fatura no 12345", return_partial=True
        )

        assert partial is True
        assert isinstance(result, list)


class TestSearchFilesContentContainsAndOtherFilters:
    """AC-6 [Medium]: content_contains diger filtrelerle AND mantigiyla
    birlesir."""

    def test_content_contains_and_extension_and_name_contains(
        self, tmp_path: Path
    ) -> None:
        (tmp_path / "fatura_2024.pdf").write_bytes(
            "fatura no 12345".encode("utf-8")
        )
        (tmp_path / "fatura_2024.txt").write_text(
            "fatura no 12345", encoding="utf-8"
        )
        (tmp_path / "invoice.pdf").write_bytes("fatura no 12345".encode("utf-8"))
        (tmp_path / "fatura_2024_nomatch.pdf").write_bytes(
            "alakasiz".encode("utf-8")
        )

        result = search_files(
            tmp_path,
            name_contains="fatura",
            extension="pdf",
            content_contains="fatura no 12345",
        )

        filenames = {item.filename for item in result}
        assert filenames == {"fatura_2024.pdf"}


class TestSearchFilesContentContainsNowRecursive:
    """Saga #336 (dosya-arama-recursive) atdd.md AC-4: content_contains ARTIK
    recursive çalışır (Saga #314'teki eski non-recursive davranışın AKSİNE —
    bu test eskiden "nested.txt sonuca girmez" bekliyordu; AC-1 ile tutarlı
    olması için GÜNCELLENDİ: artık girmesi GEREKİYOR)."""

    def test_subfolder_file_content_is_matched(self, tmp_path: Path) -> None:
        (tmp_path / "top_level.txt").write_text(
            "fatura no 12345", encoding="utf-8"
        )
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "nested.txt").write_text("fatura no 12345", encoding="utf-8")

        result = search_files(tmp_path, content_contains="fatura no 12345")

        filenames = {item.filename for item in result}
        assert filenames == {"top_level.txt", "nested.txt"}


class TestSearchFilesContentContainsSymlinkEscape:
    """AC-8 [High] (threat-model): allowed_root disina isaret eden bir
    symlink icerigi taranmaz/sonuca girmez."""

    @pytest.mark.skipif(
        os.name == "nt",
        reason=(
            "Windows'ta os.symlink() admin/developer-mode yetkisi gerektirir; "
            "CI/geliştirme ortamında bu yetki garanti değil, bu yüzden "
            "Windows'ta atlanır (Unix'te çalışır)."
        ),
    )
    def test_symlink_pointing_outside_allowed_root_is_not_searched(
        self, tmp_path: Path
    ) -> None:
        allowed_root = tmp_path / "allowed_root"
        allowed_root.mkdir()
        outside_dir = tmp_path / "outside"
        outside_dir.mkdir()

        secret_file = outside_dir / "secret.txt"
        secret_file.write_text("fatura no 12345 GİZLİ", encoding="utf-8")

        symlink_path = allowed_root / "escape_link.txt"
        os.symlink(secret_file, symlink_path)

        # allowed_root icinde normal, esleşen bir dosya da olsun
        (allowed_root / "normal.txt").write_text(
            "fatura no 12345", encoding="utf-8"
        )

        result = search_files(allowed_root, content_contains="fatura no 12345")

        filenames = {item.filename for item in result}
        assert "escape_link.txt" not in filenames
        assert "normal.txt" in filenames


# --- Saga #336: dosya-arama-recursive (RED STEP) ---
# `search_files()` su an SADECE `folder.iterdir()` ile `folder`'in DOGRUDAN
# altini tarar (Saga #313/#314, non-recursive). Asagidaki testler
# artifacts/dosya-arama-recursive/atdd.md AC-1..7'yi dogrular ve implementasyon
# HENUZ YAPILMADIGI icin KIRMIZI olmalari BEKLENEN/DOGRU davranistir.
# Derinlik sayimi: allowed_root'un DOGRUDAN altini derinlik 1 sayar (atdd.md
# Assumptions), yani `allowed_root/a/b/dosya.pdf` derinlik 2'dir.
# security.py::MAX_PATH_DEPTH = 3 DEGERI referans alinir (BAGIMSIZ sabit,
# security.py'ye dokunulmuyor - bkz. plan.md Risks).


class TestSearchFilesRecursiveDiscovery:
    """AC-1 [Critical]: coklu seviyeli klasor yapisinda alt klasordeki
    dosyalar da sonuca girmeli."""

    def test_file_two_levels_deep_is_found(self, tmp_path: Path) -> None:
        nested = tmp_path / "a" / "b"
        nested.mkdir(parents=True)
        (nested / "dosya.pdf").write_bytes(b"%PDF-1.4 fake")
        (tmp_path / "top_level.pdf").write_bytes(b"%PDF-1.4 fake")

        result = search_files(tmp_path)

        filenames = {item.filename for item in result}
        assert "dosya.pdf" in filenames
        assert "top_level.pdf" in filenames

    def test_file_two_levels_deep_is_found_with_name_filter(
        self, tmp_path: Path
    ) -> None:
        nested = tmp_path / "2024" / "Q1"
        nested.mkdir(parents=True)
        (nested / "fatura_ocak.pdf").write_bytes(b"%PDF-1.4 fake")

        result = search_files(tmp_path, name_contains="fatura")

        filenames = {item.filename for item in result}
        assert filenames == {"fatura_ocak.pdf"}


class TestSearchFilesDepthLimit:
    """AC-2 [Critical]: security.py::MAX_PATH_DEPTH (3) asan dosyalar
    sessizce sonuc disi birakilir, hata firlamaz."""

    def test_file_beyond_max_depth_is_excluded_without_error(
        self, tmp_path: Path
    ) -> None:
        # allowed_root/a/b/c/dosya.pdf -> derinlik 4, MAX_PATH_DEPTH=3'u asiyor.
        too_deep = tmp_path / "a" / "b" / "c"
        too_deep.mkdir(parents=True)
        (too_deep / "too_deep.pdf").write_bytes(b"%PDF-1.4 fake")

        # allowed_root/a/b/dosya.pdf -> derinlik 3, sinir icinde, gorunmeli.
        within_limit = tmp_path / "a" / "b"
        (within_limit / "within_limit.pdf").write_bytes(b"%PDF-1.4 fake")

        result = search_files(tmp_path)

        filenames = {item.filename for item in result}
        assert "too_deep.pdf" not in filenames
        assert "within_limit.pdf" in filenames


class TestSearchFilesCycleProtection:
    """AC-3 [Critical]: dongusel bir yapiya (gercek symlink olsun ya da
    olmasin) girildiginde sonsuz donguye GIRILMEZ - ziyaret edilen resolved
    path'ler bir sette tutulur, tekrar gorulen dizin atlanir."""

    def test_visited_path_tracking_prevents_infinite_loop_without_real_symlink(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """plan.md Risks notu: AC-3'un CEKIRDEK mantigi (ziyaret edilen
        resolved-path seti) gercek symlink KULLANMADAN, `Path.resolve()`
        sahte bir dongu uretecek sekilde monkeypatch'lenerek test edilir -
        boylece Windows'ta da (symlink admin yetkisi gerekmeden) gercekten
        dogrulanir. `A/loop_back` gercekte AYRI bir klasordur, ama
        `.resolve()`'i KASITLI olarak `A`nin resolved path'iyle AYNI deger
        donecek sekilde sahtelenir - tipki `A/link -> A` gercek dongusel
        symlink'inin davranacagi gibi."""
        root_a = tmp_path / "A"
        root_a.mkdir()
        (root_a / "file_in_a.txt").write_text("icerik", encoding="utf-8")

        loop_back = root_a / "loop_back"
        loop_back.mkdir()
        # loop_back'in altina da bir dosya koyalim - eger dongu korumasi
        # calismiyorsa buraya asla inilmeyecek zaten (resolve sahteligi
        # yuzunden "zaten ziyaret edildi" sayilmasi gerekiyor), calisiyorsa
        # bu dosya higbir zaman ikinci kez "A" olarak taranmayacak.
        (loop_back / "should_not_cause_recursion.txt").write_text(
            "icerik", encoding="utf-8"
        )

        resolved_a = root_a.resolve()
        original_resolve = Path.resolve

        def fake_resolve(self: Path, *args, **kwargs):
            if self == loop_back:
                return resolved_a
            return original_resolve(self, *args, **kwargs)

        monkeypatch.setattr(Path, "resolve", fake_resolve)

        # Bu cagri sonsuz donguye girerse test hicbir zaman bitmez (pytest
        # kendi global suresinde takilir) - testin TAMAMLANMASININ KENDISI
        # dongu korumasinin calistiginin kaniti (atdd.md Benchmark notu).
        result = search_files(tmp_path)

        filenames = {item.filename for item in result}
        assert "file_in_a.txt" in filenames

    @pytest.mark.skipif(
        os.name == "nt",
        reason=(
            "Windows'ta os.symlink() admin/developer-mode yetkisi gerektirir; "
            "CI/gelistirme ortaminda bu yetki garanti degil, bu yuzden "
            "Windows'ta atlanir (Unix'te calisir)."
        ),
    )
    def test_real_cyclic_symlink_completes_without_hanging(
        self, tmp_path: Path
    ) -> None:
        """A klasoru altinda A'ya geri donen gercek bir dongusel symlink
        (A/link -> A). Aramanin sonsuz donguye girmeden, makul surede
        TAMAMLANMASI tek basina en kritik kanittir (atdd.md Benchmark)."""
        root_a = tmp_path / "A"
        root_a.mkdir()
        (root_a / "normal.txt").write_text("icerik", encoding="utf-8")

        cyclic_link = root_a / "link"
        os.symlink(root_a, cyclic_link, target_is_directory=True)

        result = search_files(tmp_path)

        filenames = {item.filename for item in result}
        assert "normal.txt" in filenames


class TestSearchFilesContentContainsRecursive:
    """AC-4 [High]: content_contains da recursive calisir, AC-1 ile ayni
    derinlik/dongu kurallarina tabidir."""

    def test_content_search_finds_match_in_nested_folder(
        self, tmp_path: Path
    ) -> None:
        # Derinlik 3 (tmp_path/2024/Ocak/fatura.txt) - security.py::MAX_PATH_DEPTH
        # (=3) sinirinin TAM ICINDE kalir; derinlik 4 (2024/Q1/Ocak/fatura.txt)
        # AC-2 tarafindan zaten hariç tutulur, bu test onunla celismemeli.
        nested = tmp_path / "2024" / "Ocak"
        nested.mkdir(parents=True)
        (nested / "fatura.txt").write_text(
            "fatura no 98765 - odendi", encoding="utf-8"
        )
        (tmp_path / "top_level.txt").write_text(
            "alakasiz icerik", encoding="utf-8"
        )

        result = search_files(tmp_path, content_contains="fatura no 98765")

        filenames = {item.filename for item in result}
        assert filenames == {"fatura.txt"}


class TestSearchFilesRecursiveTimeout:
    """AC-5 [High]: recursive baglamda da 10sn timeout uygulanir, o ana
    kadarki sonuclarla partial=True doner (Saga #314 timeout deseniyle
    tutarli)."""

    def test_recursive_search_times_out_and_returns_partial_flag(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        for level in range(3):
            level_dir = tmp_path / f"level_{level}"
            level_dir.mkdir()
            for i in range(10):
                (level_dir / f"file_{i}.txt").write_text(
                    "fatura no 12345", encoding="utf-8"
                )

        import time as time_module

        real_monotonic = time_module.monotonic
        call_count = {"n": 0}

        def fake_monotonic():
            call_count["n"] += 1
            if call_count["n"] <= 1:
                return real_monotonic()
            return real_monotonic() + 11

        monkeypatch.setattr(time_module, "monotonic", fake_monotonic)

        result, partial = search_files(
            tmp_path, content_contains="fatura no 12345", return_partial=True
        )

        assert partial is True
        assert isinstance(result, list)


class TestSearchFilesDiscoveryTimeoutWithoutContentContains:
    """Red-team follow-up (Saga #336, medium): `content_contains` VERİLMEDEN
    (sadece name_contains gibi bir filtreyle) gezinmenin KENDİSİ 10sn'yi
    aşarsa `partial=True` dönmeli - eskiden bu durumda hiçbir zaman bütçesi
    yoktu."""

    def test_discovery_times_out_without_content_contains_and_returns_partial(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        for level in range(3):
            level_dir = tmp_path / f"level_{level}"
            level_dir.mkdir()
            for i in range(10):
                (level_dir / f"file_{i}.txt").write_text(
                    "icerik", encoding="utf-8"
                )

        import time as time_module

        real_monotonic = time_module.monotonic
        call_count = {"n": 0}

        def fake_monotonic():
            # İlk çağrıdan sonra zamanı 11 saniye ileri attır, bu yüzden
            # discovery (gezinme) icin de global 10sn timeout hemen
            # tetiklenir - content_contains hic verilmiyor.
            call_count["n"] += 1
            if call_count["n"] <= 1:
                return real_monotonic()
            return real_monotonic() + 11

        monkeypatch.setattr(time_module, "monotonic", fake_monotonic)

        result, partial = search_files(
            tmp_path, name_contains="file", return_partial=True
        )

        assert partial is True
        assert isinstance(result, list)


class TestSearchFilesRecursiveSymlinkEscape:
    """AC-6 [Medium]: allowed_root disina isaret eden bir symlink, alt
    klasorde (recursive derinlikte) olsa bile dislanir (Saga #314 AC-8'in
    recursive baglamda da gecerliligi)."""

    @pytest.mark.skipif(
        os.name == "nt",
        reason=(
            "Windows'ta os.symlink() admin/developer-mode yetkisi gerektirir; "
            "CI/gelistirme ortaminda bu yetki garanti degil, bu yuzden "
            "Windows'ta atlanir (Unix'te calisir)."
        ),
    )
    def test_nested_symlink_pointing_outside_allowed_root_is_excluded(
        self, tmp_path: Path
    ) -> None:
        allowed_root = tmp_path / "allowed_root"
        nested = allowed_root / "a" / "b"
        nested.mkdir(parents=True)
        outside_dir = tmp_path / "outside"
        outside_dir.mkdir()

        secret_file = outside_dir / "secret.txt"
        secret_file.write_text("fatura no 12345 GIZLI", encoding="utf-8")

        symlink_path = nested / "escape_link.txt"
        os.symlink(secret_file, symlink_path)

        (nested / "normal.txt").write_text("fatura no 12345", encoding="utf-8")

        result = search_files(allowed_root, content_contains="fatura no 12345")

        filenames = {item.filename for item in result}
        assert "escape_link.txt" not in filenames
        assert "normal.txt" in filenames


class TestSearchFilesHiddenFolderNotDescended:
    """AC-7 [Medium]: gizli (nokta ile baslayan) bir alt klasorun ALTINA
    hic inilmez - mevcut gizli-DOSYA-atlama kuralinin klasorlere de
    genisletilmesi."""

    def test_files_under_hidden_subfolder_are_never_scanned(
        self, tmp_path: Path
    ) -> None:
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "config").write_text("gizli git config", encoding="utf-8")
        nested_in_git = git_dir / "objects"
        nested_in_git.mkdir()
        (nested_in_git / "deep_file.txt").write_text("icerik", encoding="utf-8")

        (tmp_path / "visible.txt").write_text("icerik", encoding="utf-8")

        result = search_files(tmp_path)

        filenames = {item.filename for item in result}
        assert filenames == {"visible.txt"}
        assert "config" not in filenames
        assert "deep_file.txt" not in filenames
