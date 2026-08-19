import logging
import os
from pathlib import Path

from backend.models import OperationType, PdfFileMetadata, PlanSkeleton

logger = logging.getLogger(__name__)

# Red-team bulgusu (Saga #272): bu değişkenlerden biri prod'da (gerçek
# Windows) eksikse `_system_protected_roots()` sessizce eksik döner ve
# is_system_protected o kök için sessizce hep False olur — "güvenlik
# kapalı" durumu loglanmazsa fark edilmez. `_warn_if_protected_roots_missing`
# bunu en az bir kez WARNING seviyesinde loglar.
_EXPECTED_PROTECTED_ROOT_ENV_VARS = ("WINDIR", "ProgramFiles", "ProgramData")
_missing_roots_warned = False

# allowed_root altında izin verilen azami alt klasör derinliği (ör. derinlik
# 3: allowed_root/a/b/c/dosya.pdf kabul edilir, allowed_root/a/b/c/d/dosya.pdf
# reddedilir). Saga #272: "aşırı iç içe klasör hedefleri" reddi.
MAX_PATH_DEPTH = 3


def _system_protected_roots() -> list[Path]:
    """Windows'un kendi sistem köklerinin KESİN mutlak yolları (ortam
    değişkenlerinden). Segment-adı eşleştirmesi (ör. yolun herhangi bir
    yerinde "appdata" geçiyor mu) KASITLI OLARAK kullanılmıyor —
    `allowed_root`'un kendisi meşru biçimde bu isimlerden birini içeren bir
    yol altında olabilir (ör. taşınabilir kurulum, test ortamının geçici
    dizini `%LOCALAPPDATA%\\Temp` altında yer alır); bu yüzden sadece
    kullanıcı verisi TAŞIMAYAN, tamamen işletim sistemine/uygulamalara ait
    kesin kök dizinlerin ALTINDA olmak reddi tetikler. `%APPDATA%` /
    `%LOCALAPPDATA%` kasıtlı olarak listede DEĞİL — kullanıcı verisi de
    barındırabilirler, whitelist kökü (`is_path_allowed`) zaten bunların
    dışına çıkışı engelliyor."""
    env_roots = [
        os.environ.get("WINDIR"),
        os.environ.get("ProgramFiles"),
        os.environ.get("ProgramFiles(x86)"),
        os.environ.get("ProgramW6432"),
        os.environ.get("ProgramData"),
        os.environ.get("SystemDrive", "C:") + r"\$Recycle.Bin",
    ]
    return [Path(root) for root in env_roots if root]


def _warn_if_protected_roots_missing() -> None:
    global _missing_roots_warned
    if _missing_roots_warned:
        return

    missing = [name for name in _EXPECTED_PROTECTED_ROOT_ENV_VARS if not os.environ.get(name)]
    if missing:
        logger.warning(
            "Security Gate: sistem-korunan kök ortam değişkenleri eksik (%s) — "
            "is_system_protected bu kökler için hiçbir korumadan geçemiyor. "
            "Bu, whitelist DIŞINDA bağımsız bir savunma katmanının sessizce "
            "devre dışı kaldığı anlamına gelir.",
            ", ".join(missing),
        )
    _missing_roots_warned = True


class PathWhitelistError(Exception):
    """Raised when a planned operation's source or target path resolves
    outside the allowed root, hits a system-protected root, or exceeds the
    max depth. Carries structured fields (Saga #283) so a caller (ör.
    backend/main.py) can decide INDEPENDENTLY how much detail to expose to
    the client — `str(exc)` hâlâ eski okunabilir mesaj formatını üretir,
    geriye dönük uyumluluk için."""

    def __init__(self, *, offending_path: str, allowed_root: str, reason: str, description: str) -> None:
        self.offending_path = offending_path
        self.allowed_root = allowed_root
        self.reason = reason
        self.description = description
        super().__init__(f"{description} {reason}: {offending_path}")


def is_path_allowed(path: Path, allowed_root: Path) -> bool:
    resolved_path = path.resolve()
    resolved_root = allowed_root.resolve()
    return resolved_path == resolved_root or resolved_path.is_relative_to(resolved_root)


