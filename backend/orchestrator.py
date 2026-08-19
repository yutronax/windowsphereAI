import datetime as dt
import os
import shutil
import tempfile
import time
from pathlib import Path

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from backend import excel_rows, excel_sort, image_ops, pdf_compress, pdf_pages, word_table, zip_ops
from backend.db_models import FileOperation, Transaction
from backend.file_operations import create_transaction, record_file_operation
from backend.models import OperationType, PdfFileMetadata, PlanSkeleton, PlanStep
from backend.pdf_ocr import ocr_pdf_file
from backend.pdf_redact import redact_pdf_page
from backend.security import PathWhitelistError, is_path_allowed, validate_plan_paths


class PlanApplicationError(Exception):
    """Raised when a plan cannot be applied. Any moves already performed for
    this call have been rolled back (moved back to their original location)
    before this is raised."""


class TransactionRevertError(Exception):
    """Raised when an already-committed transaction cannot be (fully)
    reverted by `revert_transaction`. Any operations that WERE successfully
    reverted have already been persisted as "rolled_back" before this is
    raised — a partial revert is never silently lost, mirroring
    `apply_plan`'s own rollback-except-block behavior."""


# Saga #288/#289: MOVE'a ek olarak COPY ve DELETE desteklenmeye başladı.
# Her operationType'ın İLERİ (forward) ve GERİ (rollback) uygulaması farklı
# fiziksel semantiğe sahip — bu yüzden dispatch dict'leri kullanılıyor
# (gelecekteki RENAME task'ı için dördüncü bir dal eklemeyi kolaylaştırır).
#
# Sözleşme (tüm operationType'lar için AYNI — Saga #289'da netleştirildi):
# `destination_path` = forward işlem SONRASI dosyanın FİZİKSEL OLARAK
# bulunduğu yer; `backup_path` = rollback'in GERİ YÜKLEYECEĞİ konum. MOVE
# için destination=yeni konum/backup=eski konum; COPY için destination=kopya/
# backup=kaynak (rollback'te kullanılmaz, sadece şema tutarlılığı için);
# DELETE için destination=gizli yedek konumu/backup=orijinal kaynak konumu.
# Bu ortak sözleşme sayesinde rollback döngüsü HİÇBİR operationType'a özel
# dallanma gerektirmeden çalışır.
_SUPPORTED_OPERATION_TYPES = {
    OperationType.MOVE,
    OperationType.COPY,
    OperationType.DELETE,
    OperationType.RENAME,
    OperationType.LIST,
    OperationType.MERGE,
    OperationType.SPLIT,
    OperationType.OCR,
    OperationType.REDACT,
    OperationType.EXCEL_SORT,
    OperationType.EXCEL_FILTER,
    OperationType.PDF_EXTRACT_PAGES,
    OperationType.PDF_DELETE_PAGES,
    OperationType.APPEND,
    OperationType.PDF_COMPRESS,
    OperationType.EXCEL_CREATE,
    OperationType.EXCEL_APPEND,
    OperationType.WORD_APPEND_TABLE,
    OperationType.ZIP_CREATE,
    OperationType.ZIP_ADD,
    OperationType.ZIP_EXTRACT,
    OperationType.ZIP_MERGE,
    OperationType.IMAGE_CROP,
    OperationType.IMAGE_THUMBNAIL,
}

# DELETE'in fiziksel yedeklerinin saklandığı, `allowed_root` altında gizli
# klasör. transaction.id ile ayrıştırılır (farklı transaction'lardaki aynı
# isimli dosyalar çakışmasın diye). Derinlik: klasör+txn_id+dosya = 3,
# MAX_PATH_DEPTH'i (security.py, Saga #272) AŞMAZ.
_DELETE_BACKUP_DIRNAME = ".windows-ai-files-backup"


def _delete_backup_path(allowed_root: Path, transaction_id: int, filename: str) -> Path:
    return allowed_root / _DELETE_BACKUP_DIRNAME / str(transaction_id) / filename


_TRANSIENT_IO_WINERRORS = (32, 5)  # kilitli dosya (Excel/Outlook), antivirüs geçici bloğu
_TRANSIENT_IO_MAX_ATTEMPTS = 3
_TRANSIENT_IO_BACKOFF_SECONDS = 0.5


def _retry_on_transient_io_error(func, *args, **kwargs):
    """Saga #310: `func`'ı çağırır; `winerror` 32 (kilitli dosya) veya 5
    (antivirüsün geçici bloğu) olan bir `OSError` alırsa üstel backoff'lu
    olarak en fazla `_TRANSIENT_IO_MAX_ATTEMPTS` kez tekrar dener. Diğer
    tüm hatalar (kalıcı yetki sorunu, dosya yok, vb.) hiç retry edilmeden
    hemen fırlatılır — davranış bu hata sınıflarında DEĞİŞMEZ."""
    for attempt in range(_TRANSIENT_IO_MAX_ATTEMPTS):
        try:
            return func(*args, **kwargs)
        except OSError as exc:
            is_transient = getattr(exc, "winerror", None) in _TRANSIENT_IO_WINERRORS
            if not is_transient or attempt == _TRANSIENT_IO_MAX_ATTEMPTS - 1:
                raise
            time.sleep(_TRANSIENT_IO_BACKOFF_SECONDS * (2**attempt))


def _forward_move(source_path: Path, destination_path: Path) -> None:
    _retry_on_transient_io_error(shutil.move, str(source_path), str(destination_path))


def _forward_copy(source_path: Path, destination_path: Path) -> None:
    _retry_on_transient_io_error(shutil.copy2, str(source_path), str(destination_path))


def _forward_delete(source_path: Path, destination_path: Path) -> None:
    # `destination_path` burada gizli yedek konumu (bkz. `_delete_backup_path`).
    # Önce fiziksel yedek alınır, SONRA kaynak silinir — sıra önemli: yedek
    # başarısız olursa kaynak hâlâ yerinde kalır, hiçbir veri kaybı olmaz.
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    _retry_on_transient_io_error(shutil.copy2, str(source_path), str(destination_path))
    _retry_on_transient_io_error(source_path.unlink)


def _forward_merge(source_paths: list[Path], destination_path: Path) -> None:
    # Saga #304: N kaynak PDF'i sırayla append edip TEK bir yeni PDF'e yazar
    # — pypdf'in basit "reader'ları sırayla append et, tek dosyaya yaz" akışı
    # (bkz. ATDD S6). Kaynaklara HİÇ dokunulmaz.
    #
    # Red-team bulgusu (Saga #304): writer.write() destination_path'e
    # DOĞRUDAN yazarsa, yazma yarıda kesilirse (disk dolu, izin hatası vb.)
    # destination_path'te YARIM/BOZUK bir dosya kalır — çağıran kod
    # (apply_plan) rollback-temizliğini SADECE _forward_merge başarıyla
    # DÖNDÜKTEN SONRA işaretler, yani başarısız bir yazmadan sonra ortada
    # kalan artık dosya için hiçbir temizlik yolu yoktur. Bunun yerine
    # AYNI klasörde bir geçici dosyaya yazılır, SONRA `Path.replace` ile
    # (aynı dosya sistemi içinde atomik) gerçek hedefe taşınır — yazma
    # tamamlanmadan destination_path'e hiçbir şey dokunmaz. Yazma
    # başarısız olursa geçici dosya temizlenir, destination_path hiç
    # oluşturulmamış olur.
    from pypdf import PdfWriter

    fd, temp_path_str = tempfile.mkstemp(
        suffix=".tmp", prefix=destination_path.name + ".", dir=str(destination_path.parent)
    )
    temp_path = Path(temp_path_str)
    os.close(fd)
    try:
        writer = PdfWriter()
        for source_path in source_paths:
            writer.append(str(source_path))
        writer.write(str(temp_path))
        writer.close()
        temp_path.replace(destination_path)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise


def _forward_split_page(reader_page, destination_path: Path) -> None:
    # Saga #305: MERGE'in duzeltilmis _forward_merge'iyle AYNI gecici-dosya-
    # yaz + atomik-tasi deseni (bkz. o fonksiyonun docstring'i, Saga #304
    # red-team dersi) - HER cikti sayfasi icin ayri ayri uygulanir, yarida
    # kesilen bir yazma destination_path'te YARIM/BOZUK bir dosya BIRAKMAZ.
    from pypdf import PdfWriter

    fd, temp_path_str = tempfile.mkstemp(
        suffix=".tmp", prefix=destination_path.name + ".", dir=str(destination_path.parent)
    )
    temp_path = Path(temp_path_str)
    os.close(fd)
    try:
        writer = PdfWriter()
        writer.add_page(reader_page)
        writer.write(str(temp_path))
        writer.close()
        temp_path.replace(destination_path)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise


