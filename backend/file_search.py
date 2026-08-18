import datetime as dt
from pathlib import Path

from backend.models import SearchResultItem


def search_files(
    folder: Path,
    *,
    name_contains: str | None = None,
    extension: str | None = None,
    modified_after: dt.datetime | None = None,
    modified_before: dt.datetime | None = None,
) -> list[SearchResultItem]:
    """`folder`ın DOĞRUDAN altındaki (alt klasörler dahil edilmez) dosyaları
    filtreler. `discover_pdf_files` ile aynı stil: gizli (nokta ile başlayan)
    dosyalar HER ZAMAN atlanır, non-recursive, non-existent klasör boş liste
    döner.

    Filtreler AND mantığıyla birleşir:
    - `name_contains`: filename içinde case-insensitive düz substring match
    - `extension`: case-insensitive, "pdf" veya ".pdf" formlarını kabul eder
    - `modified_after`/`modified_before`: dosya mtime'ına göre dahil aralık
      (>= ve <=)

    Sonuçlar filename'e göre sıralanır ve `SearchResultItem` listesi döner.
    Hiçbiri verilmezse klasördeki TÜM görünür dosyalar döner."""

    if not folder.is_dir():
        return []

    # Tüm dosyaları topla (gizli dosyalar hariç)
    files = [
        entry
        for entry in folder.iterdir()
        if entry.is_file() and not entry.name.startswith(".")
    ]

    # Filtreleri uygula
    filtered_files = []

    for entry in files:
        # name_contains filter
        if name_contains is not None:
            if name_contains.lower() not in entry.name.lower():
                continue

        # extension filter
        if extension is not None:
            # Normalize extension: ensure it starts with "."
            normalized_filter_ext = (
                extension if extension.startswith(".") else f".{extension}"
            )
            # Get file extension (always includes the dot)
            file_ext = entry.suffix
            # Compare case-insensitive
            if file_ext.lower() != normalized_filter_ext.lower():
                continue

        # modified_after filter (inclusive >=)
        if modified_after is not None:
            file_mtime = dt.datetime.fromtimestamp(
                entry.stat().st_mtime, tz=dt.timezone.utc
            )
            if file_mtime < modified_after:
                continue

        # modified_before filter (inclusive <=)
        if modified_before is not None:
            file_mtime = dt.datetime.fromtimestamp(
                entry.stat().st_mtime, tz=dt.timezone.utc
            )
            if file_mtime > modified_before:
                continue

        # All filters passed, add to results
        filtered_files.append(entry)

    # Sort by filename and create SearchResultItem objects
    sorted_files = sorted(filtered_files, key=lambda entry: entry.name)

    result = []
    for entry in sorted_files:
        stat_info = entry.stat()
        file_mtime = dt.datetime.fromtimestamp(
            stat_info.st_mtime, tz=dt.timezone.utc
        )

        item = SearchResultItem(
            filename=entry.name,
            extension=entry.suffix,  # This already includes the dot
            modifiedAt=file_mtime.isoformat(),
            sizeBytes=stat_info.st_size,
        )
        result.append(item)

    return result
