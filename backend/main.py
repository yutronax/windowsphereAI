import dataclasses
import datetime as dt
import logging
import os
import re
import threading
import time
import uuid
from collections.abc import Generator
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession, sessionmaker

from backend.config import load_setup_config
from backend.db import create_db_engine, create_session_factory
from backend.db_models import Transaction
from backend.file_search import search_files
from backend.models import (
    AppliedFileOperation,
    ApplyPlanRequest,
    OperationType,
    PlanRequest,
    PlanSkeleton,
    RevertTransactionRequest,
    RevertTransactionResponse,
    ScanStartResponse,
    ScanStatusResponse,
    SearchRequest,
    SearchResponse,
    SessionContext,
    SessionRequest,
    TransactionApplyResponse,
    TransactionSummary,
)
from backend.orchestrator import (
    PlanApplicationError,
    TransactionRevertError,
    apply_plan,
    revert_transaction,
)
# Saga #309 red-team fix: `_distribute_files_to_steps` özel (underscore) bir
# fonksiyon ama transaction-sayısı-diff yarışını (race) ortadan kaldırmak için
# orchestrator.py'ye dokunmadan buradan doğrudan çağrılıyor (bkz.
# apply_plan_endpoint içindeki ön-kontrol yorumu) — bu, incelenmiş/onaylanmış
# minimal düzeltmedir.
from backend.orchestrator import _distribute_files_to_steps
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


@dataclasses.dataclass
class ScanState:
    """Saga #337: bellek-içi tarama durumu. `_scans`'ın değeri — hem başlangıç
    thread'i hem de status-poll eden istek thread'i tarafından okunur/yazılır,
    bu yüzden HER erişim `_scans_lock` altında yapılmalı."""

    status: str  # "running" | "done"
    scanned_count: int = 0
    results: list | None = None
    partial: bool | None = None
    completed_at: float | None = None


_scans: dict[str, ScanState] = {}
_scans_lock = threading.Lock()

# Saga #337 plan.md: ayrı bir zamanlanmış temizlik görevi YERİNE, her
# GET /api/search/scan/{scan_id} çağrısında 5 dakikadan eski VE "done"
# durumundaki kayıtlar "lazy" olarak silinir.
_SCAN_TTL_SECONDS = 300


def _cleanup_expired_scans() -> None:
    """`_scans_lock` ZATEN TUTULUYORKEN çağrılmalı (caller sorumluluğu)."""
    now = time.monotonic()
    expired_ids = [
        scan_id
        for scan_id, state in _scans.items()
        if state.status == "done"
        and state.completed_at is not None
        and (now - state.completed_at) > _SCAN_TTL_SECONDS
    ]
    for scan_id in expired_ids:
        del _scans[scan_id]