def _forward_redact(source_path: Path, page_number: int, regions: list, destination_path: Path) -> None:
    # Saga #320: MERGE/SPLIT ile AYNI gecici-dosya-yaz + atomik-tasi deseni.
    # Kaynagin TUM sayfalari vektorel olarak korunur, SADECE `page_number`
    # rasterize edilmis (uzerine opak siyah kutu(lar) cizilmis) sayfayla
    # degistirilir.
    import io

    from pypdf import PdfReader, PdfWriter

    redacted_page_bytes = redact_pdf_page(source_path, page_number, regions)

    fd, temp_path_str = tempfile.mkstemp(
        suffix=".tmp", prefix=destination_path.name + ".", dir=str(destination_path.parent)
    )
    temp_path = Path(temp_path_str)
    os.close(fd)
    try:
        source_reader = PdfReader(str(source_path))
        redacted_reader = PdfReader(io.BytesIO(redacted_page_bytes))

        writer = PdfWriter()
        for page_index, page in enumerate(source_reader.pages):
            if page_index + 1 == page_number:
                writer.add_page(redacted_reader.pages[0])
            else:
                writer.add_page(page)
        writer.write(str(temp_path))
        writer.close()
        temp_path.replace(destination_path)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise


def _render_text_page_bytes(text: str) -> bytes:
    """Saga #323: `text`i A4 sayfaya duz metin olarak ceviren tek-sayfalik
    bir PDF'in bytes'ini uretir (ReportLab). Uzun metinler `textwrap.wrap`
    ile satirlara bolunur (plan.md: word-wrap gerekli)."""
    import io
    import textwrap

    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    buffer = io.BytesIO()
    pdf_canvas = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    left_margin = 50
    top_margin = height - 50
    line_height = 14

    y = top_margin
    for line in textwrap.wrap(text, width=90) or [""]:
        pdf_canvas.drawString(left_margin, y, line)
        y -= line_height

    pdf_canvas.showPage()
    pdf_canvas.save()
    return buffer.getvalue()


def _forward_append(source_path: Path, append_text: str, backup_path: Path | None = None) -> None:
    """Saga #323: `source_path`in SONUNA `append_text`ten render edilmis
    yeni bir sayfa ekler, kaynagi YERINDE gunceller (destination ==
    source_path). Kaynak-yok (AC-3) ile kaynak-bozuk (AC-2) AYRI mesajlarla
    ayirt edilir — eski projenin ikisini AYNI kod yoluna dusurup bozuk
    kaynagin icerigini sessizce silen kusuru burada BILINCLI olarak
    imkansiz kilinir: hicbir yazma islemi, kaynak BASARIYLA okunup yeni
    sayfa render edilmeden ONCE baslamiyor (gecici-dosya+atomik-replace,
    MERGE/REDACT ile AYNI desen).

    `backup_path` verilirse (apply_plan'in rollback/revert desteği icin),
    kaynak BASARIYLA okunup yeni sayfa render edildikten SONRA ama atomik
    degistirmeden HEMEN ONCE (yani kaynagin son GECERLI hali biliniyorken)
    kaynagin bir kopyasi oraya alinir - APPEND fiziksel olarak YERINDE
    guncelleme yaptigi icin (COPY/MERGE/REDACT'in aksine), rollback icin
    orijinal icerigin ayri bir yedegi gerekir."""
    import io

    from pypdf import PdfReader, PdfWriter

    if not source_path.exists():
        raise PlanApplicationError(
            f"Kaynak dosya bulunamadı: '{source_path.name}'"
        )

    try:
        source_reader = PdfReader(str(source_path))
        source_pages = list(source_reader.pages)
    except Exception as exc:
        raise PlanApplicationError(
            f"Kaynak PDF okunamıyor, bozuk olabilir: '{source_path.name}' ({exc})"
        ) from exc

    new_page_bytes = _render_text_page_bytes(append_text)
    new_page_reader = PdfReader(io.BytesIO(new_page_bytes))

    destination_path = source_path
    fd, temp_path_str = tempfile.mkstemp(
        suffix=".tmp", prefix=destination_path.name + ".", dir=str(destination_path.parent)
    )
    temp_path = Path(temp_path_str)
    os.close(fd)
    try:
        writer = PdfWriter()
        for page in source_pages:
            writer.add_page(page)
        writer.add_page(new_page_reader.pages[0])
        writer.write(str(temp_path))
        writer.close()
        if backup_path is not None:
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(source_path), str(backup_path))
        temp_path.replace(destination_path)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise


_FORWARD_OPERATIONS = {
    OperationType.MOVE: _forward_move,
    OperationType.COPY: _forward_copy,
    OperationType.DELETE: _forward_delete,
    # Saga #290: RENAME fiziksel olarak MOVE ile AYNI ("kaynağı hedefe
    # taşı") — tek fark hedefin farklı bir klasörde değil, AYNI klasörde
    # farklı bir isimde olması, bu da sadece `destination_path`'in NASIL
    # hesaplandığında (apply_plan'ın ana döngüsü) fark yaratır.
    OperationType.RENAME: _forward_move,
}


def _rollback_move(destination_path: Path, backup_path: Path) -> None:
    shutil.move(str(destination_path), str(backup_path))


def _rollback_copy(destination_path: Path, backup_path: Path) -> None:
    # COPY'de kaynak hiç değişmedi — rollback SADECE hedefteki kopyayı siler,
    # backup_path'e (=kaynak) hiç dokunmaz.
    destination_path.unlink()


def _rollback_append(destination_path: Path, backup_path: Path) -> None:
    # Saga #323: APPEND, MOVE/COPY'nin aksine kaynağı YERİNDE günceller
    # (destination_path == orijinal kaynak konumu) — bu yüzden rollback
    # hedefi "silmek" değil, `_forward_append`in atomik değiştirmeden hemen
    # önce aldığı gizli yedeği (backup_path) geri KOPYALAYARAK dosyayı
    # eklenmiş sayfa öncesi haline döndürmektir.
    shutil.copy2(str(backup_path), str(destination_path))


def _zip_extract_backup_marker(destination_path: Path, *, folder_existed_before: bool) -> Path:
    # Saga #328 (plan.md): ZIP_EXTRACT'in hedefi bir KLASOR (potansiyel
    # olarak cok sayida dosya), _rollback_copy'nin "tek dosya sil" semantigi
    # dogrudan kullanilamaz. `backup_path` burada "destinationFolder islem
    # ONCESINDE var miydi" bilgisini tasiyan bir SENTINEL: `destination_path`
    # ile AYNI deger = klasor ONCEDEN VARDI -> rollback no-op (DELETE'in
    # "gercek anlamda geri donussuz" sinifiyla AYNI, var olan icerik geri
    # alinamaz). FARKLI bir deger (ayni klasorun altinda, `allowed_root`
    # sinirini asmayan bir isaretci) = klasor orchestrator TARAFINDAN
    # olusturuldu -> rollback TUM klasoru siler. `_rollback_completed_operations`
    # `is_path_allowed(backup_path, allowed_root)` kontrolu yaptigi icin bu
    # isaretci gercekten var olmasa bile `allowed_root` altinda kalmali.
    if folder_existed_before:
        return destination_path
    return destination_path.parent / (destination_path.name + ".zip-extract-created")


def _rollback_zip_extract(destination_path: Path, backup_path: Path) -> None:
    if backup_path == destination_path:
        return  # no-op - klasor onceden vardi, dokunulmaz.
    shutil.rmtree(destination_path, ignore_errors=True)


