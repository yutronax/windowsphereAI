import datetime as dt
import time
from pathlib import Path

from backend.models import SearchResultItem

# AC-1: encoding fallback sirasi. latin-1 pratikte HER byte dizisini
# hatasiz decode eder (256 kod noktasinin hepsi tanimli), yani asla
# UnicodeDecodeError firlatmaz - bu yuzden EN SON denenmeli, aksi halde
# cp1254 gerektiren icerik yanlislikla "basarili" latin-1 decode'una
# yakalanip kacirilabilir (bkz. plan.md risk notu).
_CONTENT_ENCODINGS = ("utf-8", "cp1254", "latin-1")

# AC-3: 10MB+ dosyalar content aramasindan atlanir.
_MAX_CONTENT_SEARCH_BYTES = 10 * 1024 * 1024

# AC-2: global tarama timeout'u.
_CONTENT_SEARCH_TIMEOUT_SECONDS = 10.0


def _is_symlink_escaping_root(entry: Path, allowed_root: Path) -> bool:
    """AC-8: `entry` bir symlink ise ve hedefi `allowed_root.resolve()`
    altinda degilse True doner (icerik aramasindan tamamen disla)."""
    if not entry.is_symlink():
        return False
    try:
        resolved_target = entry.resolve()
        resolved_root = allowed_root.resolve()
    except OSError:
        # Kirik symlink / cozulemeyen hedef -> guvenli tarafta kal, disla.
        return True
    try:
        resolved_target.relative_to(resolved_root)
    except ValueError:
        return True
    return False


def _read_file_content_lower(entry: Path) -> str | None:
    """Dosyayi encoding fallback zinciriyle okumaya calisir. Binary
    (null byte iceren) ya da tum encoding'lerde decode edilemeyen
    dosyalar icin None doner (sessizce atla, hata firlatma)."""
    try:
        raw_bytes = entry.read_bytes()
    except (PermissionError, OSError):
        return None

    if b"\x00" in raw_bytes:
        # AC-3: binary dosya tespiti.
        return None

    for encoding in _CONTENT_ENCODINGS:
        try:
            return raw_bytes.decode(encoding).lower()
        except UnicodeDecodeError:
            continue

    return None


def search_files(
    folder: Path,
    *,
    name_contains: str | None = None,
    extension: str | None = None,
    modified_after: dt.datetime | None = None,
    modified_before: dt.datetime | None = None,
    content_contains: str | None = None,
    return_partial: bool = False,
) -> list[SearchResultItem] | tuple[list[SearchResultItem], bool]:
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
    Hiçbiri verilmezse klasördeki TÜM görünür dosyalar döner.

    `content_contains` verilirse (AC-1..9): dosya icerigi utf-8/cp1254/
    latin-1 fallback zinciriyle okunur, case-insensitive substring aranir.
    Binary/10MB+/okunamayan/allowed_root disina isaret eden symlink
    dosyalar sessizce atlanir. Tum tarama 10sn'yi asarsa o ana kadarki
    sonuclarla durur. `return_partial=True` verilirse `(sonuclar, partial)`
    tuple'i doner, aksi halde sadece sonuc listesi doner (geriye donuk
    uyumluluk)."""

    def _finish(items: list[SearchResultItem], partial: bool):
        if return_partial:
            return items, partial
        return items

    if not folder.is_dir():
        return _finish([], False)

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

    # Sort by filename first (content_contains filtresi de bu sirayla
    # taranir, sonuclarin sirali olma garantisini korur).
    sorted_files = sorted(filtered_files, key=lambda entry: entry.name)

    partial = False
    result = []

    start_time = time.monotonic()

    for entry in sorted_files:
        if content_contains is not None:
            if time.monotonic() - start_time > _CONTENT_SEARCH_TIMEOUT_SECONDS:
                partial = True
                break

            # AC-8: symlink allowed_root disina cikiyorsa tamamen disla.
            if _is_symlink_escaping_root(entry, folder):
                continue

            try:
                file_size = entry.stat().st_size
            except (PermissionError, OSError):
                continue

            # AC-3: 10MB+ dosyalar content aramasindan atlanir.
            if file_size > _MAX_CONTENT_SEARCH_BYTES:
                continue

            content_lower = _read_file_content_lower(entry)
            if content_lower is None:
                # Binary / okunamayan / decode edilemeyen dosya -> atla.
                continue

            if content_contains.lower() not in content_lower:
                continue

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

    return _finish(result, partial)
