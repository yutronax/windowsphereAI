import re
from enum import Enum

from pydantic import BaseModel, field_validator

from backend.request_normalization import normalize_request_text, normalize_selected_folder

# YYYY-MM, ay 01-12 aralığında olmalı (red-team bulgusu, Saga #270: "2026-13"
# gibi geçersiz aylar eskiden bu regex'ten geçiyordu).
TARGET_FOLDER_PATTERN = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


class SessionRequest(BaseModel):
    selectedFolder: str
    requestText: str

    @field_validator("selectedFolder")
    @classmethod
    def normalize_folder(cls, value: str) -> str:
        return normalize_selected_folder(value)

    @field_validator("requestText")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return normalize_request_text(value)


class SessionContext(BaseModel):
    sessionId: str
    selectedFolder: str
    requestText: str


class OperationType(str, Enum):
    MOVE = "Taşı"
    COPY = "Kopyala"
    DELETE = "Sil"
    RENAME = "Yeniden Adlandır"
    LIST = "Listele"


class PlanStep(BaseModel):
    order: int
    operationType: OperationType
    targetFolder: str
    affectedFileCount: int

    @field_validator("order", "affectedFileCount")
    @classmethod
    def non_negative(cls, value: int) -> int:
        if value < 0:
            raise ValueError("must be a non-negative integer")
        return value

    @field_validator("targetFolder")
    @classmethod
    def target_folder_matches_year_month(cls, value: str) -> str:
        if not TARGET_FOLDER_PATTERN.match(value.strip()):
            raise ValueError("must be a YYYY-MM folder name (e.g. '2026-08')")
        return value


class DateSource(str, Enum):
    """Not: `PlanSkeleton.steps` boşsa (taşınacak PDF yoksa),
    `dateSource`/`sortOrder` yine de şema tutarlılığı için gerçek bir enum
    değeri taşır ama HİÇBİR GERÇEK KARARI TEMSİL ETMEZ — `generate_plan_skeleton`
    bu durumda LLM'e hiç istek atmadan varsayılan değerler atar (bkz.
    plan_generation.py). Downstream kod (Security/Orchestrator, Saga #271+)
    bu alanları `steps` boşken anlamlı veri gibi yorumlamamalı (red-team
    bulgusu, Saga #270)."""

    CREATED_AT = "created_at"


class SortOrder(str, Enum):
    ASCENDING = "ascending"
    DESCENDING = "descending"


class PlanSkeleton(BaseModel):
    steps: list[PlanStep]
    dateSource: DateSource
    sortOrder: SortOrder

    @field_validator("steps")
    @classmethod
    def unique_orders(cls, value: list[PlanStep]) -> list[PlanStep]:
        orders = [step.order for step in value]
        if len(orders) != len(set(orders)):
            raise ValueError("step order values must be unique")
        return value


class PdfFileMetadata(BaseModel):
    filename: str
    createdAt: str

    @field_validator("filename", "createdAt")
    @classmethod
    def not_blank(cls, value: str) -> str:
        if value.strip() == "":
            raise ValueError("must not be empty or whitespace-only")
        return value

    @field_validator("filename")
    @classmethod
    def filename_has_no_path_separators(cls, value: str) -> str:
        # Saga #272 red-team bulgusu: path-traversal/derinlik istismarının
        # tek gerçek yüzeyi filename'dir (targetFolder zaten YYYY-MM
        # regex'iyle kilitli) — bunu şema seviyesinde erkenden kapatmak,
        # backend/security.py'deki runtime derinlik kontrolünü gerçek bir
        # defense-in-depth yapar, TEK savunma olmaktan çıkarır.
        if "/" in value or "\\" in value:
            raise ValueError("must not contain path separators")
        return value


class PlanRequest(BaseModel):
    # Saga #285: pdfFiles istemciden ALINMAZ — backend, session'ın
    # selectedFolder'ını kendisi tarar (backend/pdf_discovery.py). İstemcinin
    # dosya listesi göndermesi (a) client'ın PDF içeriğine erişimini
    # gerektirir (Tauri fs plugin, yeni native bağımlılık) ve (b) whitelist
    # doğrulamasının güvendiği "kaynak dosya" listesini istemcinin
    # kontrolüne bırakırdı — backend'in kendi taraması daha az güven
    # sınırı taşır.
    sessionId: str

    @field_validator("sessionId")
    @classmethod
    def session_id_not_blank(cls, value: str) -> str:
        if value.strip() == "":
            raise ValueError("must not be empty or whitespace-only")
        return value