_ROLLBACK_OPERATIONS = {
    OperationType.MOVE: _rollback_move,
    OperationType.COPY: _rollback_copy,
    # DELETE rollback'i MOVE ile AYNI: "gizli yedek konumundaki dosyayı
    # orijinal konuma geri taşı" — _rollback_move zaten tam olarak bunu
    # yapıyor, ayrı bir fonksiyona gerek yok.
    OperationType.DELETE: _rollback_move,
    # RENAME rollback'i de MOVE ile aynı: hedefi (yeni isim) kaynağa
    # (eski isim, backup_path) geri taşı.
    OperationType.RENAME: _rollback_move,
    # Saga #304: MERGE rollback'i COPY ile AYNI — kaynaklar hiç değişmedi,
    # rollback SADECE hedefteki yeni birleşik dosyayı siler (ATDD S2).
    OperationType.MERGE: _rollback_copy,
    # Saga #305: SPLIT rollback'i de COPY ile AYNI - kaynak hic degismedi,
    # her cikti dosyasi icin bagimsiz olarak sadece hedefi siler (ATDD S2,
    # SPLIT'e ozel yeni bir rollback fonksiyonu GEREKMIYOR).
    OperationType.SPLIT: _rollback_copy,
    # Saga #320: REDACT rollback'i de COPY ile AYNI - kaynak hic degismedi,
    # rollback SADECE hedefteki karartilmis dosyayi siler (ATDD S2).
    OperationType.REDACT: _rollback_copy,
    # Saga #324: EXCEL_SORT rollback'i de COPY ile AYNI - kaynak hic
    # degismedi, rollback SADECE hedefteki siralanmis dosyayi siler.
    OperationType.EXCEL_SORT: _rollback_copy,
    # Saga #325: EXCEL_FILTER rollback'i de COPY ile AYNI - kaynak hic
    # degismedi, rollback SADECE hedefteki filtrelenmis dosyayi siler.
    OperationType.EXCEL_FILTER: _rollback_copy,
    # Saga #321: PDF_EXTRACT_PAGES/PDF_DELETE_PAGES rollback'i de COPY ile
    # AYNI - kaynak hic degismedi, rollback SADECE hedefteki cikti dosyasini
    # siler.
    OperationType.PDF_EXTRACT_PAGES: _rollback_copy,
    OperationType.PDF_DELETE_PAGES: _rollback_copy,
    # Saga #323: APPEND rollback'i - bkz. `_rollback_append` docstring'i.
    OperationType.APPEND: _rollback_append,
    # Saga #322: PDF_COMPRESS rollback'i de COPY ile AYNI - kaynak hic
    # degismedi, rollback SADECE hedefteki sikistirilmis dosyayi siler.
    # Buyume korumasi tetiklendiginde (compress_pdf False doner) zaten
    # hicbir FileOperation kaydi olusmadigi icin bu haritaya hic bakilmaz.
    OperationType.PDF_COMPRESS: _rollback_copy,
    # Saga #326: EXCEL_CREATE rollback'i de COPY ile AYNI - kaynak yok,
    # rollback SADECE hedefteki yeni oluşturulan dosyayı siler.
    OperationType.EXCEL_CREATE: _rollback_copy,
    # Saga #326: EXCEL_APPEND rollback'i - PDF APPEND'in `_rollback_append`
    # ile AYNI fonksiyonu (dosya-tipinden bağımsız, sadece `shutil.copy2`
    # ile backup_path'i geri kopyalar).
    OperationType.EXCEL_APPEND: _rollback_append,
    # Saga #327: WORD_APPEND_TABLE rollback'i - EXCEL_APPEND'in AYNI
    # fonksiyonu (dosya-tipinden bağımsız, sadece `shutil.copy2` ile
    # backup_path'i geri kopyalar).
    OperationType.WORD_APPEND_TABLE: _rollback_append,
    # Saga #328: ZIP_CREATE/ZIP_ADD/ZIP_MERGE rollback'i COPY ile AYNI -
    # kaynak(lar) hic degismedi, rollback SADECE hedefteki yeni zip'i siler.
    OperationType.ZIP_CREATE: _rollback_copy,
    OperationType.ZIP_ADD: _rollback_copy,
    OperationType.ZIP_MERGE: _rollback_copy,
    # Saga #328: ZIP_EXTRACT rollback'i - bkz. `_rollback_zip_extract`
    # docstring'i (klasor onceden var miydi izlemesi).
    OperationType.ZIP_EXTRACT: _rollback_zip_extract,
    # Saga #329: IMAGE_CROP/IMAGE_THUMBNAIL rollback'i COPY ile AYNI -
    # kaynak hic degismedi, rollback SADECE hedefteki yeni gorseli siler.
    OperationType.IMAGE_CROP: _rollback_copy,
    OperationType.IMAGE_THUMBNAIL: _rollback_copy,
}


# Saga #323: APPEND'in gizli yedeklerinin saklandığı, DELETE'in
# `_DELETE_BACKUP_DIRNAME`'iyle AYNI desende ama AYRI bir klasör
# (in-place güncellemenin yedeği DELETE'in "silinmiş dosya" yedeğiyle
# karışmasın diye).
_APPEND_BACKUP_DIRNAME = ".windows-ai-files-append-backup"


def _append_backup_path(allowed_root: Path, transaction_id: int, filename: str) -> Path:
    return allowed_root / _APPEND_BACKUP_DIRNAME / str(transaction_id) / filename


def _rollback_completed_operations(operations: list[FileOperation], allowed_root: Path) -> bool:
    """Saga #293: `apply_plan`in kendi hata-anı except-bloğu (Saga #276) VE
    `revert_transaction`in PAYLAŞTIĞI tek yardımcı — bir `FileOperation`
    listesini (ÇAĞIRAN TARAFINDAN zaten doğru [ters] sırada verilmiş
    olmalı) `destination_path`/`backup_path` alanları üzerinden fiziksel
    olarak geri alır. Her operasyon için: hedef zaten yoksa (önceden geri
    alınmış/hiç tamamlanmamış) doğrudan "rolled_back"; ters işlemin
    KENDİSİ başarısız olursa (OSError/ValueError/KeyError — bkz. Saga #288
    red-team notu) "rollback_failed" (yanlışlıkla "rolled_back" DENMEZ,
    dosya fiziksel olarak hâlâ hedefte); aksi halde "rolled_back".

    `allowed_root` ZORUNLU (Saga #293 red-team önerisi: opsiyonel/`None`
    varsayılanlı bir savunma-derinliği kontrolü, gelecekte bu yardımcıyı
    yeni bir çağıran path'lerin TAZE doğrulanmadığı bir bağlamdan
    `allowed_root` geçirmeyi UNUTARAK çağırırsa sessizce devre dışı kalan
    bir "footgun" olurdu — zorunlu yapmak bunu tip seviyesinde imkansız
    kılar, maliyeti sıfıra yakın çünkü her iki çağıranın da zaten
    `allowed_root` scope'ta var). Hem `destination_path` hem `backup_path`
    bu kök altında değilse operasyon hiç denenmeden "rollback_failed"
    işaretlenir — `apply_plan`in kendi except-bloğu path'ler AYNI çağrı
    içinde `validate_plan_paths` ile daha yeni doğrulanmış olsa da kendi
    `allowed_root`'unu geçirir (ucuz, redundant ama zararsız bir kontrol).

    Tümü başarılıysa `True`, en az biri `"rollback_failed"` olduysa
    `False` döner — çağıran bunu nihai transaction durumuna karar vermek
    için kullanır."""
    all_succeeded = True
    for operation in operations:
        destination_path = Path(operation.destination_path)
        original_source_path = Path(operation.backup_path)
        if not (
            is_path_allowed(destination_path, allowed_root)
            and is_path_allowed(original_source_path, allowed_root)
        ):
            operation.status = "rollback_failed"
            all_succeeded = False
            continue
        if not destination_path.exists():
            operation.status = "rolled_back"
            continue
        try:
            _ROLLBACK_OPERATIONS[OperationType(operation.operation_type)](
                destination_path, original_source_path
            )
            operation.status = "rolled_back"
        except (OSError, ValueError, KeyError):
            operation.status = "rollback_failed"
            all_succeeded = False
    return all_succeeded


def _claim_transaction_status(
    session: Session, transaction_id: int, *, from_status: str, to_status: str
) -> bool:
    """SQLite `with_for_update()`u desteklemediği için satır seviyesinde
    optimistic locking'i atomik bir compare-and-swap UPDATE ile taklit eder:
    `UPDATE transactions SET status=to_status WHERE id=transaction_id AND
    status=from_status`. Dönen `rowcount == 1` ise satırı BU çağıran
    "kazanmış" demektir (aynı anda başka bir işlemin aynı satırı claim
    etmesi imkansızdır, SQLite'ın tek-yazarlık kilidi sayesinde); `0` ise
    satır artık `from_status` durumunda DEĞİLDİR (yarışı kaybedildi)."""
    # `session.commit()` varsayılan olarak (`expire_on_commit=True`)
    # session'daki TÜM nesneleri expire eder — bu da çağıranın daha önce
    # yüklediği ilişkili nesnelerde (ör. `transaction.operations`) bir
    # SONRAKİ attribute okumasının sessizce YENİ bir SELECT (ve dolayısıyla
    # SQLite'ta yeni bir okuma transaction'ı) tetiklemesine yol açar — bu da
    # rollback döngüsü sürerken başka bir session'ın aynı satıra yazıp
    # commit etmesini "database is locked" ile engelleyebilir (Saga #302
    # red-team bulgusu). Claim'in commit'ini geçici olarak expire etkisi
    # olmadan yapıyoruz; çağıranlar zaten claim başarılı olduğunda ilgili
    # nesnenin `.status`unu bellekte elle güncelliyor.
    previous_expire_on_commit = session.expire_on_commit
    session.expire_on_commit = False
    try:
        result = session.execute(
            update(Transaction)
            .where(Transaction.id == transaction_id, Transaction.status == from_status)
            .values(status=to_status)
        )
        session.commit()
    finally:
        session.expire_on_commit = previous_expire_on_commit
    return result.rowcount == 1


