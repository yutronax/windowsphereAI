import logging
import os
from pathlib import Path

from backend.models import PdfFileMetadata, PlanSkeleton

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
