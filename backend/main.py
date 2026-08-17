import logging
import os
import uuid
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from backend.config import load_setup_config
from backend.models import PlanRequest, PlanSkeleton, SessionContext, SessionRequest
from backend.pdf_discovery import discover_pdf_files
from backend.plan_generation import (
    LLMClient,
    OpenAICompatibleLLMClient,
    PlanGenerationError,
    generate_plan_skeleton,
)
from backend.security import PathWhitelistError, validate_plan_paths

logger = logging.getLogger(__name__)

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


def get_session_or_404(payload: PlanRequest) -> SessionContext:
    """Saga #283: dosya-dokunan HER endpoint'in tekrar tekrar yazması
    gerekmeyen, yeniden kullanılabilir bir session-lookup dependency'si —
    `/api/plan` şu an TEK kullanıcısı, ama gelecekte eklenecek bir
    apply/execute endpoint'i de aynı `Depends(get_session_or_404)`'u
    kullanabilir."""
    session = _sessions.get(payload.sessionId)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Oturum bulunamadı")
    return session


@app.post("/api/plan")
def create_plan(
    session: SessionContext = Depends(get_session_or_404),
    client: LLMClient = Depends(get_llm_client),
) -> PlanSkeleton:
    allowed_root = Path(session.selectedFolder)
    if not allowed_root.is_dir():
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Seçili klasör artık mevcut değil",
        )
    pdf_files = discover_pdf_files(allowed_root)

    try:
        plan = generate_plan_skeleton(pdf_files, client, request_text=session.requestText)
    except PlanGenerationError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    try:
        validate_plan_paths(plan, pdf_files, allowed_root)
    except PathWhitelistError as exc:
        # Saga #283: tam mutlak path (`exc.offending_path`/`exc.allowed_root`)
        # istemciye SIZDIRILMAZ (red-team bulgusu: bu, sunucunun dosya
        # sistemi yapısı hakkında keşif bilgisi verirdi) — sadece kısa
        # `reason` (ör. "izin verilen kök dışında") 403 detail'e konur, tam
        # path'ler sadece sunucu logunda kalır.
        logger.warning(
            "Whitelist ihlali: %s %s (allowed_root=%s)",
            exc.description,
            exc.offending_path,
            exc.allowed_root,
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"{exc.description} {exc.reason}") from exc

    return plan