def revert_transaction(session: Session, transaction: Transaction) -> Transaction:
    """Saga #293: ZATEN `"committed"` durumundaki bir transaction'ı
    SONRADAN (kullanıcının manuel "geri al" isteğiyle, `apply_plan`'ın
    kendi çağrısı sırasındaki hata rollback'inden BAĞIMSIZ) geri alır.
    Sadece `status == "committed"` bir transaction kabul edilir — `pending`/
    `rolled_back`/`reverted`/`revert_failed` bir transaction'ı "geri almak"
    anlamsız veya tehlikelidir (ör. zaten `rolled_back` bir transaction'ı
    tekrar geri almak dosyaları YANLIŞ yöne taşırdı), bu yüzden reddedilir
    ve hiçbir dosyaya dokunulmaz.

    Saga #301: `allowed_root` artık parametre olarak alınmaz — Saga #294/
    #295'teki "Transaction tablosunda allowed_root kolonu YOK, istemciden
    gelir" kararı YANLIŞTI (client-supplied bir güvenlik sınırı spoofable'dı).
    Şimdi `transaction.allowed_root` (apply_plan sırasında server tarafında
    kaydedilen) kullanılır — `None` ise (migration öncesi eski kayıt)
    hiçbir dosyaya dokunulmadan `TransactionRevertError` fırlatılır.

    Sadece `status == "completed"` operasyonlar (LIST hiç kayıt
    oluşturmadığı için zaten hiç görünmez, Saga #291) TERS SIRAYLA
    `_rollback_completed_operations` ile geri alınır — `apply_plan`'ın
    kendi rollback'iyle AYNI paylaşılan mantık, kod tekrarı yok.

    Tümü başarılıysa transaction `"reverted"`, en az biri başarısız
    olursa `"revert_failed"` işaretlenir — HER İKİ durumda da DB'ye
    commit edilir (kısmi ilerleme asla sessizce kaybolmaz, `apply_plan`in
    "asla sessiz kısmi başarı" ilkesiyle simetrik); `"revert_failed"`
    durumunda `TransactionRevertError` fırlatılır."""
    if transaction.status != "committed":
        raise TransactionRevertError(
            f"Sadece 'committed' durumundaki bir transaction geri alınabilir, mevcut durum: '{transaction.status}'"
        )

    if transaction.allowed_root is None:
        raise TransactionRevertError(
            f"Transaction {transaction.id} için allowed_root kaydı yok, geri alınamıyor."
        )
    allowed_root = Path(transaction.allowed_root)

    completed_operations = [op for op in transaction.operations if op.status == "completed"]

    all_reverted = _rollback_completed_operations(
        list(reversed(completed_operations)), allowed_root=allowed_root
    )

    # Saga #302: dosya rollback'i bittikten sonra, DB'ye SON durumu yazmadan
    # hemen once atomik bir claim (compare-and-swap) yapılır — satır hâlâ
    # "committed" DEĞİLSE (ör. `purge_expired_delete_backups` araya girip
    # "backup_purged" yazdıysa) bu commit KENDİ sonucunu kazananın yazdığı
    # değerin ÜZERİNE YAZMAZ, bunun yerine hiçbir şey yazmadan
    # `TransactionRevertError` fırlatır (dosyalar zaten geri alınmış
    # olabilir, ama DB satırı yarışı kazananın değerinde kalır).
    final_status = "reverted" if all_reverted else "revert_failed"
    if not _claim_transaction_status(
        session, transaction.id, from_status="committed", to_status=final_status
    ):
        raise TransactionRevertError(
            f"Transaction {transaction.id} geri alma sırasında durumu başka bir işlem tarafından değiştirildi, sonuç yazılamadı."
        )
    transaction.status = final_status

    if not all_reverted:
        raise TransactionRevertError(
            f"Transaction {transaction.id} tam olarak geri alınamadı, bazı dosyalar kendi hedef konumlarında kaldı."
        )
    return transaction


def _distribute_files_to_steps(
    pdf_files: list[PdfFileMetadata], steps: list[PlanStep]
) -> list[tuple[PlanStep, list[PdfFileMetadata]]]:
    """`PlanStep.fileNames` (Saga #286) üzerinden her step'in HANGİ
    dosyalara sahip olduğunu KESİN olarak çözer — artık pozisyonel/sıralı
    bir varsayım YOK. Her `fileNames` girdisinin `pdf_files` içinde
    gerçekten var olduğunu VE `pdf_files`'taki her dosyanın TAM OLARAK
    bir step'e atandığını (ne eksik ne fazla, ne çift atama) doğrular;
    aksi halde tüm plan reddedilir."""
    ordered_steps = sorted(steps, key=lambda step: step.order)
    files_by_name = {file.filename: file for file in pdf_files}

    assigned_names: set[str] = set()
    distributed: list[tuple[PlanStep, list[PdfFileMetadata]]] = []
    for step in ordered_steps:
        step_files: list[PdfFileMetadata] = []
        for name in step.fileNames:
            if name not in files_by_name:
                raise PlanApplicationError(
                    f"Plan step {step.order}, pdf_files listesinde olmayan bir "
                    f"dosyaya atıfta bulunuyor: '{name}'"
                )
            if name in assigned_names:
                raise PlanApplicationError(
                    f"Dosya birden fazla step'e atanmış: '{name}'"
                )
            assigned_names.add(name)
            step_files.append(files_by_name[name])
        distributed.append((step, step_files))

    unassigned = set(files_by_name) - assigned_names
    if unassigned:
        raise PlanApplicationError(
            f"Hiçbir step'e atanmamış dosyalar var: {sorted(unassigned)}"
        )

    return distributed