def _run_scan(
    scan_id: str,
    allowed_root: Path,
    *,
    name_contains: str | None,
    extension: str | None,
    modified_after: dt.datetime | None,
    modified_before: dt.datetime | None,
    content_contains: str | None,
) -> None:
    """Arka plan thread'inde çalışır — `search_files`'ı çağırır ve sonucu
    `_scans[scan_id]`'e yazar (AC-1: `POST /api/search/scan` bunu BEKLEMEZ).

    Red-team bulgusu (artifacts/dosya-arama-ilerleme-gostergesi/red_team.json,
    medium severity): `search_files()` beklenmedik bir exception fırlatırsa
    (ör. OSError), thread sessizce ölür ve `ScanState.status` sonsuza kadar
    "running" kalırdı — bu hem atdd.md'nin "asla running'de takılı kalmaz"
    garantisini ihlal eder hem de `_cleanup_expired_scans()` sadece
    status=="done" kayıtları hedeflediği için TTL temizliği hiç devreye
    girmez (kalıcı bellek sızıntısı). Bu yüzden `search_files` çağrısı
    try/except ile sarılır: hata durumunda kayıt "done" + partial=True
    olarak işaretlenir (client polling'i sonsuza kadar beklemez, TTL
    temizliği de artık bu kaydı normal şekilde süpürebilir) ve hata
    sessizce yutulmaz, loglanır."""
    try:
        results, partial = search_files(
            allowed_root,
            name_contains=name_contains,
            extension=extension,
            modified_after=modified_after,
            modified_before=modified_before,
            content_contains=content_contains,
            return_partial=True,
        )
    except Exception:
        logger.exception("Arka plan tarama basarisiz oldu (scan_id=%s)", scan_id)
        with _scans_lock:
            state = _scans.get(scan_id)
            if state is None:
                return
            state.status = "done"
            state.scanned_count = 0
            state.results = []
            state.partial = True
            state.completed_at = time.monotonic()
        return

    with _scans_lock:
        state = _scans.get(scan_id)
        if state is None:
            # Kayıt taşındıktan sonra (ör. çok agresif bir temizlik) buraya
            # düşülürse sessizce yok say — kimsenin poll edecek referansı yok.
            return
        state.status = "done"
        state.scanned_count = len(results)
        state.results = results
        state.partial = partial
        state.completed_at = time.monotonic()

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
    endpoint'ine bağlar. Saga #301: `allowed_root` artık `Transaction`in
    kendisinde server tarafında saklanır (apply_plan sırasında kaydedilir)
    — İSTEMCİDEN GELMEZ (eski Saga #294/#295 kararı bir spoofing açığıydı).

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
    if transaction.allowed_root is None:
        # Saga #301 red-team bulgusu: bu, Saga #301 öncesi (migration
        # shim'inin NULL bıraktığı eski) bir transaction'dır — fiziksel
        # geri alma denemeden ÖNCE ayrı bir 409 ile reddedilir, aksi
        # halde `revert_transaction`in fırlattığı `TransactionRevertError`
        # aşağıdaki genel except bloğuna düşüp durumu HİÇ DEĞİŞTİRMEDEN
        # (hâlâ "committed") 200 dönerdi — bu, gerçek bir fiziksel geri
        # alma başarısızlığıyla (200 + "revert_failed") KARIŞTIRILAMAZ bir
        # veri-bütünlüğü hatasıdır, ayrı ve net bir sinyal gerektirir.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bu transaction için allowed_root kaydı eksik, geri alınamıyor.",
        )

    try:
        revert_transaction(db, transaction)
    except TransactionRevertError:
        # Saga #302 red-team bulgusu: precondition ÖNCEDEN doğrulanmış olsa
        # da, artık buraya düşmenin İKİ farklı sebebi olabilir: (a) fiziksel
        # geri almanın kendisi (kısmen) başarısız oldu (mevcut davranış,
        # `transaction.status` zaten DB'yle senkron: "revert_failed") YA DA
        # (b) `revert_transaction`in atomik claim'i YARIŞI KAYBETTİ (ör.
        # `purge_expired_delete_backups` araya girdi) — bu durumda
        # bellekteki `transaction.status` HÂLÂ claim öncesi eski değeri
        # taşır ("committed"), oysa DB'deki gerçek değer başka bir işlemin
        # yazdığı değerdir (ör. "backup_purged"). `db.refresh` ile
        # nesneyi DB'nin GERÇEK güncel durumuyla senkronlayarak istemciye
        # asla bayat bir `status` döndürmemeyi garanti ederiz.
        db.refresh(transaction)

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


def get_session_for_apply(payload: ApplyPlanRequest) -> SessionContext:
    """`get_session_or_404` ile aynı mantık ama farklı body şeması
    (ApplyPlanRequest, PlanRequest değil) olduğu için ayrı — ikisini
    birleştiren bir Protocol/generic burada gereksiz karmaşıklık
    olurdu (dar kapsam ilkesi, saga-oto atdd.md Soru 3)."""
    session = _sessions.get(payload.sessionId)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Oturum bulunamadı")
    return session


