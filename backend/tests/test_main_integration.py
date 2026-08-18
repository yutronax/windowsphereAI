import json
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.orm import Session as DbSession
from sqlalchemy.pool import StaticPool

from backend.db_models import Base
from backend.file_operations import create_transaction, record_file_operation
from backend.main import app, get_db_session, get_llm_client
from backend.models import DateSource, OperationType, PdfFileMetadata, PlanSkeleton, PlanStep, SortOrder
from backend.orchestrator import apply_plan

client = TestClient(app)


def _in_memory_db_session() -> DbSession:
    # `TestClient`, endpoint'i bir threadpool worker thread'inde çalıştırır
    # (FastAPI'nin `run_in_threadpool`'u) — sqlite'ın varsayılan
    # `check_same_thread` koruması bu yüzden `StaticPool` + `check_same_thread=False`
    # ile devre dışı bırakılmalı, aksi halde "SQLite objects created in a
    # thread can only be used in that same thread" hatası alınır.
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    return Session(bind=engine)


def _override_get_db_session(db_session: DbSession):
    # `get_db_session` FastAPI'ye bir GENERATOR olarak tanınıyor (`yield`
    # içeriyor) — override'ın da bir generator FONKSİYONU olması gerekiyor,
    # aksi halde FastAPI override'ın dönüş değerini (bir iterator) doğrudan
    # `db` parametresine bağlar, session nesnesinin kendisini DEĞİL.
    def _override():
        yield db_session

    return _override


class _StubLLMClient:
    def __init__(self, response: str | None = None, error: bool = False):
        self.response = response
        self.error = error

    def complete(self, *, model: str, system_prompt: str, user_prompt: str) -> str:
        if self.error:
            raise RuntimeError("stub failure")
        assert self.response is not None
        return self.response


def test_health_endpoint_returns_ok():
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_config_endpoint_returns_404_when_no_config(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))

    response = client.get("/api/config")

    assert response.status_code == 404


