import datetime as dt
import re
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

# Saga #336 (dosya-arama-recursive) AC-2: allowed_root altinda izin verilen
# azami alt klasor derinligi. DEGER `security.py::MAX_PATH_DEPTH` (=3) ile
# AYNI ama BAGIMSIZ bir sabittir (plan.md karari: security.py'ye dokunulmuyor,
# iki sabit gelecekte birbirinden sapabilir - bilincli trade-off).
_MAX_RECURSIVE_DEPTH = 3


def _iter_files_recursive(root: Path, timed_out: list[bool] | None = None):
    """`root` altini derinlik `_MAX_RECURSIVE_DEPTH`'e kadar recursive
    gezer, gorunur (gizli olmayan) dosyalari verir (yield).

    - Gizli (nokta ile baslayan) klasorlerin ALTINA hic inilmez (AC-7).
    - Gizli dosyalar atlanir (mevcut kural).
    - Ziyaret edilen klasorlerin resolved path'leri bir sette tutulur;
      dongusel bir yapiya (gercek symlink olsun ya da olmasin) tekrar
      girilirse o klasor atlanir (AC-3, plan.md notu).
    - `allowed_root` = `root`, derinlik sayimi `root`'un DOGRUDAN alti
      derinlik 1 sayilir (atdd.md Assumptions).

    Red-team follow-up (Saga #336, medium): gezinmenin KENDISI de
    `_CONTENT_SEARCH_TIMEOUT_SECONDS` ile sinirlidir - `content_contains`
    verilmese bile buyuk/yavas bir dizin agacinda gezinme asilip kalmasin
    diye her dizin ziyaretinden once gecen sure kontrol edilir. Timeout
    asilirsa o ana kadar kesfedilen dosyalarla gezinme durur; `timed_out`
    (caginan tarafindan verilen mutable liste) True olarak isaretlenir ki
    `search_files()` bunu `partial` bayragina yansitabilsin.
    """
    visited: set[Path] = set()

    try:
        root_resolved = root.resolve()
    except OSError:
        return
    visited.add(root_resolved)

    start_time = time.monotonic()

    def _walk(folder: Path, depth: int):
        if timed_out is not None and timed_out[0]:
            return

        if time.monotonic() - start_time > _CONTENT_SEARCH_TIMEOUT_SECONDS:
            if timed_out is not None:
                timed_out[0] = True
            return

        try:
            entries = list(folder.iterdir())
        except (PermissionError, OSError):
            return

        for entry in entries:
            if timed_out is not None and timed_out[0]:
                return

            if entry.name.startswith("."):
                # AC-7: gizli dosya/klasor - atla, altina hic inme.
                continue

            if entry.is_dir():
                if depth >= _MAX_RECURSIVE_DEPTH:
                    # AC-2: derinlik siniri asildi, bu alt klasore inme.
                    continue

                # AC-6: allowed_root disina isaret eden symlink klasorler de
                # dislanir (mevcut _is_symlink_escaping_root kurali her
                # seviyede uygulanmaya devam eder).
                if _is_symlink_escaping_root(entry, root):
                    continue

                try:
                    entry_resolved = entry.resolve()
                except OSError:
                    continue

                if entry_resolved in visited:
                    # AC-3: dongu tespiti - tekrar ziyaret edilen klasoru
                    # atla, sonsuz donguye girme.
                    continue
                visited.add(entry_resolved)

                yield from _walk(entry, depth + 1)
                if timed_out is not None and timed_out[0]:
                    return
            elif entry.is_file():
                yield entry

    yield from _walk(root, 1)


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


def _levenshtein_distance(a: str, b: str) -> int:
    """Klasik dinamik programlama ile Levenshtein (duzenleme) mesafesi.
    stdlib'de hazir bir fonksiyon olmadigi icin ek bagimlilik olmadan
    burada uygulanir (Saga #316, atdd.md AC-1/AC-5)."""
    if a == b:
        return 0
    len_a, len_b = len(a), len(b)
    if len_a == 0:
        return len_b
    if len_b == 0:
        return len_a

    previous_row = list(range(len_b + 1))
    for i, char_a in enumerate(a, start=1):
        current_row = [i] + [0] * len_b
        for j, char_b in enumerate(b, start=1):
            insert_cost = current_row[j - 1] + 1
            delete_cost = previous_row[j] + 1
            substitute_cost = previous_row[j - 1] + (0 if char_a == char_b else 1)
            current_row[j] = min(insert_cost, delete_cost, substitute_cost)
        previous_row = current_row

    return previous_row[len_b]


