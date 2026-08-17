from pydantic import BaseModel, field_validator


class SessionRequest(BaseModel):
    selectedFolder: str
    requestText: str

    @field_validator("selectedFolder", "requestText")
    @classmethod
    def not_blank(cls, value: str) -> str:
        if value.strip() == "":
            raise ValueError("must not be empty or whitespace-only")
        return value


class SessionContext(BaseModel):
    sessionId: str
    selectedFolder: str
    requestText: str