def apply_plan(
    session: Session,
    plan: PlanSkeleton,
    pdf_files: list[PdfFileMetadata],
    allowed_root: Path,
) -> Transaction:
    """Onaylanmış bir planı TEK transaction içinde gerçekten uygular: hedef
    tarih klasörlerini oluşturur, PDF'leri plan sırasıyla taşır, her adımı
    `FileOperation` olarak kaydeder (Saga #275). Bir adım başarısız olursa
    (Saga #276) o ana kadar tamamlanmış adımlar, kaydedilen
    `FileOperation.destination_path`/`backup_path` alanları kullanılarak
    TERS SIRAYLA eski konumlarına geri taşınır; `PlanApplicationError`
    net bir hata mesajıyla fırlatılır — kısmi başarı asla döndürülmez, her
    `FileOperation`ın nihai durumu (`rolled_back`/`rollback_failed`) DB'ye
    yazılır.

    `OperationType.MOVE`, `OperationType.COPY`, `OperationType.DELETE`,
    `OperationType.RENAME` ve `OperationType.LIST` destekler (Saga
    #288/#289/#290/#291) — `LIST` tamamen salt okunur/inert'tir, hiçbir
    dosya sistemi çağrısı/kaydı yapmaz. Başka bir operationType görürse
    hiçbir dosyaya dokunmadan reddeder."""
    validate_plan_paths(plan, pdf_files, allowed_root)

    for step in plan.steps:
        if step.operationType not in _SUPPORTED_OPERATION_TYPES:
            supported = ", ".join(f"'{op.value}'" for op in _SUPPORTED_OPERATION_TYPES)
            raise PlanApplicationError(
                f"Orchestrator şu an sadece {supported} operasyonlarını "
                f"destekliyor, gelen: '{step.operationType.value}'"
            )

    step_files = _distribute_files_to_steps(pdf_files, plan.steps)

    transaction = create_transaction(session, allowed_root=str(allowed_root))
    session.commit()  # Transaction kaydı, sonuç ne olursa olsun kalıcı olsun.

    applied: list[FileOperation] = []
    try:
        for step, files in step_files:
            # Saga #291: LIST tamamen salt okunur/inert — hiçbir dosya
            # sistemi çağrısı yapılmaz, hiçbir FileOperation kaydı
            # oluşturulmaz (kaydedilecek bir "dosyaya ne oldu" yok,
            # dosyaya HİÇBİR ŞEY olmuyor). Gerçek listeleme zaten
            # `/api/plan` sırasında (discover_pdf_files + PlanCard
            # gösterimi) oluyor — bkz. ATDD.
            if step.operationType == OperationType.LIST:
                continue
            # Saga #304: MERGE de LIST'e benzer bir ÖZEL DURUM ama LIST'in
            # aksine GERÇEKTEN bir dosya sistemi işlemi yapar — mevcut
            # per-dosya forward/rollback dispatch sözleşmesi ("1 kaynak → 1
            # hedef") MERGE'in "N kaynak → 1 hedef" doğasına ZORLA
            # sığdırılamaz (bkz. ATDD S1). Tek bir FileOperation kaydı
            # (N tane değil) oluşturulur.
            if step.operationType == OperationType.MERGE:
                source_paths = [allowed_root / f.filename for f in files]
                destination_path = allowed_root / step.mergedFileName
                operation = record_file_operation(
                    session,
                    transaction,
                    operation_type=step.operationType.value,
                    source_path=";".join(str(p) for p in source_paths),
                    destination_path=str(destination_path),
                    backup_path=str(destination_path),
                )
                _forward_merge(source_paths, destination_path)
                operation.status = "completed"
                session.commit()
                applied.append(operation)
                continue
            # Saga #305: SPLIT MERGE'in tam simetrik tersi - TEK kaynak PDF'i
            # acar, HER sayfa icin AYRI bir cikti dosyasi + AYRI bir
            # FileOperation kaydi olusturur (N kayit toplam, MERGE'in "1
            # kayit" desenin tersine). Cikti adi cakismasi SADECE calisma
            # zamaninda (gercek sayfa sayisi bilindiginde) tespit edilebilir
            # (ATDD S4) - her sayfa YAZILMADAN HEMEN ONCE output_path.exists()
            # kontrol edilir; VARSA PlanApplicationError firlatilir, disaridaki
            # genel except-blogu bu ana kadar YAZILMIS tum sayfalari (applied
            # listesi uzerinden) TERS SIRAYLA geri alir.
            if step.operationType == OperationType.SPLIT:
                from pypdf import PdfReader

                source_path = allowed_root / files[0].filename
                reader = PdfReader(str(source_path))
                if len(reader.pages) == 0:
                    raise PlanApplicationError(
                        f"Bölünecek PDF boş (0 sayfa): '{source_path.name}'"
                    )
                for page_index, page in enumerate(reader.pages):
                    page_number = page_index + 1
                    output_path = allowed_root / f"{source_path.stem}_{page_number}.pdf"
                    if output_path.exists():
                        raise PlanApplicationError(
                            f"SPLIT çıktı dosyası zaten var, işlem reddedildi: '{output_path.name}'"
                        )
                    operation = record_file_operation(
                        session,
                        transaction,
                        operation_type=step.operationType.value,
                        source_path=str(source_path),
                        destination_path=str(output_path),
                        backup_path=str(output_path),
                    )
                    _forward_split_page(page, output_path)
                    operation.status = "completed"
                    session.commit()
                    applied.append(operation)
                continue
            if step.operationType == OperationType.REDACT:
                source_path = allowed_root / files[0].filename
                destination_path = allowed_root / step.redactedFileName
                region = step.redactionRegions[0]
                from pypdf import PdfReader

                reader = PdfReader(str(source_path))
                if region.page > len(reader.pages):
                    raise PlanApplicationError(
                        f"REDACT sayfa numarası ({region.page}) gerçek sayfa sayısını "
                        f"({len(reader.pages)}) aşıyor: '{source_path.name}'"
                    )
                operation = record_file_operation(
                    session,
                    transaction,
                    operation_type=step.operationType.value,
                    source_path=str(source_path),
                    destination_path=str(destination_path),
                    backup_path=str(destination_path),
                )
                _forward_redact(source_path, region.page, step.redactionRegions, destination_path)
                operation.status = "completed"
                session.commit()
                applied.append(operation)
                continue
            if step.operationType == OperationType.EXCEL_SORT:
                source_path = allowed_root / files[0].filename
                destination_path = allowed_root / step.sortedFileName
                operation = record_file_operation(
                    session,
                    transaction,
                    operation_type=step.operationType.value,
                    source_path=str(source_path),
                    destination_path=str(destination_path),
                    backup_path=str(destination_path),
                )
                try:
                    excel_sort.sort_excel_sheet(
                        source_path, step.sortColumn, step.sortAscending, destination_path
                    )
                except excel_sort.ExcelSortFormulaGuardError as exc:
                    raise PlanApplicationError(
                        f"Excel sıralaması reddedildi, veri aralığında formül bulundu: '{source_path.name}' ({exc})"
                    ) from exc
                except ValueError as exc:
                    raise PlanApplicationError(
                        f"Excel sıralama sütunu çözümlenemedi: '{source_path.name}' ({exc})"
                    ) from exc
                operation.status = "completed"
                session.commit()
                applied.append(operation)
                continue
            if step.operationType == OperationType.EXCEL_FILTER:
                source_path = allowed_root / files[0].filename
                destination_path = allowed_root / step.filteredFileName
                operation = record_file_operation(
                    session,
                    transaction,
                    operation_type=step.operationType.value,
                    source_path=str(source_path),
                    destination_path=str(destination_path),
                    backup_path=str(destination_path),
                )
                try:
                    excel_sort.filter_excel_sheet(
                        source_path, step.filterColumn, step.filterValue, destination_path
                    )
                except excel_sort.ExcelFilterFormulaGuardError as exc:
                    raise PlanApplicationError(
                        f"Excel filtresi reddedildi, veri aralığında formül bulundu: '{source_path.name}' ({exc})"
                    ) from exc
                except ValueError as exc:
                    raise PlanApplicationError(
                        f"Excel filtre sütunu çözülemedi: '{source_path.name}' ({exc})"
                    ) from exc
                operation.status = "completed"
                session.commit()
                applied.append(operation)
                continue
            if step.operationType == OperationType.PDF_EXTRACT_PAGES:
                source_path = allowed_root / files[0].filename
                destination_path = allowed_root / step.extractedFileName
                operation = record_file_operation(
                    session,
                    transaction,
                    operation_type=step.operationType.value,
                    source_path=str(source_path),
                    destination_path=str(destination_path),
                    backup_path=str(destination_path),
                )
                try:
                    pdf_pages.extract_pdf_pages(source_path, step.pageSpec, destination_path)
                except ValueError as exc:
                    raise PlanApplicationError(
                        f"PDF sayfa aralığı çözülemedi: '{source_path.name}' ({exc})"
                    ) from exc
                operation.status = "completed"
                session.commit()
                applied.append(operation)
                continue
            if step.operationType == OperationType.PDF_DELETE_PAGES:
                source_path = allowed_root / files[0].filename
                destination_path = allowed_root / step.remainingFileName
                operation = record_file_operation(
                    session,
                    transaction,
                    operation_type=step.operationType.value,
                    source_path=str(source_path),
                    destination_path=str(destination_path),
                    backup_path=str(destination_path),
                )
                try:
                    pdf_pages.delete_pdf_pages(source_path, step.pageSpec, destination_path)
                except ValueError as exc:
                    if "all pages would be deleted" in str(exc):
                        raise PlanApplicationError(
                            f"PDF'in tüm sayfaları silinemez: '{source_path.name}' ({exc})"
                        ) from exc
                    raise PlanApplicationError(
                        f"PDF sayfa aralığı çözülemedi: '{source_path.name}' ({exc})"
                    ) from exc
                operation.status = "completed"
                session.commit()
                applied.append(operation)
                continue
            if step.operationType == OperationType.PDF_COMPRESS:
                # Saga #322: plan.md deseni - compress_pdf() True donerse
                # EXCEL_FILTER blogunun (record+completed+append) kopyasi,
                # False donerse (buyume korumasi) HICBIR FileOperation kaydi
                # olusturulmadan LIST'in izlediği "kayitsiz continue" deseni.
                source_path = allowed_root / files[0].filename
                destination_path = allowed_root / step.compressedFileName
                try:
                    compressed = pdf_compress.compress_pdf(source_path, destination_path)
                except Exception as exc:
                    raise PlanApplicationError(
                        f"PDF sıkıştırılamadı, dosya okunamıyor: '{source_path.name}' ({exc})"
                    ) from exc
                if not compressed:
                    continue
                operation = record_file_operation(
                    session,
                    transaction,
                    operation_type=step.operationType.value,
                    source_path=str(source_path),
                    destination_path=str(destination_path),
                    backup_path=str(destination_path),
                )
                operation.status = "completed"
                session.commit()
                applied.append(operation)
                continue
            if step.operationType == OperationType.EXCEL_CREATE:
                # Saga #326: EXCEL_FILTER'ın deseni ama KAYNAK YOK -
                # source_path fiziksel olarak var olmadığı için
                # record_file_operation'a boş string geçilir (MERGE'in
                # çoklu-kaynak ";".join(...) deseninden farklı, burada
                # gerçekten kaynak YOK).
                destination_path = allowed_root / step.createdFileName
                operation = record_file_operation(
                    session,
                    transaction,
                    operation_type=step.operationType.value,
                    source_path="",
                    destination_path=str(destination_path),
                    backup_path=str(destination_path),
                )
                try:
                    excel_rows.create_excel_file(step.createRows, destination_path)
                except Exception as exc:
                    raise PlanApplicationError(
                        f"EXCEL_CREATE çıktı dosyası oluşturulamadı: '{destination_path.name}' ({exc})"
                    ) from exc
                operation.status = "completed"
                session.commit()
                applied.append(operation)
                continue
            if step.operationType == OperationType.EXCEL_APPEND:
                # Saga #326: PDF `OperationType.APPEND` bloğunun BİREBİR
                # kopyası - EXCEL_APPEND de YERİNDE günceller (destination
                # == source).
                source_path = allowed_root / files[0].filename
                destination_path = source_path
                backup_path = _append_backup_path(allowed_root, transaction.id, files[0].filename)
                operation = record_file_operation(
                    session,
                    transaction,
                    operation_type=step.operationType.value,
                    source_path=str(source_path),
                    destination_path=str(destination_path),
                    backup_path=str(backup_path),
                )
                try:
                    excel_rows.append_excel_rows(source_path, step.appendRows, backup_path)
                except Exception as exc:
                    raise PlanApplicationError(
                        f"EXCEL_APPEND kaynağı okunamıyor: '{source_path.name}' ({exc})"
                    ) from exc
                operation.status = "completed"
                session.commit()
                applied.append(operation)
                continue
            if step.operationType == OperationType.WORD_APPEND_TABLE:
                # Saga #327: EXCEL_APPEND bloğunun BİREBİR kopyası -
                # WORD_APPEND_TABLE de YERİNDE günceller (destination ==
                # source).
                source_path = allowed_root / files[0].filename
                destination_path = source_path
                backup_path = _append_backup_path(allowed_root, transaction.id, files[0].filename)
                operation = record_file_operation(
                    session,
                    transaction,
                    operation_type=step.operationType.value,
                    source_path=str(source_path),
                    destination_path=str(destination_path),
                    backup_path=str(backup_path),
                )
                try:
                    word_table.append_table(source_path, step.tableHeaders, step.tableRows, backup_path)
                except Exception as exc:
                    raise PlanApplicationError(
                        f"WORD_APPEND_TABLE kaynağı okunamıyor: '{source_path.name}' ({exc})"
                    ) from exc
                operation.status = "completed"
                session.commit()
                applied.append(operation)
                continue
            if step.operationType == OperationType.APPEND:
                # Saga #323: APPEND YERINDE gunceller - destination_path ==
                # source_path (MERGE/REDACT/EXCEL_SORT'un aksine, kaynak
                # gercekten degisir). Rollback icin ayrı bir backup_path
                # (gizli klasor) kullanilir; bu, `record_file_operation`in
                # backup_path alanina yazilir - `_rollback_append` bunu
                # okuyup dosyayi eklenmis sayfa oncesi haline dondurur.
                source_path = allowed_root / files[0].filename
                destination_path = source_path
                backup_path = _append_backup_path(allowed_root, transaction.id, files[0].filename)
                operation = record_file_operation(
                    session,
                    transaction,
                    operation_type=step.operationType.value,
                    source_path=str(source_path),
                    destination_path=str(destination_path),
                    backup_path=str(backup_path),
                )
                _forward_append(source_path, step.appendText, backup_path=backup_path)
                operation.status = "completed"
                session.commit()
                applied.append(operation)
                continue
            if step.operationType == OperationType.ZIP_CREATE:
                # Saga #328: MERGE'in "N kaynak -> 1 hedef" deseni.
                source_paths = [allowed_root / f.filename for f in files]
                destination_path = allowed_root / step.zippedFileName
                operation = record_file_operation(
                    session,
                    transaction,
                    operation_type=step.operationType.value,
                    source_path=";".join(str(p) for p in source_paths),
                    destination_path=str(destination_path),
                    backup_path=str(destination_path),
                )
                try:
                    zip_ops.create_zip(source_paths, destination_path)
                except Exception as exc:
                    raise PlanApplicationError(
                        f"ZIP_CREATE kaynağı okunamıyor: '{exc}'"
                    ) from exc
                operation.status = "completed"
                session.commit()
                applied.append(operation)
                continue
            if step.operationType == OperationType.ZIP_ADD:
                # Saga #328: EXCEL_FILTER'in "1 kaynak -> 1 hedef" deseni.
                source_path = allowed_root / files[0].filename
                files_to_add_paths = [allowed_root / name for name in step.filesToAdd]
                destination_path = allowed_root / step.addedFileName
                operation = record_file_operation(
                    session,
                    transaction,
                    operation_type=step.operationType.value,
                    source_path=str(source_path),
                    destination_path=str(destination_path),
                    backup_path=str(destination_path),
                )
                try:
                    zip_ops.add_to_zip(source_path, files_to_add_paths, destination_path)
                except Exception as exc:
                    raise PlanApplicationError(
                        f"ZIP_ADD kaynağı okunamıyor: '{source_path.name}' ({exc})"
                    ) from exc
                operation.status = "completed"
                session.commit()
                applied.append(operation)
                continue
            if step.operationType == OperationType.ZIP_EXTRACT:
                source_path = allowed_root / files[0].filename
                destination_folder = allowed_root / step.destinationFolder
                # Rollback icin gerekli: destinationFolder mkdir'DEN (burada
                # zip_ops.extract_zip'in kendi extractall'i) ONCE var miydi?
                folder_existed_before = destination_folder.exists()
                backup_marker = _zip_extract_backup_marker(
                    destination_folder, folder_existed_before=folder_existed_before
                )
                operation = record_file_operation(
                    session,
                    transaction,
                    operation_type=step.operationType.value,
                    source_path=str(source_path),
                    destination_path=str(destination_folder),
                    backup_path=str(backup_marker),
                )
                try:
                    zip_ops.extract_zip(source_path, destination_folder, allowed_root)
                except PathWhitelistError as exc:
                    raise PlanApplicationError(
                        f"ZIP_EXTRACT reddedildi, güvenli olmayan giriş yolu: '{exc}'"
                    ) from exc
                except Exception as exc:
                    raise PlanApplicationError(
                        f"ZIP_EXTRACT kaynağı okunamıyor: '{source_path.name}' ({exc})"
                    ) from exc
                operation.status = "completed"
                session.commit()
                applied.append(operation)
                continue
            if step.operationType == OperationType.ZIP_MERGE:
                source_paths = [allowed_root / f.filename for f in files]
                destination_path = allowed_root / step.mergedZipFileName
                operation = record_file_operation(
                    session,
                    transaction,
                    operation_type=step.operationType.value,
                    source_path=";".join(str(p) for p in source_paths),
                    destination_path=str(destination_path),
                    backup_path=str(destination_path),
                )
                try:
                    zip_ops.merge_zips(source_paths, destination_path)
                except Exception as exc:
                    raise PlanApplicationError(
                        f"ZIP_MERGE kaynağı okunamıyor: '{exc}'"
                    ) from exc
                operation.status = "completed"
                session.commit()
                applied.append(operation)
                continue
            if step.operationType == OperationType.IMAGE_CROP:
                # Saga #329: EXCEL_FILTER'ın "1 kaynak -> 1 hedef" deseni.
                source_path = allowed_root / files[0].filename
                destination_path = allowed_root / step.croppedFileName
                operation = record_file_operation(
                    session,
                    transaction,
                    operation_type=step.operationType.value,
                    source_path=str(source_path),
                    destination_path=str(destination_path),
                    backup_path=str(destination_path),
                )
                try:
                    image_ops.crop_image(
                        source_path,
                        (step.cropBox.x0, step.cropBox.y0, step.cropBox.x1, step.cropBox.y1),
                        destination_path,
                    )
                except ValueError as exc:
                    raise PlanApplicationError(
                        f"IMAGE_CROP alanı geçersiz: '{source_path.name}' ({exc})"
                    ) from exc
                except Exception as exc:
                    raise PlanApplicationError(
                        f"IMAGE_CROP kaynağı okunamıyor: '{source_path.name}' ({exc})"
                    ) from exc
                operation.status = "completed"
                session.commit()
                applied.append(operation)
                continue
            if step.operationType == OperationType.IMAGE_THUMBNAIL:
                # Saga #329: IMAGE_CROP bloğunun BİREBİR kopyası.
                source_path = allowed_root / files[0].filename
                destination_path = allowed_root / step.thumbnailFileName
                operation = record_file_operation(
                    session,
                    transaction,
                    operation_type=step.operationType.value,
                    source_path=str(source_path),
                    destination_path=str(destination_path),
                    backup_path=str(destination_path),
                )
                try:
                    image_ops.create_thumbnail(
                        source_path, step.maxWidth, step.maxHeight, destination_path
                    )
                except ValueError as exc:
                    raise PlanApplicationError(
                        f"IMAGE_THUMBNAIL boyutu geçersiz: '{source_path.name}' ({exc})"
                    ) from exc
                except Exception as exc:
                    raise PlanApplicationError(
                        f"IMAGE_THUMBNAIL kaynağı okunamıyor: '{source_path.name}' ({exc})"
                    ) from exc
                operation.status = "completed"
                session.commit()
                applied.append(operation)
                continue
            if step.operationType == OperationType.OCR:
                source_path = allowed_root / files[0].filename
                if not is_path_allowed(source_path, allowed_root):
                    raise PlanApplicationError(
                        f"OCR kaynağı izin verilen kök dışında: '{source_path}'"
                    )
                ocr_pdf_file(source_path)
                continue
            # Saga #289/#290: DELETE ve RENAME'in gerçek bir hedef klasörü
            # yok — targetFolder (YYYY-MM) şema gereği hâlâ zorunlu ama
            # ikisinde de kullanılmıyor (bkz. ATDD "bilinen sınırlama").
            # Saga #304: MERGE de aynı şekilde — allowed_root'un KÖK
            # seviyesine yazar, dated bir alt klasör kavramı yok.
            # Sadece MOVE/COPY için gerçek hedef klasör oluşturulur.
            if step.operationType not in (
                OperationType.DELETE,
                OperationType.RENAME,
                OperationType.MERGE,
                OperationType.SPLIT,
                OperationType.REDACT,
                OperationType.EXCEL_SORT,
                OperationType.EXCEL_FILTER,
                OperationType.PDF_EXTRACT_PAGES,
                OperationType.PDF_DELETE_PAGES,
                OperationType.PDF_COMPRESS,
                OperationType.EXCEL_CREATE,
                OperationType.EXCEL_APPEND,
                OperationType.WORD_APPEND_TABLE,
                OperationType.ZIP_CREATE,
                OperationType.ZIP_ADD,
                OperationType.ZIP_EXTRACT,
                OperationType.ZIP_MERGE,
                OperationType.IMAGE_CROP,
                OperationType.IMAGE_THUMBNAIL,
            ):
                target_dir = allowed_root / step.targetFolder
                target_dir.mkdir(parents=True, exist_ok=True)
            # RENAME: fileNames[i] -> newFileNames[i] eşleşmesi (Saga #290).
            new_name_by_old_name = (
                dict(zip(step.fileNames, step.newFileNames))
                if step.operationType == OperationType.RENAME
                else {}
            )
            for pdf_file in files:
                source_path = allowed_root / pdf_file.filename
                if step.operationType == OperationType.DELETE:
                    destination_path = _delete_backup_path(allowed_root, transaction.id, pdf_file.filename)
                    backup_path = source_path
                elif step.operationType == OperationType.RENAME:
                    destination_path = allowed_root / new_name_by_old_name[pdf_file.filename]
                    backup_path = source_path
                else:
                    destination_path = target_dir / pdf_file.filename
                    backup_path = source_path

                operation = record_file_operation(
                    session,
                    transaction,
                    operation_type=step.operationType.value,
                    source_path=str(source_path),
                    destination_path=str(destination_path),
                    backup_path=str(backup_path),
                )
                _FORWARD_OPERATIONS[step.operationType](source_path, destination_path)
                operation.status = "completed"
                session.commit()
                applied.append(operation)
    except Exception as exc:
        # Saga #276: geri alma, bellek-içi bir yardımcı yapı değil, DOĞRUDAN
        # kaydedilmiş `FileOperation.destination_path`/`backup_path`
        # alanlarından okunarak yapılır — tamamlanmış adımlar TERS SIRAYLA
        # (`reversed(applied)`) geri çevrilir. Saga #293: bu döngünün
        # gövdesi artık `revert_transaction`in de kullandığı paylaşılan
        # `_rollback_completed_operations`'a çıkarıldı (kod tekrarı yok) —
        # `allowed_root` burada de geçiriliyor — path'ler bu ÇAĞRININ
        # başında `validate_plan_paths` ile zaten yeni doğrulanmıştı ama
        # yardımcı fonksiyonun imzası artık bunu ZORUNLU kılıyor (Saga
        # #293 red-team önerisi, bkz. `_rollback_completed_operations`
        # docstring'i).
        _rollback_completed_operations(list(reversed(applied)), allowed_root)
        for operation in transaction.operations:
            # Kaydı oluşturulmuş ama shutil.move'un kendisi başarısız olduğu
            # için hiç "completed" olamamış son adım — hiçbir dosya
            # hareketi yapılmadığı için doğrudan rolled_back sayılabilir.
            if operation.status == "pending":
                operation.status = "rolled_back"
        transaction.status = "rolled_back"
        session.commit()
        raise PlanApplicationError(
            f"Plan uygulanamadı, tamamlanmış adımlar geri alındı: {exc}"
        ) from exc

    transaction.status = "committed"
    session.commit()
    return transaction


