import os
import tempfile
from pathlib import Path

from PIL import Image


def crop_image(
    source_path: Path, box: tuple[float, float, float, float], destination_path: Path
) -> None:
    """Saga #329 (ATDD AC-1/AC-3/AC-7): `source_path`teki görseli `box`
    (`x0, y0, x1, y1`) ile kırpıp YENİ bir dosyaya (`destination_path`)
    yazar, kaynağa hiç dokunmaz. `img.crop()` sınır-dışı bir `box` için
    HATA VERMEZ (sessizce siyah/boş alanla doldurur) - bu yüzden `box`ın
    geometrisi VE kaynağın gerçek piksel sınırlarını (`img.size`) aşıp
    aşmadığı `img.crop()` ÇAĞRILMADAN ÖNCE elle kontrol edilir (plan.md
    Risks), Pillow'un kendi sessiz toleransına GÜVENİLMEZ."""
    x0, y0, x1, y1 = box
    if x1 <= x0:
        raise ValueError("box'ın x1 değeri x0'dan büyük olmalı")
    if y1 <= y0:
        raise ValueError("box'ın y1 değeri y0'dan büyük olmalı")

    with Image.open(str(source_path)) as img:
        width, height = img.size
        if x0 < 0 or y0 < 0 or x1 > width or y1 > height:
            raise ValueError(
                f"box ({box}) kaynağın piksel sınırlarını ({width}x{height}) aşıyor"
            )
        cropped = img.crop(box)

        fd, temp_path_str = tempfile.mkstemp(
            suffix=".tmp", prefix=destination_path.name + ".", dir=str(destination_path.parent)
        )
        temp_path = Path(temp_path_str)
        os.close(fd)
        try:
            # `.tmp` uzantısı Pillow'un formatı dosya uzantısından çıkarmasını
            # engeller (`unknown file extension`) - kaynağın kendi formatı
            # açıkça geçirilir (`format` kaynak/hedef arasında değişmez, ATDD
            # "Kapsam Dışı" bölümü).
            cropped.save(str(temp_path), format=img.format)
            temp_path.replace(destination_path)
        except Exception:
            temp_path.unlink(missing_ok=True)
            raise


def create_thumbnail(
    source_path: Path, max_width: int, max_height: int, destination_path: Path
) -> None:
    """Saga #329 (ATDD AC-4/AC-6/AC-7): `source_path`teki görselin en-boy
    oranını KORUYARAK `max_width`x`max_height` üst sınırına küçültülmüş bir
    kopyasını YENİ bir dosyaya (`destination_path`) yazar, kaynağa hiç
    dokunmaz. `Image.thumbnail()` IN-PLACE çalışır ve `None` döner (plan.md
    ile doğrulandı) - `img.thumbnail((max_width, max_height))` çağrıldıktan
    SONRA `img` kaydedilir, dönüş değeri hiç kullanılmaz."""
    if max_width <= 0 or max_height <= 0:
        raise ValueError("maxWidth ve maxHeight pozitif olmalı")

    with Image.open(str(source_path)) as img:
        source_format = img.format
        img.thumbnail((max_width, max_height))

        fd, temp_path_str = tempfile.mkstemp(
            suffix=".tmp", prefix=destination_path.name + ".", dir=str(destination_path.parent)
        )
        temp_path = Path(temp_path_str)
        os.close(fd)
        try:
            img.save(str(temp_path), format=source_format)
            temp_path.replace(destination_path)
        except Exception:
            temp_path.unlink(missing_ok=True)
            raise
