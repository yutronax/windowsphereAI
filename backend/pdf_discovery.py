import datetime as dt
from pathlib import Path

from backend.models import PdfFileMetadata


def discover_pdf_files(folder: Path) -> list[PdfFileMetadata]:
    """`folder`ın DOĞRUDAN altındaki (alt klasörler dahil edilmez —
    Saga #272'nin derinlik/whitelist kısıtlarıyla tutarlı, taşınacak
    dosyalar zaten kullanıcının seçtiği kökte olmalı) `.pdf` dosyalarını
    listeler. `createdAt`, dosyanın oluşturulma zaman damgasından
    (`Path.stat().st_ctime`) türetilir — bu SADECE Windows'ta gerçek
    "oluşturulma zamanı"dır (proje şu an sadece Windows hedefliyor);
    POSIX'te `st_ctime` "son meta veri değişikliği zamanı"dır, backend
    ileride Linux/macOS'ta çalıştırılırsa bu alan sessizce yanlış anlam
    taşır — bu red-team bulgusu olarak belgelendi, henüz düzeltilmedi
    (proje Windows-only kapsamında MVP için kabul edilebilir).
    `folder` yoksa veya bir dizin değilse boş liste döner — bu fonksiyon
    seviyesinde bir hata SAYILMAZ (çağıran, ör. `/api/plan`, klasörün
    var olup olmadığını KENDİSİ ayrıca kontrol etmelidir; bkz.
    backend/main.py'deki `allowed_root.is_dir()` kontrolü).

    Gizli (nokta ile başlayan) dosya/klasörler HER ZAMAN atlanır — ör.
    `.windows-ai-files-backup/` (Saga #289'un DELETE fiziksel yedek
    klasörü). Tarama zaten recursive olmadığı için bu klasörün İÇİNDEKİ
    dosyalar (2 seviye derinde) yapısal olarak zaten taranamaz, ama bu
    koruma AÇIKÇA/kendini belgeleyen şekilde kodda dursun istendi —
    ileride tarama recursive hale getirilirse "silinmiş" dosyaların
    yanlışlıkla yeni bir planın kaynağı olarak yeniden keşfedilmesini
    yapısal olarak engeller (red-team bulgusu, Saga #289)."""
    if not folder.is_dir():
        return []

    pdf_files = [
        entry
        for entry in folder.iterdir()
        if entry.is_file() and entry.suffix.lower() == ".pdf" and not entry.name.startswith(".")
    ]

    return [
        PdfFileMetadata(
            filename=entry.name,
            createdAt=dt.datetime.fromtimestamp(entry.stat().st_ctime, tz=dt.timezone.utc).isoformat(),
        )
        for entry in sorted(pdf_files, key=lambda entry: entry.name)
    ]