@app.post("/api/transactions/apply")
def apply_plan_endpoint(
    payload: ApplyPlanRequest,
    session: SessionContext = Depends(get_session_for_apply),
    db: DbSession = Depends(get_db_session),
) -> TransactionApplyResponse:
    allowed_root = Path(session.selectedFolder)
    if not allowed_root.is_dir():
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Seçili klasör artık mevcut değil")

    # Saga #309 ATDD Soru 4: apply_plan boş/sadece-LIST bir planı
    # sorunsuzca "committed" (0 FileOperation) sayar — bu, eski projenin
    # "hiçbir dosya işlenmedi ama success döndü" hata sınıfı. apply_plan
    # ÇAĞRILMADAN ÖNCE reddedilir, orchestrator.py'ye dokunulmaz.
    has_real_operation = any(step.operationType != OperationType.LIST for step in payload.plan.steps)
    if not has_real_operation:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Plan hiçbir gerçek dosya işlemi içermiyor",
        )

    pdf_files = discover_pdf_files(allowed_root)

    # Saga #309 red-team fix: transaction-sayısı ÖNCESİ/SONRASI diff'ine
    # (racy — eşzamanlı başka bir isteğin oluşturduğu transaction bu isteği
    # yanlış sınıflandırıp OLMAYAN bir transaction'ı sızdırabilirdi)
    # dayanmak YERİNE, `apply_plan`'ın `create_transaction()`'dan ÖNCE
    # yaptığı whitelist-benzeri doğrulamayı (`_distribute_files_to_steps`)
    # burada DOĞRUDAN, `apply_plan` çağrılmadan ÖNCE, kendi try/except'i
    # içinde tekrar çalıştırıyoruz. Bu determinist ön-kontrol geçerse,
    # `apply_plan` içindeki asıl çağrı bu adımda ASLA
    # `PlanApplicationError` fırlatamaz — dolayısıyla `apply_plan` çağrısı
    # sırasında yakalanan HERHANGİ bir `PlanApplicationError`, tanım
    # itibarıyla `create_transaction()` ÇALIŞTIKTAN SONRA oluşmuş olmalı
    # (bkz. orchestrator.py apply_plan: create_transaction erken çağrılır,
    # sonra adımlar uygulanır/rollback edilir). `_distribute_files_to_steps`
    # özel (underscore) bir fonksiyon ama bu düzeltme onu orchestrator.py'ye
    # dokunmadan doğrudan çağırmayı gerektiriyor (incelenmiş/onaylanmış
    # minimal kapsam). Hata mesajları sadece dosya adı içerir, tam path
    # sızdırmaz (bkz. _distribute_files_to_steps).
    try:
        _distribute_files_to_steps(pdf_files, payload.plan.steps)
    except PlanApplicationError as exc:
        logger.warning("Plan geçersiz (apply, transaction oluşturulmadan önce): %s", exc)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    try:
        transaction = apply_plan(db, payload.plan, pdf_files, allowed_root)
    except PathWhitelistError as exc:
        logger.warning(
            "Whitelist ihlali (apply): %s %s (allowed_root=%s)",
            exc.description, exc.offending_path, exc.allowed_root,
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"{exc.description} {exc.reason}") from exc
    except PlanApplicationError as exc:
        # Yukarıdaki ön-kontrol zaten geçti — bu noktaya ULAŞILDIYSA
        # `apply_plan` zaten `create_transaction()`'ı çalıştırmış ve
        # ardından ATOMİK olarak geri almış olmalı (transaction.status =
        # "rolled_back", bkz. orchestrator.py). Exception'ı 500'e çevirmek
        # yerine, DB'de zaten rolled_back olarak işaretlenmiş transaction'ı
        # normal bir 200 yanıtla döneriz — frontend'in transactionResult.ts'i
        # rolled_back'i zaten "failed" olarak gösteriyor (Saga #277).
        logger.warning("Plan uygulaması başarısız, geri alındı: %s", exc)
        latest_transaction = db.scalars(
            select(Transaction).order_by(Transaction.id.desc())
        ).first()
        if latest_transaction is None:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Plan uygulanamadı") from exc
        return TransactionApplyResponse(
            id=latest_transaction.id,
            status=latest_transaction.status,
            operations=[],
        )

    # Saga #320 red-team bulgusu 3: REDACT step'leri icin, cikan dosyanin
    # sekil degistirdigini (rasterize sayfa, artik metin-aranabilir/
    # kopyalanabilir degil, dosya buyudu) belirten bir uyari eklenir.
    # `apply_plan` bu bilgiyi Transaction ORM'inde tasimadigi icin,
    # zaten burada elimizde olan dogrulanmis `payload.plan.steps`
    # taranarak minimal-degisiklikle olusturulur.
    warnings = [
        f"'{step.redactedFileName}' dosyasinin {step.redactionRegions[0].page}. sayfasi artik "
        "bir goruntu - metin olarak aranabilir/kopyalanabilir degil ve dosya boyutu buyudu."
        for step in payload.plan.steps
        if step.operationType == OperationType.REDACT
    ]

    return TransactionApplyResponse(
        id=transaction.id,
        status=transaction.status,
        operations=[
            AppliedFileOperation(destination_path=op.destination_path, status=op.status)
            for op in transaction.operations
        ],
        warnings=warnings,
    )


def get_session_for_search(payload: SearchRequest) -> SessionContext:
    """`get_session_or_404` ve `get_session_for_apply` ile aynı mantık ama
    SearchRequest şeması olduğu için ayrı bir dependency — Saga #313."""
    session = _sessions.get(payload.sessionId)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Oturum bulunamadı")
    return session


