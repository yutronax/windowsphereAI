import uuid

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from backend.config import load_setup_config
from backend.models import SessionContext, SessionRequest

app = FastAPI()

_sessions: dict[str, SessionContext] = {}

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "tauri://localhost",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/config")
def get_config() -> dict[str, str]:
    config = load_setup_config()
    if config is None:
        raise HTTPException(status_code=404)
    return config


@app.post("/api/session", status_code=status.HTTP_201_CREATED)
def create_session(payload: SessionRequest) -> SessionContext:
    session = SessionContext(
        sessionId=str(uuid.uuid4()),
        selectedFolder=payload.selectedFolder,
        requestText=payload.requestText,
    )
    _sessions[session.sessionId] = session
    return session
