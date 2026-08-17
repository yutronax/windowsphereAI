from enum import Enum

from pydantic import BaseModel, field_validator

from backend.request_normalization import normalize_request_text, normalize_selected_folder


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
    def target_folder_not_blank(cls, value: str) -> str:
        if value.strip() == "":
            raise ValueError("must not be empty or whitespace-only")
        return value


class PlanSkeleton(BaseModel):
    steps: list[PlanStep]

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


class PlanRequest(BaseModel):
    sessionId: str
    pdfFiles: list[PdfFileMetadata]

    @field_validator("sessionId")
    @classmethod
    def session_id_not_blank(cls, value: str) -> str:
        if value.strip() == "":
            raise ValueError("must not be empty or whitespace-only")
        return value
