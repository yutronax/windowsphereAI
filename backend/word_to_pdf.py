import os
import shutil
import subprocess
import tempfile
from pathlib import Path


class WordToPdfConversionError(Exception):
    """Word-to-PDF dönüşümü sırasında oluşan hatalar için exception."""
    pass


def convert_word_to_pdf(source_path: Path, destination_path: Path, timeout: int = 60) -> None:
    """Kaynak .docx dosyasını LibreOffice --convert-to pdf ile hedef
    .pdf dosyasına dönüştürür. Tazelik kontrolü (mtime+boyut) yapılır.

    İşlem adımları:
    1. LibreOffice ikili konumunu bulur (PATH'te "soffice" veya sabit Windows yolu).
    2. Dönüşüm öncesi hedef dosyasının (varsa) mtime'ını kaydeder.
    3. Geçici bir dizinde subprocess çalıştırır (LibreOffice çıktı dosya adını
       her zaman source.stem+".pdf" olarak üretir).
    4. Tazelik doğrulaması yapar: geçici çıktı dosyası varsa ve mtime'ı
       dönüşüm öncesi hedef mtime'ından daha yeniyse, atomik taşıma yapılır.
    5. Tazelik kontrolü başarısızsa (profil kilidi, başarısız dönüşüm vb.)
       WordToPdfConversionError fırlatılır.

    Hata halleri:
    - LibreOffice bulunamazsa: "LibreOffice bulunamadı" mesajıyla exception.
    - Timeout: "Dönüşüm zaman aşımına uğradı" mesajıyla exception.
    - Tazelik başarısızsa: "LibreOffice meşgul olabilir, tekrar deneyin" mesajıyla exception.

    Args:
        source_path: .docx dosyasının yolu (var olması gerekir).
        destination_path: Oluşturulacak .pdf dosyasının hedef yolu.
        timeout: Subprocess çağrısı için timeout (saniye), varsayılan 60.

    Raises:
        WordToPdfConversionError: Dönüşüm başarısız olursa.
    """
    # 1. LibreOffice ikili konumunu bulur (PATH'ten).
    soffice_path = shutil.which("soffice")
    if soffice_path is None:
        raise WordToPdfConversionError("LibreOffice bulunamadı")

    # 2. Dönüşüm öncesi hedef dosyasının mtime'ını kaydet (varsa).
    pre_conversion_mtime = None
    if destination_path.exists():
        try:
            pre_conversion_mtime = destination_path.stat().st_mtime
        except (OSError, ValueError):
            # Dosya var ama stat başarısız olmuş, yine de devam et.
            pass

    # 3. Geçici dizin oluştur ve subprocess çalıştır.
    tmp_dir = tempfile.mkdtemp()
    try:
        try:
            result = subprocess.run(
                [soffice_path, "--headless", "--norestore", "--convert-to", "pdf",
                 "--outdir", tmp_dir, str(source_path)],
                timeout=timeout,
                capture_output=True,
                text=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise WordToPdfConversionError("Dönüşüm zaman aşımına uğradı") from exc

        # 4. LibreOffice'in ürettiği geçici çıktı dosyasını bul.
        # (LibreOffice her zaman source.stem + ".pdf" olarak üretir)
        temp_output = Path(tmp_dir) / (source_path.stem + ".pdf")

        # 5. Tazelik doğrulaması: geçici çıktı varsa ve boyutu > 0,
        # ve mtime dönüşüm-öncesi hedeftekinden (varsa) daha yeniyse.
        if not temp_output.exists():
            raise WordToPdfConversionError(
                "LibreOffice meşgul olabilir, tekrar deneyin"
            )

        temp_stats = temp_output.stat()
        if temp_stats.st_size == 0:
            raise WordToPdfConversionError(
                "LibreOffice meşgul olabilir, tekrar deneyin"
            )

        # mtime karşılaştırması: geçici çıktı, dönüşüm öncesi hedef mtime'ından
        # daha yeni olmalı (veya hedef hiç yoksa).
        if pre_conversion_mtime is not None:
            if temp_stats.st_mtime <= pre_conversion_mtime:
                raise WordToPdfConversionError(
                    "LibreOffice meşgul olabilir, tekrar deneyin"
                )

        # 6. Atomik taşıma.
        temp_output.replace(destination_path)

    finally:
        # Geçici dizini temizle.
        try:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        except Exception:
            pass