def recover_incomplete_transactions(session: Session) -> list[Transaction]:
    """Saga #286: `apply_plan` çalışırken süreç çökerse (`shutil.move`
    başarılı olduktan hemen sonra ama `session.commit()`'ten ÖNCE),
    `FileOperation.status` sonsuza dek "pending" asılı kalabilir — dosya
    fiziksel olarak taşınmış olabilir ama DB bunu bilmiyor olabilir. Bu
    fonksiyon `status="pending"` olan tüm `Transaction`'ları tarar ve her
    `FileOperation`'ı GERÇEK dosya sistemi durumuna göre uzlaştırır:
    `destination_path` fiziksel olarak varsa dosya gerçekten taşınmış
    demektir → `"completed"`; yoksa taşıma hiç gerçekleşmemiş/geri
    alınmış demektir → `"rolled_back"` (kaynak zaten olması gereken
    yerde). Tüm operasyonları `"completed"` olan bir transaction
    `"committed"` işaretlenir, aksi halde `"rolled_back"`.

    ÖNEMLİ (red-team bulgusu): transaction'ın kendisi hâlâ `"pending"`
    olduğu sürece, İÇİNDEKİ HER `FileOperation` yeniden doğrulanır —
    sadece kendi durumu `"pending"` olanlar DEĞİL. Gerekçe: `apply_plan`in
    rollback except bloğu bir operasyonu bellek-içi `"completed"`→
    `"rolled_back"`e çevirdikten SONRA ama nihai `session.commit()`'ten
    ÖNCE süreç çökerse, DB'de o operasyon hâlâ `"completed"` görünür —
    ama dosya fiziksel olarak zaten geri taşınmış olabilir. Sadece
    `status=="pending"` olanları kontrol etmek bu operasyonu sonsuza dek
    yanlış etiketli bırakırdı.

    Henüz bir FastAPI startup event'ine BAĞLANMADI (Saga #287'nin devamı
    — gerçek bir apply endpoint'i olmadan bağlanacak bir başlangıç akışı
    yok); bu saf, çağrılabilir bir fonksiyon."""
    pending_transactions = session.scalars(
        select(Transaction).where(Transaction.status == "pending")
    ).all()

    recovered: list[Transaction] = []
    for transaction in pending_transactions:
        all_completed = True
        for operation in transaction.operations:
            if Path(operation.destination_path).exists():
                operation.status = "completed"
            else:
                operation.status = "rolled_back"
                all_completed = False
        if any(operation.status == "rolled_back" for operation in transaction.operations):
            all_completed = False
        transaction.status = "committed" if all_completed else "rolled_back"
        recovered.append(transaction)

    session.commit()
    return recovered