def _parse_search_date(value: str | None, field_name: str) -> dt.datetime | None:
    """`/api/search` ve `/api/search/scan` arasında paylaşılan ISO 8601
    parse + naive->UTC normalizasyon mantığı (refaktör, davranış aynı)."""
    if value is None:
        return None
    try:
        parsed = dt.datetime.fromisoformat(value)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{field_name} geçersiz ISO 8601 formatı: '{value}'",
        )
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed


@app.post("/api/search")
def search_endpoint(
    payload: SearchRequest,
    session: SessionContext = Depends(get_session_for_search),
) -> SearchResponse:
    """Saga #313: Dosya arama endpoint'i — salt-okunur, session.selectedFolder'da
    ad/uzantı/tarih filtrelerine göre dosya arar. /api/plan akışından bağımsız."""
    allowed_root = Path(session.selectedFolder)
    if not allowed_root.is_dir():
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Seçili klasör artık mevcut değil",
        )

    # modifiedAfter/modifiedBefore ISO 8601 string'lerini datetime'a çevir
    modified_after = _parse_search_date(payload.modifiedAfter, "modifiedAfter")
    modified_before = _parse_search_date(payload.modifiedBefore, "modifiedBefore")

    # Saga #316 AC-4: fuzzyName ve namePattern birbirini dislar, ikisi
    # birden verilirse 422.
    if payload.fuzzyName is not None and payload.namePattern is not None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="fuzzyName ve namePattern aynı anda kullanılamaz",
        )

    # Saga #316 AC-3: gecersiz regex erkenden 422 ile reddedilir, 500 degil.
    if payload.namePattern is not None:
        try:
            re.compile(payload.namePattern)
        except re.error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"namePattern geçersiz regex: '{payload.namePattern}'",
            )

    results, partial = search_files(
        allowed_root,
        name_contains=payload.nameContains,
        extension=payload.extension,
        modified_after=modified_after,
        modified_before=modified_before,
        content_contains=payload.contentContains,
        fuzzy_name=payload.fuzzyName,
        name_pattern=payload.namePattern,
        return_partial=True,
    )

    return SearchResponse(results=results, partial=partial)


@app.post("/api/search/scan", status_code=status.HTTP_202_ACCEPTED)
def start_search_scan(
    payload: SearchRequest,
    session: SessionContext = Depends(get_session_for_search),
) -> ScanStartResponse:
    """Saga #337: `/api/search`in asenkron kardeşi — session/allowed_root
    doğrulaması `get_session_for_search` dependency'si sayesinde AYNI
    (404/410, AC-6), ama `search_files()` bir arka plan thread'inde
    çalıştırılır ve yanıt onu BEKLEMEDEN hemen döner (AC-1)."""
    allowed_root = Path(session.selectedFolder)
    if not allowed_root.is_dir():
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Seçili klasör artık mevcut değil",
        )

    modified_after = _parse_search_date(payload.modifiedAfter, "modifiedAfter")
    modified_before = _parse_search_date(payload.modifiedBefore, "modifiedBefore")

    # AC-S1 (threat-model): tahmin edilemez, sıralı-olmayan kimlik.
    scan_id = str(uuid.uuid4())
    with _scans_lock:
        _cleanup_expired_scans()
        _scans[scan_id] = ScanState(status="running")

    thread = threading.Thread(
        target=_run_scan,
        args=(scan_id, allowed_root),
        kwargs={
            "name_contains": payload.nameContains,
            "extension": payload.extension,
            "modified_after": modified_after,
            "modified_before": modified_before,
            "content_contains": payload.contentContains,
        },
        daemon=True,
    )
    thread.start()

    return ScanStartResponse(scanId=scan_id)


@app.get("/api/search/scan/{scan_id}")
def get_search_scan_status(scan_id: str, response: Response) -> ScanStatusResponse:
    """Saga #337: bir taramanın durumunu sorgular. Lazy cleanup: erişim
    öncesi 5 dakikadan eski `done` kayıtlar silinir (plan.md).

    Bilinmeyen `scan_id` için gövde `{"status": "not_found", ...}` olmalı
    (test_search_scan.py AC-4/AC-7) — standart FastAPI `HTTPException`
    `{"detail": ...}` üretir, bu yüzden burada durum kodu doğrudan
    `Response` üzerinden ayarlanıp ScanStatusResponse gövdesi döndürülür."""
    with _scans_lock:
        _cleanup_expired_scans()
        state = _scans.get(scan_id)
        if state is None:
            response.status_code = status.HTTP_404_NOT_FOUND
            return ScanStatusResponse(status="not_found", scannedCount=0)
        return ScanStatusResponse(
            status=state.status,
            scannedCount=state.scanned_count,
            results=state.results,
            partial=state.partial,
        )
