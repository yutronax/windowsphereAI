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