def is_path_too_deep(path: Path, allowed_root: Path, max_depth: int = MAX_PATH_DEPTH) -> bool:
    """`path`, `allowed_root`'a göre `max_depth`'ten daha fazla alt klasör
    içeriyorsa True döner. `path`in `allowed_root` altında olduğu varsayılır
    (çağırmadan önce `is_path_allowed` ile doğrulanmalı)."""
    resolved_path = path.resolve()
    resolved_root = allowed_root.resolve()
    relative_parts = resolved_path.relative_to(resolved_root).parts
    return len(relative_parts) > max_depth


def is_system_protected(path: Path) -> bool:
    _warn_if_protected_roots_missing()
    resolved_path = path.resolve()
    return any(is_path_allowed(resolved_path, root) for root in _system_protected_roots())


def _validate_single_path(path: Path, allowed_root: Path, description: str) -> None:
    if not is_path_allowed(path, allowed_root):
        raise PathWhitelistError(
            offending_path=str(path),
            allowed_root=str(allowed_root),
            reason="izin verilen kök dışında",
            description=description,
        )
    if is_system_protected(path):
        raise PathWhitelistError(
            offending_path=str(path),
            allowed_root=str(allowed_root),
            reason="korunan bir sistem klasörüne değiyor",
            description=description,
        )
    if is_path_too_deep(path, allowed_root):
        raise PathWhitelistError(
            offending_path=str(path),
            allowed_root=str(allowed_root),
            reason="izin verilen azami derinliği aşıyor",
            description=description,
        )


def validate_plan_paths(
    plan: PlanSkeleton,
    pdf_files: list[PdfFileMetadata],
    allowed_root: Path,
) -> None:
    """Her planlanan taşımanın kaynak dosyasının ve hedef klasörünün
    `allowed_root` altında, sistem klasörlerinden uzak ve azami derinlik
    sınırı içinde kaldığını canonical path üzerinden doğrular. Bu
    kurallardan herhangi birini ihlal eden tek bir dosya/klasör bile tüm
    planı reddeder — hiçbir adım kısmen kabul edilmez."""
    for pdf_file in pdf_files:
        _validate_single_path(allowed_root / pdf_file.filename, allowed_root, "Kaynak dosya")

    for step in plan.steps:
        _validate_single_path(allowed_root / step.targetFolder, allowed_root, "Hedef klasör")
        if step.operationType == OperationType.MERGE:
            _validate_single_path(allowed_root / step.mergedFileName, allowed_root, "Birleştirme hedefi")
        if step.operationType == OperationType.REDACT:
            _validate_single_path(allowed_root / step.redactedFileName, allowed_root, "Karartma hedefi")
        if step.operationType == OperationType.EXCEL_SORT:
            _validate_single_path(allowed_root / step.sortedFileName, allowed_root, "Sıralama hedefi")
        if step.operationType == OperationType.EXCEL_CREATE:
            # Saga #326: EXCEL_CREATE kaynaksız (fileNames boş) - genel
            # pdf_files döngüsü hedefi hiç göremez, bu yüzden
            # EXCEL_SORT/REDACT ile AYNI desende ayrıca doğrulanır.
            _validate_single_path(allowed_root / step.createdFileName, allowed_root, "Excel oluşturma hedefi")

    validate_rename_destinations(plan, pdf_files, allowed_root)
    validate_merge_destinations(plan, pdf_files, allowed_root)
    validate_redact_destinations(plan, pdf_files, allowed_root)
    validate_excel_sort_destinations(plan, pdf_files, allowed_root)


def _normalize_filename(name: str) -> str:
    # 3. red-team turu bulgusu (deneysel doğrulandı, HIGH): proje
    # Windows-only hedefliyor (bkz. pdf_discovery.py'nin st_ctime notu) —
    # Windows dosya sistemi CASE-INSENSITIVE'dir ("b.pdf" ve "B.PDF" AYNI
    # dosyadır), ama Python `set`/`==` karşılaştırması case-SENSITIVE'dir.
    # `os.path.normcase` Windows'ta küçük harfe çevirir (POSIX'te no-op) —
    # bu fonksiyonun kullanılmadığı HER isim karşılaştırması, bir
    # zincirleme rename'in sadece harf büyüklüğü farkıyla (ör.
    # `a.pdf`→`B.PDF`, sonra `b.pdf`→`c.pdf`) fark edilmeden geçmesine
    # yol açabilir — round 1/2'deki AYNI veri kaybı sınıfı.
    return os.path.normcase(name)


def validate_rename_destinations(
    plan: PlanSkeleton,
    pdf_files: list[PdfFileMetadata],
    allowed_root: Path,
) -> None:
    """Saga #290 red-team bulgusu (deneysel doğrulandı, HIGH severity):
    `shutil.move`, hedefte ZATEN VAR OLAN bir dosyayı hiçbir hata
    vermeden SESSİZCE üzerine yazar. `PlanStep.newFileNames` şema
    seviyesinde kendi içinde tutarlı olsa bile (tekil, fileNames ile
    çakışmıyor), planın HİÇ dokunmadığı, `allowed_root`'ta ZATEN VAR
    OLAN bir dosyayla (ör. kullanıcının önemli bir dosyasıyla) çakışabilir
    — bu, Pydantic'in göremeyeceği bir dosya sistemi gerçeğidir, bu
    yüzden ayrı bir runtime kontrolü olarak burada yapılır.
    `pdf_files`'taki (planın bildiği/dokunabileceği) isimlerden biriyse
    çakışma İZİN VERİLİR (o dosya zaten planın bir parçası); aksi halde
    tüm plan reddedilir.

    İKİNCİ KONTROL (2. red-team turu, deneysel doğrulandı, HIGH): tek bir
    step İÇİNDE `newFileNames`/`fileNames` çakışması `models.py`'de
    şema seviyesinde zaten yasak — ama PLAN GENELİNDE FARKLI step'ler
    arasında hâlâ bir "zincirleme rename" mümkündü: step 0
    `a.pdf`→`b.pdf`, step 1 `b.pdf`→`c.pdf` — `b.pdf` step 0'ın hedefi,
    step 1'in kaynağı. `apply_plan` bunu SIRAYLA uyguladığında, step 0
    `b.pdf`yi (varsa) SESSİZCE üzerine yazar (`shutil.move` semantiği),
    ORİJİNAL `b.pdf`'in içeriği hiçbir yerde kalmadan kaybolur — SIRA
    ÖNEMLİ DEĞİL, herhangi bir isim planda hem bir RENAME kaynağı hem
    bir RENAME hedefi olamaz.

    TÜM isim karşılaştırmaları `_normalize_filename` (Windows
    case-insensitive) üzerinden yapılır (3. red-team turu, deneysel
    doğrulandı, HIGH) — hem çakışma/zincir tespiti hem "planın bildiği
    dosya" muafiyeti bu sayede `a.pdf`/`A.pdf` gibi sadece harf büyüklüğü
    farklı adları AYNI dosya olarak doğru tanır.

    Zincir tespiti ÇİFT-bazlıdır (kaynak, hedef) — SADECE aynı dosyanın
    KENDİ çiftinin dışındaki bir çiftin kaynağıyla çakışırsa reddedilir.
    Bu, `a.pdf`→`A.pdf` gibi kendi kendine sadece-harf-büyüklüğü
    rename'inin (tek çift, başka hiçbir çiftle ilişkisi yok) yanlışlıkla
    "zincir" sayılıp reddedilmesini ÖNLER — ilk saf küme-kesişimi
    yaklaşımı bunu hatalı biçimde reddediyordu (3. red-team turu
    bulgusu)."""
    rename_pairs: list[tuple[str, str]] = []
    for step in plan.steps:
        if step.operationType != OperationType.RENAME:
            continue
        for source_name, dest_name in zip(step.fileNames, step.newFileNames or []):
            rename_pairs.append((_normalize_filename(source_name), _normalize_filename(dest_name)))

    for dest_index, (_, dest_norm) in enumerate(rename_pairs):
        for source_index, (source_norm, _) in enumerate(rename_pairs):
            if dest_index != source_index and dest_norm == source_norm:
                raise PathWhitelistError(
                    offending_path=dest_norm,
                    allowed_root=str(allowed_root),
                    reason="planda zincirleme yeniden adlandırmaya (bir dosya hem kaynak hem hedef) izin verilmiyor",
                    description="Yeniden adlandırma zinciri",
                )

    known_filenames = {_normalize_filename(pdf_file.filename) for pdf_file in pdf_files}
    for step in plan.steps:
        if step.operationType != OperationType.RENAME:
            continue
        for new_name in step.newFileNames or []:
            if _normalize_filename(new_name) in known_filenames:
                continue
            candidate = allowed_root / new_name
            if candidate.exists():
                raise PathWhitelistError(
                    offending_path=str(candidate),
                    allowed_root=str(allowed_root),
                    reason="planın bilmediği, zaten var olan bir dosyayla çakışıyor",
                    description="Yeniden adlandırma hedefi",
                )