DEFAULT_DELETE_BACKUP_RETENTION_DAYS = 30


def _purge_backup_dir_size_mb(backup_base_dir: Path) -> float:
    """Hesapla backup_base_dir altındaki TÜM dosyaların toplam boyutunu MB cinsinden."""
    total_bytes = 0
    if backup_base_dir.exists():
        for file_path in backup_base_dir.rglob("*"):
            if file_path.is_file():
                total_bytes += file_path.stat().st_size
    return total_bytes / (1024 * 1024)


def _purge_one_transaction_backup(
    session: Session, transaction: Transaction, backup_dir: Path
) -> bool:
    """Saga #302 CAS+rmtree desenini kapsüller: "committed" -> "purging" -> "backup_purged"
    başarılı olursa True döndürür, başarısızsa "purging" -> "committed"e geri döner."""
    if not _claim_transaction_status(
        session, transaction.id, from_status="committed", to_status="purging"
    ):
        # Yarışı kaybettik (ör. `revert_transaction` araya girdi)
        return False
    try:
        shutil.rmtree(backup_dir)
    except OSError:
        # Fiziksel silme başarısız oldu — telafi edici CAS ile satırı "committed"a geri döndür
        _claim_transaction_status(
            session, transaction.id, from_status="purging", to_status="committed"
        )
        return False
    if not _claim_transaction_status(
        session, transaction.id, from_status="purging", to_status="backup_purged"
    ):
        # Teorik olarak imkansız ama savunmacı: devam etmiyoruz
        return False
    transaction.status = "backup_purged"
    return True


