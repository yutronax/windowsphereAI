import logging
import os
import uuid
from collections.abc import Generator
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession, sessionmaker

from backend.config import load_setup_config
from backend.db import create_db_engine, create_session_factory
from backend.db_models import Transaction
from backend.models import (
    PlanRequest,
    PlanSkeleton,
    RevertTransactionRequest,
    RevertTransactionResponse,
    SessionContext,
    SessionRequest,
    TransactionSummary,
)
from backend.orchestrator import TransactionRevertError, revert_transaction
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


_db_session_factory: sessionmaker[DbSession] | None = None


def _get_db_session_factory() -> sessionmaker[DbSession]:
    # Saga #294 red-team bulgusu: `get_llm_client`'ın "her istekte taze
    # oluştur" deseni burada UYGUN DEĞİL — o desende maliyet sadece bir
    # HTTP istemcisi kurmak, burada ise `create_db_engine`'in HER
    # ÇAĞRISI `Base.metadata.create_all` + `_add_missing_columns` (tam
    # şema introspection/ALTER TABLE taraması) çalıştırıyor. Bu, sık
    # poll'lanabilecek bir "geçmiş" endpoint'i için gereksiz tekrarlanan
    # I/O anlamına gelirdi. Engine/session-factory artık SÜREÇ BAŞINA BİR
    # KEZ (lazy, ilk çağrıda) oluşturulup modül seviyesinde önbelleğe
    # alınıyor — `get_db_session` sadece `factory()`/`yield`/`close()`
    # yapıyor. Testler zaten `get_db_session`'ı `app.dependency_overrides`
    # ile TAMAMEN atlıyor (bkz. test_main_integration.py), bu yüzden bu
    # cache testler arası izolasyonu bozmuyor.
    global _db_session_factory
    if _db_session_factory is None:
        engine = create_db_engine()
        _db_session_factory = create_session_factory(engine)
    return _db_session_factory


def get_db_session() -> Generator[DbSession, None, None]:
    db = _get_db_session_factory()()
    try:
        yield db
    finally:
        db.close()


def _transaction_to_summary(transaction: Transaction) -> TransactionSummary:
    # Saga #283 ilkesiyle tutarlı: tam mutlak path İSTEMCİYE SIZDIRILMAZ,
    # sadece hedef klasörün ADI (`.name`) döner.
    target_folders = sorted({Path(op.destination_path).parent.name for op in transaction.operations})
    return TransactionSummary(
        id=transaction.id,
        createdAt=transaction.created_at,
        status=transaction.status,
        fileCount=len(transaction.operations),
        targetFolders=target_folders,
    )


@app.get("/api/transactions")
def list_transactions(db: DbSession = Depends(get_db_session)) -> list[TransactionSummary]:
    # `created_at.desc()` TEK BAŞINA yeterli değil — hızlı ardışık
    # transaction'lar aynı milisaniyede oluşturulabilir (`dt.datetime.utcnow`
    # çözünürlüğü), bu da eşit zaman damgalarında sıralamayı belirsiz
    # bırakır. `id.desc()` ikincil sıralama anahtarı, eşitlik durumunda bile
    # en son OLUŞTURULANIN (en yüksek id) önce gelmesini GARANTİ eder.
    transactions = db.scalars(
        select(Transaction).order_by(Transaction.created_at.desc(), Transaction.id.desc())
    ).all()
    return [_transaction_to_summary(transaction) for transaction in transactions]


@app.post("/api/transactions/{transaction_id}/revert")
def revert_transaction_endpoint(
    transaction_id: int,
    payload: RevertTransactionRequest,
    db: DbSession = Depends(get_db_session),
) -> RevertTransactionResponse:
    """Saga #295: `revert_transaction`i (Saga #293) gerçek bir HTTP
    endpoint'ine bağlar. `allowed_root`, `Transaction`in kendisinde
    saklanmadığı için (Saga #294 ile aynı dar-kapsam kararı) İSTEMCİDEN
    gelir — istemci zaten kendi session'ının `selectedFolder`'ını bilir.

    Durum önce (ÖNCEDEN, `revert_transaction`i hiç çağırmadan) kontrol
    edilir — bu, "geçersiz istek" (404/409) ile "geçerli istek ama
    fiziksel geri alma başarısız oldu" (200 + `revert_failed`) arasında
    hata mesajı PARSE ETMEDEN net bir ayrım sağlar."""
    transaction = db.get(Transaction, transaction_id)
    if transaction is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction bulunamadı")
    if transaction.status != "committed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Sadece 'committed' durumundaki bir transaction geri alınabilir, mevcut durum: '{transaction.status}'",
        )

    allowed_root = Path(payload.allowedRoot)
    try:
        revert_transaction(db, transaction, allowed_root)
    except TransactionRevertError:
        # Precondition ÖNCEDEN doğrulandığı için buraya düşen TEK olası
        # sebep fiziksel geri almanın kendisinin (kısmen) başarısız
        # olmasıdır — bu bir istemci hatası DEĞİL, gerçek bir operasyon
        # sonucu, bu yüzden 200 ile döner (ResultCard'ın zaten sahip
        # olduğu completed/partial/failed üçlü-durum modeline uyar).
        pass

    return RevertTransactionResponse(transactionId=transaction.id, status=transaction.status)


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
