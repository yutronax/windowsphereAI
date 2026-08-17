from pathlib import Path

from backend.models import PdfFileMetadata, PlanSkeleton


class PathWhitelistError(Exception):
    """Raised when a planned operation's source or target path resolves outside the allowed root."""


def is_path_allowed(path: Path, allowed_root: Path) -> bool:
    resolved_path = path.resolve()
    resolved_root = allowed_root.resolve()
    return resolved_path == resolved_root or resolved_path.is_relative_to(resolved_root)


def validate_plan_paths(
    plan: PlanSkeleton,
    pdf_files: list[PdfFileMetadata],
    allowed_root: Path,
) -> None:
    """Her planlanan taşımanın kaynak dosyasının ve hedef klasörünün
    `allowed_root` altında kaldığını canonical path üzerinden doğrular.
    Whitelist dışındaki tek bir dosya/klasör bile tüm planı reddeder."""
    for pdf_file in pdf_files:
        source_path = allowed_root / pdf_file.filename
        if not is_path_allowed(source_path, allowed_root):
            raise PathWhitelistError(
                f"Kaynak dosya izin verilen kök dışında: {pdf_file.filename}"
            )

    for step in plan.steps:
        target_path = allowed_root / step.targetFolder
        if not is_path_allowed(target_path, allowed_root):
            raise PathWhitelistError(
                f"Hedef klasör izin verilen kök dışında: {step.targetFolder}"
            )