# Saga #316: fuzzy_name eslesmesi icin esik (Levenshtein mesafesi <=2).
_FUZZY_NAME_MAX_DISTANCE = 2


def search_files(
    folder: Path,
    *,
    name_contains: str | None = None,
    extension: str | None = None,
    modified_after: dt.datetime | None = None,
    modified_before: dt.datetime | None = None,
    content_contains: str | None = None,
    fuzzy_name: str | None = None,
    name_pattern: str | None = None,
    return_partial: bool = False,
) -> list[SearchResultItem] | tuple[list[SearchResultItem], bool]:
    """`folder` altını recursive olarak (derinlik sınırlı `_MAX_RECURSIVE_DEPTH`,
    döngü korumalı) tarar ve dosyaları filtreler. Gizli (nokta ile başlayan)
    dosya/klasörler HER ZAMAN atlanır (klasörlerin altına hiç inilmez),
    non-existent klasör boş liste döner.

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
    sonuclarla durur. Dizin gezinmesinin (discovery, `content_contains`
    verilmese bile) KENDISI de 10sn'yi asarsa ayni sekilde o ana kadar
    kesfedilen dosyalarla durur (red-team follow-up, Saga #336 medium
    bulgusu). `return_partial=True` verilirse `(sonuclar, partial)`
    tuple'i doner (discovery-timeout VEYA content-timeout, ikisinden biri
    olursa partial=True), aksi halde sadece sonuc listesi doner (geriye
    donuk uyumluluk)."""

    def _finish(items: list[SearchResultItem], partial: bool):
        if return_partial:
            return items, partial
        return items

    if not folder.is_dir():
        return _finish([], False)

    # Tüm dosyaları topla (recursive, gizli dosyalar/klasörler hariç,
    # derinlik sınırı ve döngü koruması ile - Saga #336). `discovery_timed_out`
    # gezinmenin (content_contains'ten BAGIMSIZ) kendisinin 10sn'yi asip
    # asmadigini tasir (red-team follow-up, Saga #336 medium bulgusu).
    # AC-7 (Saga #316): fuzzy_name/name_pattern SADECE kok dizini tarar -
    # bilincli non-recursive kapsam karari, #336'nin recursive davranisindan
    # BAGIMSIZ. Red-team follow-up (Saga #316, medium bulgusu): bu durumda
    # `_iter_files_recursive()` HIC CAGRILMAZ - TUM alt agaci derinlik 3'e
    # kadar gezip sonra `entry.parent == folder` ile filtrelemek israfti.
    # Bunun yerine dogrudan `folder.iterdir()` ile SADECE kok dizindeki
    # (gizli olmayan) dosyalar toplanir - discovery-timeout kavrami bu
    # dalda anlamsizdir (sadece 1 dizin taranir), `discovery_timed_out`
    # False kalir.
    discovery_timed_out = [False]
    if fuzzy_name is not None or name_pattern is not None:
        try:
            files = [
                entry
                for entry in folder.iterdir()
                if not entry.name.startswith(".") and entry.is_file()
            ]
        except (PermissionError, OSError):
            files = []
    else:
        files = list(_iter_files_recursive(folder, timed_out=discovery_timed_out))

    # Saga #316 AC-3: gecersiz regex `search_files()` icinde sessizce
    # atlanir (hicbir dosya name_pattern filtresini gecemez) - erken
    # validasyon endpoint (main.py) seviyesinde yapilir.
    compiled_name_pattern: re.Pattern[str] | None = None
    if name_pattern is not None:
        try:
            compiled_name_pattern = re.compile(name_pattern, re.IGNORECASE)
        except re.error:
            compiled_name_pattern = None

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

        # fuzzy_name filter (AC-1/AC-5): entry.stem ile karsilastirilir
        # (entry.name DEGIL - plan.md notu), Levenshtein mesafesi <=2.
        if fuzzy_name is not None:
            distance = _levenshtein_distance(
                entry.stem.lower(), fuzzy_name.lower()
            )
            if distance > _FUZZY_NAME_MAX_DISTANCE:
                continue

        # name_pattern filter (AC-2): regex entry.name'e uygulanir.
        if name_pattern is not None:
            if compiled_name_pattern is None or not compiled_name_pattern.search(
                entry.name
            ):
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

    # Gezinme (discovery) asamasi zaten timeout'a ugradiysa partial=True
    # ile basla - content_contains dongusu bunu ayrica True'ya cekebilir
    # ama asla False'a geri dondurmez (content-timeout'un da mevcut
    # davranisiyla tutarli).
    partial = discovery_timed_out[0]
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