def purge_expired_delete_backups(
    session: Session,
    allowed_root: Path,
    *,
    older_than_days: int = DEFAULT_DELETE_BACKUP_RETENTION_DAYS,
    now: dt.datetime | None = None,
) -> list[int]:
    """Saga #300: `_delete_backup_path`in oluşturduğu gizli yedek klasörü
    (`allowed_root/.windows-ai-files-backup/<txn_id>/`) DELETE
    işlemlerinin fiziksel yedeklerini SONSUZA DEK saklıyordu — hiçbir
    temizlik mekanizması yoktu (Saga #289 red-team bulgusu). Bu fonksiyon
    `created_at`i `now - older_than_days`ten ESKİ, `status == "committed"`
    VE TÜM operasyonları DELETE olan ("saf DELETE") transaction'ların
    gizli yedek klasörünü fiziksel olarak siler.

    KRİTİK (kod keşfinde bulunan güvenlik gerekliliği): purge edilen
    transaction `"backup_purged"` YENİ durumuna geçirilir — `"committed"`
    OLARAK BIRAKILMAZ. Aksi halde `revert_transaction`in
    `_rollback_completed_operations`i, artık fiziksel olarak VAR OLMAYAN
    yedek dosyasını "zaten geri alınmış" sanıp SESSİZCE `"rolled_back"`
    işaretlerdi (bkz. o fonksiyonun `destination_path.exists()` kısayolu)
    — kullanıcı "geri aldım" sanır ama dosya GERÇEKTE SONSUZA DEK
    KAYBOLMUŞ olurdu. `"backup_purged"` durumu, `revert_transaction`in
    ZATEN VAR OLAN "sadece committed transaction'lar geri alınabilir"
    guard'ı (Saga #293) tarafından OTOMATİK OLARAK reddedilir — bu
    fonksiyon o guard'a hiçbir yeni kod eklemeden güvenir.

    KARIŞIK operasyonlu (DELETE + başka bir tür) transaction'lar PURGE
    EDİLMEZ — MOVE/COPY/RENAME adımlarının backup_path'i gizli klasör
    DEĞİL, orijinal konumdur; bunları da `"backup_purged"` yapmak hâlâ
    geri alınabilir adımları haksız yere kilitlerdi (dar kapsam kararı,
    bkz. ATDD S3).

    RED-TEAM BULGUSU (HIGH, hemen düzeltildi): `Transaction` tablosunda
    hangi `allowed_root`a ait olduğunu belirten bir kolon YOK (Saga #294/
    #295'teki AYNI dar-kapsam kararı) — bu fonksiyonun DB sorgusu TÜM
    köklerdeki committed transaction'ları döndürür, ama `backup_dir` SADECE
    çağıranın verdiği TEK `allowed_root` altında hesaplanır. Birden fazla
    kök/session kullanan bir kurulumda, BAŞKA bir köke ait bir transaction
    için `backup_dir.exists()` YANLIŞ olur (o kökte hiç yok) — eski kod
    yine de `"backup_purged"` işaretlerdi, bu da hiçbir şey fiziksel olarak
    silinmeden o transaction'ı SONSUZA DEK geri-alınamaz kılardı. Düzeltme:
    `backup_dir.exists()` KONTROLÜ ARTIK ŞARTI — sadece GERÇEKTEN bir şey
    silinen (bu `allowed_root` altında gerçekten var olan) transaction'lar
    `"backup_purged"` olur; başka bir köke ait adaylar DOKUNULMADAN atlanır
    (tekrar deneme fırsatı kalır, hiçbir revertible transaction sessizce
    kilitlenmez).

    Henüz bir zamanlayıcıya/FastAPI startup event'ine BAĞLANMADI
    (`recover_incomplete_transactions` ile AYNI emsal, Saga #286/#287) —
    bu saf, çağrılabilir bir fonksiyon."""
    cutoff = (now or dt.datetime.utcnow()) - dt.timedelta(days=older_than_days)
    candidates = session.scalars(
        select(Transaction).where(Transaction.status == "committed", Transaction.created_at < cutoff)
    ).all()

    purged_ids: list[int] = []
    for transaction in candidates:
        operations = transaction.operations
        if not operations:
            continue
        if not all(operation.operation_type == OperationType.DELETE.value for operation in operations):
            continue
        backup_dir = allowed_root / _DELETE_BACKUP_DIRNAME / str(transaction.id)
        if not backup_dir.exists():
            # Bu `allowed_root` altında hiç yok — ya BAŞKA bir köke ait
            # (çok-kök senaryosu, red-team bulgusu) ya da daha önce zaten
            # temizlenmiş. Her iki durumda da DOKUNMA: durumu değiştirip
            # hâlâ geçerli olabilecek bir transaction'ı YANLIŞLIKLA
            # kilitlemektense hiçbir şey yapmamak daha güvenli.
            continue
        if _purge_one_transaction_backup(session, transaction, backup_dir):
            purged_ids.append(transaction.id)

    session.commit()
    return purged_ids


def purge_oversized_delete_backups(
    session: Session,
    allowed_root: Path,
    *,
    max_total_mb: float = 2000.0,
) -> list[int]:
    """Saga #312: `purge_expired_delete_backups`'a ek olarak bir toplam-boyut
    sınırı: `allowed_root/.windows-ai-files-backup/` altındaki TÜM yedeklerin
    toplam boyutu `max_total_mb` eşiğini (varsayılan 2000 MB) aşarsa, süresi
    henüz dolmamış olsa bile EN ESKİ (created_at artan) saf-DELETE
    `"committed"` transaction'lardan başlayarak, toplam boyut eşiğin ALTINA
    inene kadar veya aday kalmayana kadar purge edilir.

    Mevcut `purge_expired_delete_backups`'ın imzası/davranışı DEĞİŞMEZ — bu
    ayrı, tamamen ek bir fonksiyon. Toplam boyut `max_total_mb`'yi AŞMIYORSA
    fonksiyon hiçbir şey yapmaz, boş liste döner (dosya sistemine hiç
    dokunulmaz).

    Adaylar (status=="committed", TÜM operasyonları DELETE olan, bu
    `allowed_root` altında backup_dir gerçekten var olan) EN ESKİ `created_at`
    ten başlanarak sırayla purge edilir.

    Her purge edilen transaction, `purge_expired_delete_backups` ile AYNI
    güvenlik disiplinini kullanır: `_claim_transaction_status` ile 3 durumlu
    CAS (`committed`→`purging`→`backup_purged`), `rmtree` KİLİT TUTULMADAN
    çağrılır, başarısızlıkta telafi edici geri-dönüş."""
    backup_base_dir = allowed_root / _DELETE_BACKUP_DIRNAME

    # Toplam boyutu hesapla
    total_size_mb = _purge_backup_dir_size_mb(backup_base_dir)
    if total_size_mb <= max_total_mb:
        # Eşik altında — hiçbir şey yapma
        return []

    # Toplam boyutu aşıyor — adayları bul
    candidates = session.scalars(
        select(Transaction).where(Transaction.status == "committed")
    ).all()

    # Adayları filtrele: sadece saf DELETE transaction'ları ve bu allowed_root'ta backup_dir'i olanlar
    purge_candidates: list[tuple[Transaction, Path]] = []
    for transaction in candidates:
        operations = transaction.operations
        if not operations:
            continue
        if not all(operation.operation_type == OperationType.DELETE.value for operation in operations):
            continue
        backup_dir = allowed_root / _DELETE_BACKUP_DIRNAME / str(transaction.id)
        if not backup_dir.exists():
            # Bu `allowed_root` altında hiç yok — atla
            continue
        purge_candidates.append((transaction, backup_dir))

    # Adayları created_at artan (EN ESKİ ilk) sırasıyla sırala
    purge_candidates.sort(key=lambda x: x[0].created_at)

    purged_ids: list[int] = []
    for transaction, backup_dir in purge_candidates:
        # Bu transaction'ı purge et
        if _purge_one_transaction_backup(session, transaction, backup_dir):
            purged_ids.append(transaction.id)

        # Her purge'dan sonra gerçek toplam boyutu yeniden hesapla ve eşiği kontrol et
        total_size_mb = _purge_backup_dir_size_mb(backup_base_dir)
        if total_size_mb <= max_total_mb:
            # Eşik altına indik — durur
            break

    session.commit()
    return purged_ids