def validate_merge_destinations(
    plan: PlanSkeleton,
    pdf_files: list[PdfFileMetadata],
    allowed_root: Path,
) -> None:
    """Saga #304: `validate_rename_destinations`iyle (Saga #290) BİREBİR
    aynı ilkeler, `mergedFileName` için — (a) planın bilmediği zaten var
    olan bir dosyayla çakışamaz (`pdf_files`'taki bilinen isimlerden biriyse
    izin verilir), (b) plan genelinde birden fazla MERGE/RENAME step'i AYNI
    hedefi üretemez (zincirleme çakışma) — RENAME'in kendi hedefleriyle de
    (`validate_rename_destinations`'ın topladığı `rename_pairs` ile AYNI
    fikirdeki) çakışma dahil, çünkü ikisi de `apply_plan`'da SIRAYLA aynı
    `allowed_root` altına yazıyor. Tüm karşılaştırmalar `_normalize_filename`
    (Windows case-insensitive) üzerinden yapılır."""
    merge_destinations: list[str] = [
        _normalize_filename(step.mergedFileName)
        for step in plan.steps
        if step.operationType == OperationType.MERGE
    ]
    rename_destinations: list[str] = [
        _normalize_filename(dest_name)
        for step in plan.steps
        if step.operationType == OperationType.RENAME
        for dest_name in (step.newFileNames or [])
    ]
    all_destinations = merge_destinations + rename_destinations

    for dest_index, dest_norm in enumerate(merge_destinations):
        for other_index, other_norm in enumerate(all_destinations):
            if other_index != dest_index and dest_norm == other_norm:
                raise PathWhitelistError(
                    offending_path=dest_norm,
                    allowed_root=str(allowed_root),
                    reason="planda zincirleme hedef çakışmasına (birden fazla MERGE/RENAME step'i aynı hedefi üretemez) izin verilmiyor",
                    description="Birleştirme hedefi",
                )

    known_filenames = {_normalize_filename(pdf_file.filename) for pdf_file in pdf_files}
    for step in plan.steps:
        if step.operationType != OperationType.MERGE:
            continue
        merged_name = step.mergedFileName
        if _normalize_filename(merged_name) in known_filenames:
            continue
        candidate = allowed_root / merged_name
        if candidate.exists():
            raise PathWhitelistError(
                offending_path=str(candidate),
                allowed_root=str(allowed_root),
                reason="planın bilmediği, zaten var olan bir dosyayla çakışıyor",
                description="Birleştirme hedefi",
            )


def validate_redact_destinations(
    plan: PlanSkeleton,
    pdf_files: list[PdfFileMetadata],
    allowed_root: Path,
) -> None:
    """Saga #320: `validate_merge_destinations` ile BİREBİR aynı ilkeler,
    `redactedFileName` için - (a) planın bilmediği zaten var olan bir
    dosyayla çakışamaz, (b) plan genelinde birden fazla MERGE/RENAME/REDACT
    step'i AYNI hedefi üretemez (zincirleme çakışma). Tüm karşılaştırmalar
    `_normalize_filename` (Windows case-insensitive) üzerinden yapılır."""
    redact_destinations: list[str] = [
        _normalize_filename(step.redactedFileName)
        for step in plan.steps
        if step.operationType == OperationType.REDACT
    ]
    merge_destinations: list[str] = [
        _normalize_filename(step.mergedFileName)
        for step in plan.steps
        if step.operationType == OperationType.MERGE
    ]
    rename_destinations: list[str] = [
        _normalize_filename(dest_name)
        for step in plan.steps
        if step.operationType == OperationType.RENAME
        for dest_name in (step.newFileNames or [])
    ]
    all_destinations = redact_destinations + merge_destinations + rename_destinations

    for dest_index, dest_norm in enumerate(redact_destinations):
        for other_index, other_norm in enumerate(all_destinations):
            if other_index != dest_index and dest_norm == other_norm:
                raise PathWhitelistError(
                    offending_path=dest_norm,
                    allowed_root=str(allowed_root),
                    reason="planda zincirleme hedef çakışmasına (birden fazla MERGE/RENAME/REDACT step'i aynı hedefi üretemez) izin verilmiyor",
                    description="Karartma hedefi",
                )

    known_filenames = {_normalize_filename(pdf_file.filename) for pdf_file in pdf_files}
    for step in plan.steps:
        if step.operationType != OperationType.REDACT:
            continue
        redacted_name = step.redactedFileName
        if _normalize_filename(redacted_name) in known_filenames:
            continue
        candidate = allowed_root / redacted_name
        if candidate.exists():
            raise PathWhitelistError(
                offending_path=str(candidate),
                allowed_root=str(allowed_root),
                reason="planın bilmediği, zaten var olan bir dosyayla çakışıyor",
                description="Karartma hedefi",
            )


def validate_excel_sort_destinations(
    plan: PlanSkeleton,
    pdf_files: list[PdfFileMetadata],
    allowed_root: Path,
) -> None:
    """Saga #324: `validate_redact_destinations` ile BİREBİR aynı iskelet,
    `sortedFileName` için - (a) planın bilmediği zaten var olan bir
    dosyayla çakışamaz, (b) plan genelinde birden fazla MERGE/RENAME/REDACT/
    EXCEL_SORT step'i AYNI hedefi üretemez (zincirleme çakışma). Tüm
    karşılaştırmalar `_normalize_filename` (Windows case-insensitive)
    üzerinden yapılır."""
    excel_sort_destinations: list[str] = [
        _normalize_filename(step.sortedFileName)
        for step in plan.steps
        if step.operationType == OperationType.EXCEL_SORT
    ]
    redact_destinations: list[str] = [
        _normalize_filename(step.redactedFileName)
        for step in plan.steps
        if step.operationType == OperationType.REDACT
    ]
    merge_destinations: list[str] = [
        _normalize_filename(step.mergedFileName)
        for step in plan.steps
        if step.operationType == OperationType.MERGE
    ]
    rename_destinations: list[str] = [
        _normalize_filename(dest_name)
        for step in plan.steps
        if step.operationType == OperationType.RENAME
        for dest_name in (step.newFileNames or [])
    ]
    all_destinations = excel_sort_destinations + redact_destinations + merge_destinations + rename_destinations

    for dest_index, dest_norm in enumerate(excel_sort_destinations):
        for other_index, other_norm in enumerate(all_destinations):
            if other_index != dest_index and dest_norm == other_norm:
                raise PathWhitelistError(
                    offending_path=dest_norm,
                    allowed_root=str(allowed_root),
                    reason="planda zincirleme hedef çakışmasına (birden fazla MERGE/RENAME/REDACT/EXCEL_SORT step'i aynı hedefi üretemez) izin verilmiyor",
                    description="Sıralama hedefi",
                )

    known_filenames = {_normalize_filename(pdf_file.filename) for pdf_file in pdf_files}
    for step in plan.steps:
        if step.operationType != OperationType.EXCEL_SORT:
            continue
        sorted_name = step.sortedFileName
        if _normalize_filename(sorted_name) in known_filenames:
            continue
        candidate = allowed_root / sorted_name
        if candidate.exists():
            raise PathWhitelistError(
                offending_path=str(candidate),
                allowed_root=str(allowed_root),
                reason="planın bilmediği, zaten var olan bir dosyayla çakışıyor",
                description="Sıralama hedefi",
            )