def test_config_endpoint_returns_saved_config(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    config_dir = tmp_path / "windows-ai-files"
    config_dir.mkdir()
    (config_dir / "config.json").write_text(
        json.dumps({"selectedFolder": r"C:\Users\Yusuf\Documents"}), encoding="utf-8"
    )

    response = client.get("/api/config")

    assert response.status_code == 200
    assert response.json() == {"selectedFolder": r"C:\Users\Yusuf\Documents"}


def test_config_endpoint_returns_404_when_config_is_corrupted(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    config_dir = tmp_path / "windows-ai-files"
    config_dir.mkdir()
    (config_dir / "config.json").write_text("{not valid json", encoding="utf-8")

    response = client.get("/api/config")

    assert response.status_code == 404


def test_cors_header_present_for_allowed_origin():
    response = client.get("/api/health", headers={"Origin": "tauri://localhost"})

    assert response.headers.get("access-control-allow-origin") == "tauri://localhost"


def test_session_endpoint_creates_a_session_with_a_uuid_and_echoes_input():
    response = client.post(
        "/api/session",
        json={"selectedFolder": r"C:\Users\Yusuf\Documents", "requestText": "PDF'leri tarihe göre sırala"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["selectedFolder"] == r"C:\Users\Yusuf\Documents"
    assert body["requestText"] == "PDF'leri tarihe göre sırala"
    assert uuid.UUID(body["sessionId"])


def test_session_endpoint_returns_422_for_empty_selected_folder():
    response = client.post(
        "/api/session",
        json={"selectedFolder": "", "requestText": "PDF'leri tarihe göre sırala"},
    )

    assert response.status_code == 422


def test_session_endpoint_returns_422_for_whitespace_only_request_text():
    response = client.post(
        "/api/session",
        json={"selectedFolder": r"C:\Users\Yusuf\Documents", "requestText": "   "},
    )

    assert response.status_code == 422


def test_session_endpoint_returns_422_for_missing_fields():
    response = client.post("/api/session", json={})

    assert response.status_code == 422


def test_session_endpoint_trims_leading_and_trailing_whitespace_from_request_text():
    response = client.post(
        "/api/session",
        json={"selectedFolder": r"C:\Users\Yusuf\Documents", "requestText": "  PDF'leri tarihe göre sırala  "},
    )

    assert response.status_code == 201
    assert response.json()["requestText"] == "PDF'leri tarihe göre sırala"


def test_session_endpoint_trims_leading_and_trailing_whitespace_from_selected_folder():
    response = client.post(
        "/api/session",
        json={"selectedFolder": r"  C:\Users\Yusuf\Documents  ", "requestText": "bir istek"},
    )

    assert response.status_code == 201
    assert response.json()["selectedFolder"] == r"C:\Users\Yusuf\Documents"


def test_cors_header_present_for_session_post_from_allowed_origin():
    response = client.post(
        "/api/session",
        json={"selectedFolder": r"C:\Users\Yusuf\Documents", "requestText": "bir istek"},
        headers={"Origin": "tauri://localhost"},
    )

    assert response.headers.get("access-control-allow-origin") == "tauri://localhost"


VALID_PLAN_JSON = json.dumps(
    {
        "dateSource": "created_at",
        "sortOrder": "ascending",
        "steps": [{"order": 0, "operationType": "Taşı", "targetFolder": "2026-08", "affectedFileCount": 1, "fileNames": ["a.pdf"]}],
    }
)


def _create_session(selected_folder: str = r"C:\Users\Yusuf\Documents", request_text: str = "bir istek") -> str:
    response = client.post(
        "/api/session",
        json={"selectedFolder": selected_folder, "requestText": request_text},
    )
    return response.json()["sessionId"]


def test_plan_endpoint_returns_503_when_no_llm_api_key_configured(monkeypatch):
    monkeypatch.delenv("PLAN_LLM_API_KEY", raising=False)
    session_id = _create_session()

    response = client.post("/api/plan", json={"sessionId": session_id})

    assert response.status_code == 503


def test_plan_endpoint_returns_404_when_session_does_not_exist():
    app.dependency_overrides[get_llm_client] = lambda: _StubLLMClient(response=VALID_PLAN_JSON)
    try:
        response = client.post("/api/plan", json={"sessionId": str(uuid.uuid4())})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404


def test_plan_endpoint_discovers_real_pdf_files_from_selected_folder_and_returns_the_plan(tmp_path):
    # Saga #285: pdfFiles artık istemciden gelmiyor — backend
    # session.selectedFolder'ı kendisi tarıyor (backend/pdf_discovery.py).
    (tmp_path / "a.pdf").write_bytes(b"%PDF-1.4 fake")
    session_id = _create_session(selected_folder=str(tmp_path))
    app.dependency_overrides[get_llm_client] = lambda: _StubLLMClient(response=VALID_PLAN_JSON)
    try:
        response = client.post("/api/plan", json={"sessionId": session_id})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["steps"][0]["targetFolder"] == "2026-08"


def test_plan_endpoint_passes_the_session_request_text_to_plan_generation(tmp_path):
    # Saga #292: kullanicinin gercek istegi (session.requestText) LLM'e
    # iletilmiyordu - COPY/DELETE/RENAME/LIST hicbir zaman gercek bir
    # kullanici istegiyle tetiklenemezdi. Artik /api/plan bunu iletiyor.
    (tmp_path / "a.pdf").write_bytes(b"%PDF-1.4 fake")
    session_id = _create_session(selected_folder=str(tmp_path), request_text="Bu dosyalari yedekle")

    captured_prompt: dict[str, str] = {}

    class _CapturingStubLLMClient(_StubLLMClient):
        def complete(self, *, model: str, system_prompt: str, user_prompt: str) -> str:
            captured_prompt["user_prompt"] = user_prompt
            return super().complete(model=model, system_prompt=system_prompt, user_prompt=user_prompt)

    app.dependency_overrides[get_llm_client] = lambda: _CapturingStubLLMClient(response=VALID_PLAN_JSON)
    try:
        response = client.post("/api/plan", json={"sessionId": session_id})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert "Bu dosyalari yedekle" in captured_prompt["user_prompt"]


def test_plan_endpoint_returns_410_when_selected_folder_no_longer_exists(tmp_path):
    # Saga #285 red-team bulgusu: klasör session olusturulduktan sonra
    # silinirse/tasinirsa, bu "0 PDF bulundu" ile ayni sekilde 200
    # donmemeli - kullanicinin gormesi gereken gercek durum farkli.
    missing_folder = tmp_path / "silinmis-klasor"
    session_id = _create_session(selected_folder=str(missing_folder))
    app.dependency_overrides[get_llm_client] = lambda: _StubLLMClient(response=VALID_PLAN_JSON)
    try:
        response = client.post("/api/plan", json={"sessionId": session_id})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 410


def test_plan_endpoint_returns_empty_plan_when_selected_folder_has_no_pdf_files(tmp_path):
    session_id = _create_session(selected_folder=str(tmp_path))
    app.dependency_overrides[get_llm_client] = lambda: _StubLLMClient(response=VALID_PLAN_JSON)
    try:
        response = client.post("/api/plan", json={"sessionId": session_id})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["steps"] == []


def test_plan_endpoint_ignores_non_pdf_files_and_subfolders(tmp_path):
    (tmp_path / "a.pdf").write_bytes(b"%PDF-1.4 fake")
    (tmp_path / "not-a-pdf.txt").write_text("merhaba")
    subfolder = tmp_path / "alt-klasor"
    subfolder.mkdir()
    (subfolder / "b.pdf").write_bytes(b"%PDF-1.4 fake")
    session_id = _create_session(selected_folder=str(tmp_path))

    captured_prompt: dict[str, str] = {}

    class _CapturingStubLLMClient(_StubLLMClient):
        def complete(self, *, model: str, system_prompt: str, user_prompt: str) -> str:
            captured_prompt["user_prompt"] = user_prompt
            return super().complete(model=model, system_prompt=system_prompt, user_prompt=user_prompt)

    app.dependency_overrides[get_llm_client] = lambda: _CapturingStubLLMClient(response=VALID_PLAN_JSON)
    try:
        response = client.post("/api/plan", json={"sessionId": session_id})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert "a.pdf" in captured_prompt["user_prompt"]
    assert "not-a-pdf.txt" not in captured_prompt["user_prompt"]
    assert "b.pdf" not in captured_prompt["user_prompt"]


def test_plan_endpoint_returns_502_when_plan_generation_fails(tmp_path):
    (tmp_path / "a.pdf").write_bytes(b"%PDF-1.4 fake")
    session_id = _create_session(selected_folder=str(tmp_path))
    app.dependency_overrides[get_llm_client] = lambda: _StubLLMClient(error=True)
    try:
        response = client.post("/api/plan", json={"sessionId": session_id})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 502
    assert "detail" in response.json()


def test_plan_endpoint_returns_422_for_missing_fields():
    app.dependency_overrides[get_llm_client] = lambda: _StubLLMClient(response=VALID_PLAN_JSON)
    try:
        response = client.post("/api/plan", json={})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422


def test_plan_endpoint_returns_403_when_a_discovered_pdf_sits_under_a_system_root(tmp_path, monkeypatch):
    # allowed_root'un kendisi sistem korumalı DEĞİLSE bile, içindeki bir
    # PDF gerçekten bir sistem kökü altına denk gelirse (ör. allowed_root
    # ProgramData'nın kendisiyse) whitelist reddeder — Saga #272 koruması.
    protected_root = tmp_path / "ProgramData"
    protected_root.mkdir()
    (protected_root / "a.pdf").write_bytes(b"%PDF-1.4 fake")
    monkeypatch.setenv("ProgramData", str(protected_root))
    session_id = _create_session(selected_folder=str(protected_root))
    app.dependency_overrides[get_llm_client] = lambda: _StubLLMClient(response=VALID_PLAN_JSON)
    try:
        response = client.post("/api/plan", json={"sessionId": session_id})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    # Saga #283 red-team bulgusu: tam mutlak path istemciye SIZDIRILMAMALI
    # (sunucunun dosya sistemi yapısı hakkında keşif bilgisi verirdi).
    assert str(protected_root) not in response.json()["detail"]


def test_transactions_endpoint_returns_empty_list_when_no_transactions_exist():
    db_session = _in_memory_db_session()
    app.dependency_overrides[get_db_session] = _override_get_db_session(db_session)
    try:
        response = client.get("/api/transactions")
    finally:
        app.dependency_overrides.clear()
        db_session.close()

    assert response.status_code == 200
    assert response.json() == []


def test_transactions_endpoint_returns_newest_transaction_first_with_a_status_field_summary(tmp_path):
    db_session = _in_memory_db_session()
    older = create_transaction(db_session)
    record_file_operation(
        db_session,
        older,
        operation_type="Taşı",
        source_path=str(tmp_path / "a.pdf"),
        destination_path=str(tmp_path / "2026-07" / "a.pdf"),
        backup_path=str(tmp_path / "a.pdf"),
    )
    older.status = "committed"
    db_session.commit()

    newer = create_transaction(db_session)
    record_file_operation(
        db_session,
        newer,
        operation_type="Taşı",
        source_path=str(tmp_path / "b.pdf"),
        destination_path=str(tmp_path / "2026-08" / "b.pdf"),
        backup_path=str(tmp_path / "b.pdf"),
    )
    newer.status = "committed"
    db_session.commit()

    app.dependency_overrides[get_db_session] = _override_get_db_session(db_session)
    try:
        response = client.get("/api/transactions")
    finally:
        app.dependency_overrides.clear()
        db_session.close()

    assert response.status_code == 200
    body = response.json()
    assert [entry["id"] for entry in body] == [newer.id, older.id]
    assert body[0]["status"] == "committed"
    assert body[0]["fileCount"] == 1
    assert body[0]["targetFolders"] == ["2026-08"]


def test_transactions_endpoint_never_leaks_absolute_paths_only_folder_names(tmp_path):
    db_session = _in_memory_db_session()
    transaction = create_transaction(db_session)
    record_file_operation(
        db_session,
        transaction,
        operation_type="Taşı",
        source_path=str(tmp_path / "a.pdf"),
        destination_path=str(tmp_path / "2026-08" / "a.pdf"),
        backup_path=str(tmp_path / "a.pdf"),
    )
    transaction.status = "committed"
    db_session.commit()

    app.dependency_overrides[get_db_session] = _override_get_db_session(db_session)
    try:
        response = client.get("/api/transactions")
    finally:
        app.dependency_overrides.clear()
        db_session.close()

    body = response.json()
    assert str(tmp_path) not in json.dumps(body)


def _apply_a_move_plan(db_session, tmp_path):
    (tmp_path / "a.pdf").write_bytes(b"%PDF-1.4 fake")
    pdf_files = [PdfFileMetadata(filename="a.pdf", createdAt="2026-08-01")]
    plan = PlanSkeleton(
        steps=[
            PlanStep(
                order=0,
                operationType=OperationType.MOVE,
                targetFolder="2026-08",
                affectedFileCount=1,
                fileNames=["a.pdf"],
            )
        ],
        dateSource=DateSource.CREATED_AT,
        sortOrder=SortOrder.ASCENDING,
    )
    return apply_plan(db_session, plan, pdf_files, tmp_path)


def test_revert_endpoint_returns_404_for_an_unknown_transaction_id():
    db_session = _in_memory_db_session()
    app.dependency_overrides[get_db_session] = _override_get_db_session(db_session)
    try:
        response = client.post("/api/transactions/999/revert", json={})
    finally:
        app.dependency_overrides.clear()
        db_session.close()

    assert response.status_code == 404


def test_revert_endpoint_returns_409_when_the_transaction_is_not_committed(tmp_path):
    db_session = _in_memory_db_session()
    transaction = _apply_a_move_plan(db_session, tmp_path)
    transaction.status = "reverted"
    db_session.commit()

    app.dependency_overrides[get_db_session] = _override_get_db_session(db_session)
    try:
        response = client.post(f"/api/transactions/{transaction.id}/revert", json={})
    finally:
        app.dependency_overrides.clear()
        db_session.close()

    assert response.status_code == 409
    # Reddedilince hiçbir dosyaya dokunulmaz.
    assert not (tmp_path / "a.pdf").exists()
    assert (tmp_path / "2026-08" / "a.pdf").exists()


def test_revert_endpoint_moves_the_file_back_and_returns_reverted_status(tmp_path):
    db_session = _in_memory_db_session()
    transaction = _apply_a_move_plan(db_session, tmp_path)

    app.dependency_overrides[get_db_session] = _override_get_db_session(db_session)
    try:
        response = client.post(f"/api/transactions/{transaction.id}/revert", json={})
    finally:
        app.dependency_overrides.clear()
        db_session.close()

    assert response.status_code == 200
    body = response.json()
    assert body == {"transactionId": transaction.id, "status": "reverted"}
    assert (tmp_path / "a.pdf").exists()
    assert not (tmp_path / "2026-08" / "a.pdf").exists()


def test_revert_endpoint_ignores_a_spoofed_allowed_root_and_uses_the_transactions_own_stored_root(tmp_path):
    # Saga #301: RevertTransactionRequest artik allowedRoot alani icermiyor.
    # Istemci yine de eski/spoofed bir "allowedRoot" alani gonderirse (ornegin
    # genis bir kok, "C:\\"), Pydantic'in varsayilan extra="ignore" davranisi
    # (bu projede hicbir model extra="forbid" kullanmiyor) bu alani yok sayar
    # ve gercek containment/revert islemi HER ZAMAN transaction'in KENDI
    # apply_plan sirasinda kaydedilen allowed_root'unu kullanir.
    db_session = _in_memory_db_session()
    transaction = _apply_a_move_plan(db_session, tmp_path)

    app.dependency_overrides[get_db_session] = _override_get_db_session(db_session)
    try:
        response = client.post(
            f"/api/transactions/{transaction.id}/revert",
            json={"allowedRoot": "C:\\"},
        )
    finally:
        app.dependency_overrides.clear()
        db_session.close()

    assert response.status_code == 200
    assert response.json() == {"transactionId": transaction.id, "status": "reverted"}
    assert (tmp_path / "a.pdf").exists()
    assert not (tmp_path / "2026-08" / "a.pdf").exists()


def test_revert_endpoint_returns_409_when_the_transactions_allowed_root_is_missing(tmp_path):
    # Saga #301 red-team bulgusu: migration oncesi (allowed_root kolonu
    # eklenmeden once olusturulmus) "committed" bir transaction icin
    # allowed_root NULL olabilir. Bu, `TransactionRevertError`i genel
    # except blogunda YUTUP durumu DEGISTIRMEDEN (hala "committed") 200
    # donen bir onceki implementasyondan FARKLI olarak, fiziksel geri
    # alma hic denenmeden ayri ve net bir 409 ile reddedilmeli.
    db_session = _in_memory_db_session()
    transaction = _apply_a_move_plan(db_session, tmp_path)
    transaction.allowed_root = None
    db_session.commit()

    app.dependency_overrides[get_db_session] = _override_get_db_session(db_session)
    try:
        response = client.post(f"/api/transactions/{transaction.id}/revert", json={})
    finally:
        app.dependency_overrides.clear()
        db_session.close()

    assert response.status_code == 409
    # Reddedilince hicbir dosyaya dokunulmaz ve durum "committed" olarak kalir.
    assert not (tmp_path / "a.pdf").exists()
    assert (tmp_path / "2026-08" / "a.pdf").exists()


def test_revert_endpoint_reports_the_real_db_status_after_losing_the_claim_race(tmp_path, monkeypatch):
    # Saga #302 red-team bulgusu: `revert_transaction`in atomik claim'i
    # (ornegin `purge_expired_delete_backups`e) yarisi KAYBETTIGINDE
    # `TransactionRevertError` firlatilir, ama eskiden endpoint bu durumda
    # bellekteki BAYAT `transaction.status`u ("committed") donerdi - DB'deki
    # GERCEK deger (kazananin yazdigi "backup_purged") ile UYUMSUZ. Bu test,
    # `db.refresh(transaction)` duzeltmesinin istemciye HER ZAMAN DB'nin
    # guncel degerini dondurdugunu kanitlar.
    import backend.orchestrator as orchestrator_module
    from sqlalchemy import update as sa_update

    db_session = _in_memory_db_session()
    transaction = _apply_a_move_plan(db_session, tmp_path)
    txn_id = transaction.id

    def _lose_the_race(session, transaction_id, *, from_status, to_status):
        # Baska bir islemin (ornegin purge) yarisi kazanip satiri
        # "backup_purged" yaptigini simule et, sonra HER ZAMAN kaybettigimizi
        # bildir - `revert_transaction`in TransactionRevertError firlatmasini
        # tetikler.
        session.execute(
            sa_update(orchestrator_module.Transaction)
            .where(orchestrator_module.Transaction.id == transaction_id)
            .values(status="backup_purged")
        )
        session.commit()
        return False

    monkeypatch.setattr(orchestrator_module, "_claim_transaction_status", _lose_the_race)

    app.dependency_overrides[get_db_session] = _override_get_db_session(db_session)
    try:
        response = client.post(f"/api/transactions/{txn_id}/revert", json={})
    finally:
        app.dependency_overrides.clear()
        db_session.close()

    assert response.status_code == 200
    # Onceki hatali davranis: {"transactionId": txn_id, "status": "committed"}
    # (bayat bellek-ici deger) donerdi. Duzeltilmis davranis: DB'nin GERCEK
    # guncel degeri.
    assert response.json() == {"transactionId": txn_id, "status": "backup_purged"}


def test_revert_endpoint_returns_200_with_revert_failed_status_when_the_physical_move_fails(tmp_path):
    db_session = _in_memory_db_session()
    transaction = _apply_a_move_plan(db_session, tmp_path)
    # Rollback'in KAYNAĞINI (hedef klasördeki dosya) bir KLASÖRE, hedefini
    # (orijinal konum) DOLU bir dosyaya çeviriyoruz — `shutil.move` bir
    # klasörü zaten var olan bir dosyanın üzerine taşımaya çalışınca
    # OSError fırlatır (backend/tests/test_orchestrator.py'deki AYNI
    # kanıtlanmış desen).
    moved_file = tmp_path / "2026-08" / "a.pdf"
    moved_file.unlink()
    moved_file.mkdir()
    (tmp_path / "a.pdf").write_bytes(b"conflict")

    app.dependency_overrides[get_db_session] = _override_get_db_session(db_session)
    try:
        response = client.post(f"/api/transactions/{transaction.id}/revert", json={})
    finally:
        app.dependency_overrides.clear()
        db_session.close()

    assert response.status_code == 200
    assert response.json() == {"transactionId": transaction.id, "status": "revert_failed"}
