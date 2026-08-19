import os
import shutil
import tempfile
from pathlib import Path

from docx import Document


def append_table(source_path: Path, headers: list | None, rows: list, backup_path: Path) -> None:
    """Saga #327 (ATDD AC-1/AC-2/AC-3/AC-4): `headers` (opsiyonel) ve
    `rows`tan oluşan bir tabloyu `source_path`in SONUNA ekler, kaynağı
    YERİNDE günceller (`excel_rows.append_excel_rows`'un AYNI "önce oku,
    sonra yedekle, sonra atomik yaz" sırası). Sütun sayısı uyuşmazlığında
    (`headers` varsa `len(headers)`, yoksa `rows[0]`'un uzunluğu referans
    alınır) `ValueError` fırlatılır, HİÇBİR ŞEY yazılmaz. Kaynak yoksa/
    bozuksa exception fırlatılır, HİÇBİR dosya oluşturulmaz/değiştirilmez."""
    if not source_path.exists():
        raise FileNotFoundError(
            f"WORD_APPEND_TABLE kaynağı okunamıyor: '{source_path.name}'"
        )

    try:
        document = Document(str(source_path))
    except Exception as exc:
        raise ValueError(
            f"WORD_APPEND_TABLE kaynağı okunamıyor: '{source_path.name}' ({exc})"
        ) from exc

    reference_col_count = len(headers) if headers is not None else len(rows[0])
    for row in rows:
        if len(row) != reference_col_count:
            raise ValueError(
                f"WORD_APPEND_TABLE sütun sayısı uyuşmuyor: '{source_path.name}'"
            )

    total_row_count = (1 if headers is not None else 0) + len(rows)
    table = document.add_table(rows=total_row_count, cols=reference_col_count)

    row_offset = 0
    if headers is not None:
        for col_index, value in enumerate(headers):
            table.rows[0].cells[col_index].text = str(value)
        row_offset = 1

    for row_index, row in enumerate(rows):
        for col_index, value in enumerate(row):
            table.rows[row_offset + row_index].cells[col_index].text = str(value)

    backup_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(source_path), str(backup_path))

    fd, temp_path_str = tempfile.mkstemp(
        suffix=".tmp", prefix=source_path.name + ".", dir=str(source_path.parent)
    )
    temp_path = Path(temp_path_str)
    os.close(fd)
    try:
        document.save(str(temp_path))
        temp_path.replace(source_path)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise
