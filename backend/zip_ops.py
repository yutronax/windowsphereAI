import os
import tempfile
import zipfile
from pathlib import Path

from backend.security import _validate_single_path


def _write_zip_atomically(destination_path: Path, write_entries) -> None:
    """Saga #328 refactor: `create_zip`/`add_to_zip`/`merge_zips`'in
    (üçü de bu dosyada) birebir aynı tempfile+atomik-replace bloğunu
    paylaşan yardımcı. `write_entries(zf)` çağrılıp içeriği doldurur;
    herhangi bir hata durumunda geçici dosya silinir, `destination_path`e
    hiç dokunulmaz."""
    fd, temp_path_str = tempfile.mkstemp(
        suffix=".tmp", prefix=destination_path.name + ".", dir=str(destination_path.parent)
    )
    temp_path = Path(temp_path_str)
    os.close(fd)
    try:
        with zipfile.ZipFile(temp_path, "w") as zf:
            write_entries(zf)
        temp_path.replace(destination_path)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise


def create_zip(source_paths: list[Path], destination_path: Path) -> None:
    """Saga #328 (ATDD AC-1): `source_paths`'i düz yapıda (arcname sadece
    dosya adı, alt-klasör yok) `destination_path`'e zipler. Kaynaklardan
    biri eksikse hiçbir zip yazılmaz."""

    def write_entries(zf: zipfile.ZipFile) -> None:
        for source_path in source_paths:
            zf.write(source_path, arcname=source_path.name)

    _write_zip_atomically(destination_path, write_entries)


def add_to_zip(source_path: Path, files_to_add: list[Path], destination_path: Path) -> None:
    """Saga #328 (ATDD AC-4): kaynak zip'in TÜM eski girişlerini okuyup,
    `files_to_add` ile birlikte YENİ bir zip'e (`destination_path`) yazar.
    Kaynak zip DEĞİŞMEZ (yeni dosyaya yazılıyor)."""
    with zipfile.ZipFile(source_path, "r") as source_zf:
        old_entries = [(info.filename, source_zf.read(info.filename)) for info in source_zf.infolist()]

    def write_entries(zf: zipfile.ZipFile) -> None:
        for name, data in old_entries:
            zf.writestr(name, data)
        for file_path in files_to_add:
            zf.write(file_path, arcname=file_path.name)

    _write_zip_atomically(destination_path, write_entries)


def extract_zip(source_path: Path, destination_folder: Path, allowed_root: Path) -> None:
    """Saga #328 (ATDD AC-2/AC-3/AC-S1): `source_path`'i `destination_folder`'a
    çıkarır. Zip-slip taraması `backend.security._validate_single_path`i
    (mevcut whitelist mekanizması) YENİDEN KULLANIR — yeni bir güvenlik
    algoritması YOK. TÜM girişler gerçek çıkarmadan ÖNCE taranır ("tüm-ya-da-
    hiç"): herhangi biri reddedilirse, HİÇBİR dosya çıkarılmaz."""
    with zipfile.ZipFile(source_path, "r") as zf:
        for entry_name in zf.namelist():
            candidate_path = destination_folder / entry_name
            _validate_single_path(candidate_path, allowed_root, "Zip çıkarma hedefi")
        zf.extractall(destination_folder)


def merge_zips(source_paths: list[Path], destination_path: Path) -> None:
    """Saga #328 (ATDD AC-5): `source_paths`'teki HER zip'in TÜM girişlerini
    okuyup YENİ bir zip'e (`destination_path`) yazar. Kaynaklar DEĞİŞMEZ."""
    all_entries: list[tuple[str, bytes]] = []
    for source_path in source_paths:
        with zipfile.ZipFile(source_path, "r") as source_zf:
            for info in source_zf.infolist():
                all_entries.append((info.filename, source_zf.read(info.filename)))

    def write_entries(zf: zipfile.ZipFile) -> None:
        for name, data in all_entries:
            zf.writestr(name, data)

    _write_zip_atomically(destination_path, write_entries)


def list_zip_entries(source_path: Path) -> list[dict]:
    """Saga #328 (ATDD AC-5b): `source_path`teki zip'in girişlerini
    (ad/boyut/sıkıştırılmış boyut) döner. Salt okunur, hiçbir yazma yok."""
    with zipfile.ZipFile(source_path, "r") as zf:
        return [
            {
                "name": info.filename,
                "size": info.file_size,
                "compressedSize": info.compress_size,
            }
            for info in zf.infolist()
        ]
