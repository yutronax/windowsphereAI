import os
import uuid
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from backend.config import load_setup_config
from backend.models import PlanRequest, PlanSkeleton, SessionContext, SessionRequest
from backend.plan_generation import (
    LLMClient,
    OpenAICompatibleLLMClient,
    PlanGenerationError,
    generate_plan_skeleton,
)
from backend.security import PathWhitelistError, validate_plan_paths

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


def get_llm_client() -> LLMClient:
    api_key = os.environ.get("PLAN_LLM_API_KEY")
    if not api_key:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="LLM API anahtarı yapılandırılmamış")
    base_url = os.environ.get("PLAN_LLM_BASE_URL")
    return OpenAICompatibleLLMClient(api_key=api_key, base_url=base_url)


@app.post("/api/plan")
def create_plan(payload: PlanRequest, client: LLMClient = Depends(get_llm_client)) -> PlanSkeleton:
    session = _sessions.get(payload.sessionId)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Oturum bulunamadı")

    try:
        plan = generate_plan_skeleton(payload.pdfFiles, client)
    except PlanGenerationError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    try:
        validate_plan_paths(plan, payload.pdfFiles, Path(session.selectedFolder))
    except PathWhitelistError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    return plan
