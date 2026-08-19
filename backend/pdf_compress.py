import os
import tempfile
from pathlib import Path

from pypdf import PdfReader, PdfWriter


def compress_pdf(source_path: Path, destination_path: Path) -> bool:
    """`source_path`teki PDF'i pypdf-native yontemlerle (icerik akisi
    sikistirma + yinelenen nesne kaldirma) sikistirip YENI bir dosyaya
    (`destination_path`) yazar - kaynaga asla dokunulmaz (Saga #322, ATDD
    AC-1).

    Buyume korumasi (AC-2/AC-5): sonuc boyutu kaynak boyutundan KUCUK
    DEGILSE `destination_path`e HICBIR SEY yazilmaz (gecici dosya silinir),
    `False` doner - hata DEGIL. Gercek kucultme saglanirsa gecici dosya
    `destination_path`e atomik `replace` ile tasinir, `True` doner.

    Kaynak acilamiyorsa (bozuk PDF/dosya yok) pypdf'in firlattigi exception
    yakalanmadan yukari firlatilir - orchestrator bunu `PlanApplicationError`e
    cevirir. Desen `pdf_pages.py`nin tempfile+atomik-replace deseniyle AYNI."""
    reader = PdfReader(str(source_path))
    writer = PdfWriter()
    writer.append(reader)

    for page in writer.pages:
        page.compress_content_streams(level=-1)
    writer.compress_identical_objects(remove_duplicates=True, remove_unreferenced=True)

    fd, temp_path_str = tempfile.mkstemp(
        suffix=".tmp", prefix=destination_path.name + ".", dir=str(destination_path.parent)
    )
    temp_path = Path(temp_path_str)
    os.close(fd)
    try:
        with open(temp_path, "wb") as f:
            writer.write(f)

        original_size = source_path.stat().st_size
        compressed_size = temp_path.stat().st_size
        if compressed_size >= original_size:
            temp_path.unlink(missing_ok=True)
            return False

        temp_path.replace(destination_path)
        return True
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise
