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

        # Saga #338: Merkezi whitelist kontrolü — 11 operasyon için
        # OperationType → hedef-alan-adı eşlemesi (dict-driven).
        dest_field = _DESTINATION_FIELD_BY_OPERATION.get(step.operationType)
        if dest_field is not None:
            dest_value = getattr(step, dest_field, None)
            if dest_value is not None:
                _validate_single_path(allowed_root / dest_value, allowed_root, f"{dest_field} hedefi")

        # RENAME özel durum: hedef alanı 'newFileNames' bir liste, tekil alan değil.
        if step.operationType == OperationType.RENAME:
            for new_name in step.newFileNames or []:
                _validate_single_path(allowed_root / new_name, allowed_root, "Yeniden adlandırma hedefi")

    # Saga #338: Merkezi çakışma kontrolü — tüm 11 operasyon + RENAME için.
    validate_destination_collisions(plan, pdf_files, allowed_root)


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


# Saga #338: OperationType → hedef-alan-adı eşlemesi. 13 operasyon için
# merkezi whitelist + çakışma kontrolü. RENAME ('newFileNames', liste) burada
# YOK — ayrı olarak ele alınıyor. Red-team bulgusunun ardından IMAGE_CROP ve
# IMAGE_THUMBNAIL da dahil edildi (Saga #338 follow-up).
_DESTINATION_FIELD_BY_OPERATION: dict[OperationType, str] = {
    OperationType.MERGE: "mergedFileName",
    OperationType.REDACT: "redactedFileName",
    OperationType.EXCEL_SORT: "sortedFileName",
    OperationType.EXCEL_CREATE: "createdFileName",
    OperationType.EXCEL_FILTER: "filteredFileName",
    OperationType.PDF_EXTRACT_PAGES: "extractedFileName",
    OperationType.PDF_DELETE_PAGES: "remainingFileName",
    OperationType.PDF_COMPRESS: "compressedFileName",
    OperationType.WORD_TO_PDF: "pdfFileName",
    OperationType.ZIP_CREATE: "zippedFileName",
    OperationType.ZIP_ADD: "addedFileName",
    OperationType.ZIP_MERGE: "mergedZipFileName",
    OperationType.IMAGE_CROP: "croppedFileName",
    OperationType.IMAGE_THUMBNAIL: "thumbnailFileName",
}


def validate_destination_collisions(
    plan: PlanSkeleton,
    pdf_files: list[PdfFileMetadata],
    allowed_root: Path,
) -> None:
    """Saga #338: Merkezi "zincirleme hedef çakışması" kontrolü — tüm 11
    operasyon (dict'teki) + RENAME için. Bu fonksiyon mevcut 4 ayrı fonksiyonun
    (`validate_rename_destinations`, `validate_merge_destinations`,
    `validate_redact_destinations`, `validate_excel_sort_destinations`)
    yerini alır.

    Kurallar (mevcut 4 fonksiyondan korunmuştur):
    1. Plan genelinde AYNI normalized isim, birden fazla step'te hedef
       olamaz (ör. step 0 MERGE→'c.pdf', step 1 EXCEL_FILTER→'C.PDF').
    2. Planın bilmediği (pdf_files'ta olmayan) ve `allowed_root`'ta zaten var
       olan bir dosyayla AYNI isimde bir hedef OLAMAZ (kullanıcı verisinin
       sessiz üzerine yazılması).
    3. RENAME için özel: bir step'in hedefi (newFileNames içindeki) başka bir
       step'in kaynağı (fileNames içindeki) olamaz — "zincirleme rename".

    TÜM isim karşılaştırmaları `_normalize_filename` (Windows
    case-insensitive) üzerinden yapılır — `a.pdf`/`A.pdf` AYNI dosya sayılır.

    Zincir tespiti: kendi kendine sadece-harf-büyüklüğü değişikliği
    (a.pdf→A.pdf, AYNI pair) güvenlidir, diğer hiçbir çakışma tolerans edilmez."""
    known_filenames = {_normalize_filename(pdf_file.filename) for pdf_file in pdf_files}

    # Tüm hedef isimleri toplama: (unique_idx, normalized_name)
    all_destinations: list[tuple[int, str]] = []
    destination_descriptions: dict[tuple[int, str], str] = {}

    dest_index_counter = 0

    # Dict'teki 11 operasyon
    for step_idx, step in enumerate(plan.steps):
        dest_field = _DESTINATION_FIELD_BY_OPERATION.get(step.operationType)
        if dest_field is not None:
            dest_value = getattr(step, dest_field, None)
            if dest_value is not None:
                norm_name = _normalize_filename(dest_value)
                all_destinations.append((dest_index_counter, norm_name))
                destination_descriptions[(dest_index_counter, norm_name)] = f"{dest_field} (operationType={step.operationType.value})"

                # Planın bilmediği, zaten var olan dosya çakışması
                if norm_name not in known_filenames:
                    candidate = allowed_root / dest_value
                    if candidate.exists():
                        raise PathWhitelistError(
                            offending_path=str(candidate),
                            allowed_root=str(allowed_root),
                            reason="planın bilmediği, zaten var olan bir dosyayla çakışıyor",
                            description=f"{dest_field} hedefi",
                        )
                dest_index_counter += 1

    # RENAME özel durum: çapraz-step zincir tespiti + hedef çakışması
    rename_pairs: list[tuple[str, str]] = []  # (norm_source, norm_dest)
    rename_pair_indices: list[int] = []  # corresponding unique indices
    rename_destinations_list: list[tuple[int, str]] = []  # all RENAME destinations

    for step_idx, step in enumerate(plan.steps):
        if step.operationType != OperationType.RENAME:
            continue
        for source_name, dest_name in zip(step.fileNames, step.newFileNames or []):
            norm_source = _normalize_filename(source_name)
            norm_dest = _normalize_filename(dest_name)
            rename_pairs.append((norm_source, norm_dest))
            rename_pair_indices.append(dest_index_counter)
            rename_destinations_list.append((dest_index_counter, norm_dest))
            destination_descriptions[(dest_index_counter, norm_dest)] = f"newFileNames (operationType=RENAME)"

            # Planın bilmediği, zaten var olan dosya çakışması
            if norm_dest not in known_filenames:
                candidate = allowed_root / dest_name
                if candidate.exists():
                    raise PathWhitelistError(
                        offending_path=str(candidate),
                        allowed_root=str(allowed_root),
                        reason="planın bilmediği, zaten var olan bir dosyayla çakışıyor",
                        description="Yeniden adlandırma hedefi",
                    )
            dest_index_counter += 1

    # RENAME çapraz-step zincir tespiti: dest_i == source_j ve i != j
    for dest_idx, (_, dest_norm) in enumerate(rename_pairs):
        for source_idx, (source_norm, _) in enumerate(rename_pairs):
            if dest_idx != source_idx and dest_norm == source_norm:
                raise PathWhitelistError(
                    offending_path=dest_norm,
                    allowed_root=str(allowed_root),
                    reason="planda zincirleme yeniden adlandırmaya (bir dosya hem kaynak hem hedef) izin verilmiyor",
                    description="Yeniden adlandırma zinciri",
                )

    # Tüm hedefler (dict'teki 11 operasyon + RENAME) birleştirilir
    all_destinations.extend(rename_destinations_list)

    # Hedef çakışması: aynı norm isim, farklı unique_idx'ler
    for dest_idx, (idx_a, norm_a) in enumerate(all_destinations):
        for src_idx, (idx_b, norm_b) in enumerate(all_destinations):
            # Kendi kendine aynı indexed entry — skip
            if idx_a == idx_b:
                continue
            # Farklı unique index, AYNI normalized isim — HATA
            if norm_a == norm_b:
                raise PathWhitelistError(
                    offending_path=norm_a,
                    allowed_root=str(allowed_root),
                    reason="planda zincirleme hedef çakışmasına (birden fazla step'i aynı hedefi üretemez) izin verilmiyor",
                    description=f"Hedef çakışması: {destination_descriptions.get((idx_a, norm_a), norm_a)} vs {destination_descriptions.get((idx_b, norm_b), norm_b)}",
                )
