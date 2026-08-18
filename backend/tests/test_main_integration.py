import datetime as dt
import json
import os
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.orm import Session as DbSession
from sqlalchemy.pool import StaticPool

from backend.db_models import Base, Transaction
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


def _valid_apply_plan_body(file_names: list[str] | None = None) -> dict:
    return {
        "dateSource": "created_at",
        "sortOrder": "ascending",
        "steps": [
            {
                "order": 0,
                "operationType": "Taşı",
                "targetFolder": "2026-08",
                "affectedFileCount": len(file_names) if file_names is not None else 1,
                "fileNames": file_names if file_names is not None else ["a.pdf"],
            }
        ],
    }


def test_apply_plan_endpoint_moves_the_file_on_disk_and_returns_committed_status(tmp_path):
    # Saga #309: onaylanan plan gerçekten POST /api/transactions/apply'a
    # gönderildiğinde dosyalar diskte gerçekten taşınmalı ve yanıt
    # TransactionApplyResponse şeklini (id/status/operations) taşımalı.
    db_session = _in_memory_db_session()
    (tmp_path / "a.pdf").write_bytes(b"%PDF-1.4 fake")
    session_id = _create_session(selected_folder=str(tmp_path))

    app.dependency_overrides[get_db_session] = _override_get_db_session(db_session)
    try:
        response = client.post(
            "/api/transactions/apply",
            json={"sessionId": session_id, "plan": _valid_apply_plan_body()},
        )
    finally:
        app.dependency_overrides.clear()
        db_session.close()

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "committed"
    assert isinstance(body["id"], int)
    assert body["operations"] == [
        {"destination_path": str(tmp_path / "2026-08" / "a.pdf"), "status": "completed"}
    ]
    # Dosya GERÇEKTEN diskte taşınmış olmalı.
    assert not (tmp_path / "a.pdf").exists()
    assert (tmp_path / "2026-08" / "a.pdf").exists()


def test_apply_plan_endpoint_returns_422_and_creates_no_transaction_for_a_zero_real_operation_plan(tmp_path):
    # Saga #309 ATDD Soru 4: boş steps VEYA sadece LIST adımlarından oluşan
    # bir plan, "0 dosya işlendi ama success" false-positive'ini önlemek
    # için apply_plan hiç çağrılmadan 422 ile reddedilmeli — hiçbir
    # Transaction satırı DB'ye yazılmamalı.
    db_session = _in_memory_db_session()
    (tmp_path / "a.pdf").write_bytes(b"%PDF-1.4 fake")
    session_id = _create_session(selected_folder=str(tmp_path))
    empty_plan = {"dateSource": "created_at", "sortOrder": "ascending", "steps": []}

    app.dependency_overrides[get_db_session] = _override_get_db_session(db_session)
    try:
        response = client.post(
            "/api/transactions/apply",
            json={"sessionId": session_id, "plan": empty_plan},
        )
    finally:
        app.dependency_overrides.clear()
        transaction_count = len(db_session.scalars(select(Transaction)).all())
        db_session.close()

    assert response.status_code == 422
    assert transaction_count == 0


def test_apply_plan_endpoint_returns_422_for_a_plan_with_only_list_steps(tmp_path):
    db_session = _in_memory_db_session()
    (tmp_path / "a.pdf").write_bytes(b"%PDF-1.4 fake")
    session_id = _create_session(selected_folder=str(tmp_path))
    list_only_plan = {
        "dateSource": "created_at",
        "sortOrder": "ascending",
        "steps": [
            {
                "order": 0,
                "operationType": "Listele",
                "targetFolder": "2026-08",
                "affectedFileCount": 1,
                "fileNames": ["a.pdf"],
            }
        ],
    }

    app.dependency_overrides[get_db_session] = _override_get_db_session(db_session)
    try:
        response = client.post(
            "/api/transactions/apply",
            json={"sessionId": session_id, "plan": list_only_plan},
        )
    finally:
        app.dependency_overrides.clear()
        transaction_count = len(db_session.scalars(select(Transaction)).all())
        db_session.close()

    assert response.status_code == 422
    assert transaction_count == 0


def test_apply_plan_endpoint_returns_403_when_a_file_name_is_not_in_the_whitelisted_pdf_files(tmp_path):
    # Whitelist ihlali: fileNames, allowed_root'ta taranan pdf_files'ta
    # BULUNMAYAN bir dosya adına atıfta bulunuyor. Tam path istemciye
    # SIZDIRILMAMALI (Saga #283 ilkesi) — sadece kısa `reason`.
    db_session = _in_memory_db_session()
    (tmp_path / "a.pdf").write_bytes(b"%PDF-1.4 fake")
    session_id = _create_session(selected_folder=str(tmp_path))

    app.dependency_overrides[get_db_session] = _override_get_db_session(db_session)
    try:
        response = client.post(
            "/api/transactions/apply",
            json={"sessionId": session_id, "plan": _valid_apply_plan_body(file_names=["does-not-exist.pdf"])},
        )
        # Saga #309 red-team fix regresyon testi: bu 403, `_distribute_files_
        # to_steps` ön-kontrolünden geliyor ve `apply_plan`/`create_transaction`
        # HİÇ ÇAĞRILMAMALI — yani bu istek SIFIR yeni Transaction satırı
        # oluşturmalı. Eski (racy) count-diff sürümünde bu doğruydu ama sadece
        # eşzamanlı başka bir transaction yokken; artık deterministik.
        transaction_count = len(db_session.scalars(select(Transaction)).all())
    finally:
        app.dependency_overrides.clear()
        db_session.close()

    assert response.status_code == 403
    detail = response.json()["detail"]
    assert str(tmp_path) not in detail
    assert transaction_count == 0


def test_apply_plan_endpoint_returns_404_for_an_unknown_session_id(tmp_path):
    db_session = _in_memory_db_session()

    app.dependency_overrides[get_db_session] = _override_get_db_session(db_session)
    try:
        response = client.post(
            "/api/transactions/apply",
            json={"sessionId": str(uuid.uuid4()), "plan": _valid_apply_plan_body()},
        )
    finally:
        app.dependency_overrides.clear()
        db_session.close()

    assert response.status_code == 404


def test_apply_plan_endpoint_returns_410_when_the_selected_folder_no_longer_exists(tmp_path):
    db_session = _in_memory_db_session()
    missing_folder = tmp_path / "silinmis-klasor"
    session_id = _create_session(selected_folder=str(missing_folder))

    app.dependency_overrides[get_db_session] = _override_get_db_session(db_session)
    try:
        response = client.post(
            "/api/transactions/apply",
            json={"sessionId": session_id, "plan": _valid_apply_plan_body()},
        )
    finally:
        app.dependency_overrides.clear()
        db_session.close()

    assert response.status_code == 410


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


def _build_minimal_real_pdf_bytes() -> bytes:
    # Saga #320 red-team bulgusu 3: REDACT icin sayfa-sayisi dogrulamasi
    # gercek bir pypdf.PdfReader gerektiriyor - "%PDF-1.4 fake" sahte
    # bayti burada yeterli degil. test_pdf_redact.py/test_orchestrator.py
    # ile AYNI el-yapimi minimal PDF teknigi (reportlab kurulu degil).
    objects = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        3: b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 300] /Contents 4 0 R >>",
        4: b"<< /Length 4 >>\nstream\n\nendstream",
    }
    out = bytearray()
    out += b"%PDF-1.4\n"
    offsets: dict[int, int] = {}
    for obj_num in sorted(objects):
        offsets[obj_num] = len(out)
        out += f"{obj_num} 0 obj\n".encode()
        out += objects[obj_num]
        out += b"\nendobj\n"
    xref_offset = len(out)
    max_obj = max(objects)
    out += f"xref\n0 {max_obj + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for obj_num in range(1, max_obj + 1):
        out += f"{offsets.get(obj_num, 0):010d} 00000 n \n".encode()
    out += b"trailer\n"
    out += f"<< /Size {max_obj + 1} /Root 1 0 R >>\n".encode()
    out += b"startxref\n"
    out += f"{xref_offset}\n".encode()
    out += b"%%EOF"
    return bytes(out)


def test_apply_plan_endpoint_returns_a_warning_for_a_redact_step(tmp_path):
    # Saga #320 red-team bulgusu 3 (AC6/P1): REDACT ciktisi rasterize
    # edilmis bir sayfa icerir (buyur, artik metin-aranabilir/kopyalanabilir
    # degil) - TransactionApplyResponse'un bunu `warnings` alaninda acikca
    # bildirmesi gerekir, aksi halde istemci sessizce kesfetmemis olur.
    db_session = _in_memory_db_session()
    (tmp_path / "gizli.pdf").write_bytes(_build_minimal_real_pdf_bytes())
    session_id = _create_session(selected_folder=str(tmp_path))
    redact_plan = {
        "dateSource": "created_at",
        "sortOrder": "ascending",
        "steps": [
            {
                "order": 0,
                "operationType": "Karart",
                "targetFolder": "2026-08",
                "affectedFileCount": 1,
                "fileNames": ["gizli.pdf"],
                "redactionRegions": [{"page": 1, "x0": 0, "y0": 0, "x1": 300, "y1": 300}],
                "redactedFileName": "gizli_karartilmis.pdf",
            }
        ],
    }

    app.dependency_overrides[get_db_session] = _override_get_db_session(db_session)
    try:
        response = client.post(
            "/api/transactions/apply",
            json={"sessionId": session_id, "plan": redact_plan},
        )
    finally:
        app.dependency_overrides.clear()
        db_session.close()

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "committed"
    assert len(body["warnings"]) == 1
    assert "gizli_karartilmis.pdf" in body["warnings"][0]
    assert (tmp_path / "gizli_karartilmis.pdf").exists()


# Saga #313: Dosya arama endpoint'i testleri


def test_search_endpoint_returns_404_for_unknown_session_id():
    response = client.post(
        "/api/search",
        json={"sessionId": str(uuid.uuid4())},
    )

    assert response.status_code == 404


def test_search_endpoint_returns_410_when_selected_folder_no_longer_exists(tmp_path):
    missing_folder = tmp_path / "silinmis-klasor"
    session_id = _create_session(selected_folder=str(missing_folder))

    response = client.post(
        "/api/search",
        json={"sessionId": session_id},
    )

    assert response.status_code == 410


def test_search_endpoint_returns_200_with_all_files_when_no_filters_applied(tmp_path):
    (tmp_path / "dosya1.txt").write_text("merhaba")
    (tmp_path / "dosya2.pdf").write_bytes(b"%PDF-1.4 fake")
    (tmp_path / "test.doc").write_bytes(b"fake doc")
    session_id = _create_session(selected_folder=str(tmp_path))

    response = client.post(
        "/api/search",
        json={"sessionId": session_id},
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["results"]) == 3
    filenames = [r["filename"] for r in body["results"]]
    assert "dosya1.txt" in filenames
    assert "dosya2.pdf" in filenames
    assert "test.doc" in filenames


def test_search_endpoint_ignores_hidden_files(tmp_path):
    (tmp_path / "dosya1.txt").write_text("merhaba")
    (tmp_path / ".gizli").write_text("gizli dosya")
    session_id = _create_session(selected_folder=str(tmp_path))

    response = client.post(
        "/api/search",
        json={"sessionId": session_id},
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["results"]) == 1
    assert body["results"][0]["filename"] == "dosya1.txt"


def test_search_endpoint_filters_by_name_contains_case_insensitive(tmp_path):
    (tmp_path / "fatura_01.pdf").write_bytes(b"%PDF-1.4 fake")
    (tmp_path / "FATURA_02.pdf").write_bytes(b"%PDF-1.4 fake")
    (tmp_path / "rapor.txt").write_text("rapor")
    session_id = _create_session(selected_folder=str(tmp_path))

    response = client.post(
        "/api/search",
        json={"sessionId": session_id, "nameContains": "fatura"},
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["results"]) == 2
    filenames = {r["filename"] for r in body["results"]}
    assert "fatura_01.pdf" in filenames
    assert "FATURA_02.pdf" in filenames


def test_search_endpoint_filters_by_extension_with_dot(tmp_path):
    (tmp_path / "dosya1.pdf").write_bytes(b"%PDF-1.4 fake")
    (tmp_path / "dosya2.PDF").write_bytes(b"%PDF-1.4 fake")
    (tmp_path / "dosya3.txt").write_text("txt")
    session_id = _create_session(selected_folder=str(tmp_path))

    response = client.post(
        "/api/search",
        json={"sessionId": session_id, "extension": ".pdf"},
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["results"]) == 2
    filenames = {r["filename"] for r in body["results"]}
    assert "dosya1.pdf" in filenames
    assert "dosya2.PDF" in filenames


def test_search_endpoint_filters_by_extension_without_dot(tmp_path):
    (tmp_path / "dosya1.pdf").write_bytes(b"%PDF-1.4 fake")
    (tmp_path / "dosya2.PDF").write_bytes(b"%PDF-1.4 fake")
    (tmp_path / "dosya3.txt").write_text("txt")
    session_id = _create_session(selected_folder=str(tmp_path))

    response = client.post(
        "/api/search",
        json={"sessionId": session_id, "extension": "pdf"},
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["results"]) == 2
    filenames = {r["filename"] for r in body["results"]}
    assert "dosya1.pdf" in filenames
    assert "dosya2.PDF" in filenames


def test_search_endpoint_filters_by_modified_after(tmp_path):
    import time as time_module

    file1 = tmp_path / "dosya1.txt"
    file1.write_text("eski")
    old_mtime = time_module.time() - 3600  # 1 saat önce
    file1_mtime = dt.datetime.fromtimestamp(old_mtime, tz=dt.timezone.utc)

    file2 = tmp_path / "dosya2.txt"
    file2.write_text("yeni")

    # file1'in mtime'ını geriye al
    os.utime(file1, (old_mtime, old_mtime))

    session_id = _create_session(selected_folder=str(tmp_path))

    # file1'den SONRA (biraz daha sonra) dosyaları ara - file1'in mtime'ından
    # SONRA olanları. >= olduğu için, file1_mtime'dan 1 saniye sonrasını seçiyoruz.
    filter_time = file1_mtime + dt.timedelta(seconds=1)
    response = client.post(
        "/api/search",
        json={"sessionId": session_id, "modifiedAfter": filter_time.isoformat()},
    )

    assert response.status_code == 200
    body = response.json()
    # file1 GEÇ (mtime'ı filter_time'dan daha eski), file2 VAR
    filenames = [r["filename"] for r in body["results"]]
    assert "dosya1.txt" not in filenames
    assert "dosya2.txt" in filenames


def test_search_endpoint_filters_by_modified_before(tmp_path):
    import time as time_module

    file1 = tmp_path / "dosya1.txt"
    file1.write_text("eski")
    old_mtime = time_module.time() - 3600  # 1 saat önce
    file1_mtime = dt.datetime.fromtimestamp(old_mtime, tz=dt.timezone.utc)

    file2 = tmp_path / "dosya2.txt"
    file2.write_text("yeni")

    # file2'nin mtime'ını ileride al
    os.utime(file1, (old_mtime, old_mtime))

    session_id = _create_session(selected_folder=str(tmp_path))

    # file1'den daha eski dosyaları ara (file1_mtime'dan önce)
    response = client.post(
        "/api/search",
        json={"sessionId": session_id, "modifiedBefore": file1_mtime.isoformat()},
    )

    assert response.status_code == 200
    body = response.json()
    # file1 VAR, file2 GEÇ
    filenames = [r["filename"] for r in body["results"]]
    assert "dosya1.txt" in filenames
    assert "dosya2.txt" not in filenames


# --- Saga #335: tz-naive-tarih-500-fix (RED STEP) ---
# `modifiedAfter`/`modifiedBefore` offset'siz (naive) ISO 8601 string'i
# gonderildiginde `backend/main.py` naive bir `datetime` uretiyor,
# `backend/file_search.py::search_files()` ise dosya `st_mtime`'ini HER
# ZAMAN tz-aware (UTC) uretip karsilastiriyor -> naive/aware karsilastirmasi
# Python'da TypeError firlatir, bu da yakalanmayan bir 500'e dusuyor. Henuz
# duzeltme YAPILMADI, bu yuzden asagidaki testler simdi 500 (veya TestClient
# icinde firlatilan TypeError) ile KIRMIZI olmalidir - bu BEKLENEN (red step).


def test_search_endpoint_filters_by_naive_modified_after_defaults_to_utc(tmp_path):
    """AC-1 [Critical]: naive modifiedAfter (offset yok) -> 500 DEGIL, 200 doner,
    UTC varsayilip dogru filtrelenir."""
    import time as time_module

    file1 = tmp_path / "dosya1.txt"
    file1.write_text("eski")
    old_mtime = time_module.time() - 3600  # 1 saat once
    file1_mtime_utc = dt.datetime.fromtimestamp(old_mtime, tz=dt.timezone.utc)
    os.utime(file1, (old_mtime, old_mtime))

    file2 = tmp_path / "dosya2.txt"
    file2.write_text("yeni")

    session_id = _create_session(selected_folder=str(tmp_path))

    # file1'in mtime'indan 1 saniye SONRAsini, offset OLMADAN (naive) gonder.
    naive_filter_time = (file1_mtime_utc + dt.timedelta(seconds=1)).replace(tzinfo=None)
    response = client.post(
        "/api/search",
        json={"sessionId": session_id, "modifiedAfter": naive_filter_time.isoformat()},
    )

    assert response.status_code == 200
    body = response.json()
    filenames = [r["filename"] for r in body["results"]]
    assert "dosya1.txt" not in filenames
    assert "dosya2.txt" in filenames


def test_search_endpoint_filters_by_naive_modified_before_defaults_to_utc(tmp_path):
    """AC-2 [Critical]: naive modifiedBefore (offset yok) -> 500 DEGIL, 200 doner,
    UTC varsayilip dogru filtrelenir."""
    import time as time_module

    file1 = tmp_path / "dosya1.txt"
    file1.write_text("eski")
    old_mtime = time_module.time() - 3600  # 1 saat once
    file1_mtime_utc = dt.datetime.fromtimestamp(old_mtime, tz=dt.timezone.utc)
    os.utime(file1, (old_mtime, old_mtime))

    file2 = tmp_path / "dosya2.txt"
    file2.write_text("yeni")

    session_id = _create_session(selected_folder=str(tmp_path))

    # file1'in mtime'indan 1 saniye SONRAsini, offset OLMADAN (naive) gonder
    # -> file1 (daha eski) bu sinirin altinda kalmali, file2 (daha yeni) disarida.
    naive_filter_time = (file1_mtime_utc + dt.timedelta(seconds=1)).replace(tzinfo=None)
    response = client.post(
        "/api/search",
        json={"sessionId": session_id, "modifiedBefore": naive_filter_time.isoformat()},
    )

    assert response.status_code == 200
    body = response.json()
    filenames = [r["filename"] for r in body["results"]]
    assert "dosya1.txt" in filenames
    assert "dosya2.txt" not in filenames


def test_search_endpoint_combines_naive_modified_after_with_aware_modified_before(tmp_path):
    """AC-3 [High]: modifiedAfter naive VE modifiedBefore tz-aware (+03:00) birlikte
    verilir -> 200 doner, ikisi de bagimsiz dogru normalize edilip AND ile birlesir."""
    import time as time_module

    file_too_old = tmp_path / "cok_eski.txt"
    file_too_old.write_text("cok eski")
    too_old_mtime = time_module.time() - 7200  # 2 saat once
    os.utime(file_too_old, (too_old_mtime, too_old_mtime))

    file_in_range = tmp_path / "aralikta.txt"
    file_in_range.write_text("aralikta")
    in_range_mtime = time_module.time() - 3600  # 1 saat once
    os.utime(file_in_range, (in_range_mtime, in_range_mtime))

    file_too_new = tmp_path / "cok_yeni.txt"
    file_too_new.write_text("cok yeni")
    # su anki (en yeni) mtime - filtrelerin disinda kalmali.

    session_id = _create_session(selected_folder=str(tmp_path))

    # modifiedAfter: cok_eski'nin biraz SONRASI, naive (offset yok).
    naive_after = (
        dt.datetime.fromtimestamp(too_old_mtime, tz=dt.timezone.utc) + dt.timedelta(seconds=1)
    ).replace(tzinfo=None)
    # modifiedBefore: cok_yeni'den biraz ONCESI, tz-aware (+03:00) -> UTC'ye
    # cevrildiginde aralikta.txt'yi icine alan ama cok_yeni.txt'yi disarida
    # birakan bir sinir.
    aware_before_utc = dt.datetime.now(dt.timezone.utc) - dt.timedelta(seconds=1)
    aware_before_plus3 = aware_before_utc.astimezone(dt.timezone(dt.timedelta(hours=3)))

    response = client.post(
        "/api/search",
        json={
            "sessionId": session_id,
            "modifiedAfter": naive_after.isoformat(),
            "modifiedBefore": aware_before_plus3.isoformat(),
        },
    )

    assert response.status_code == 200
    body = response.json()
    filenames = [r["filename"] for r in body["results"]]
    assert "cok_eski.txt" not in filenames
    assert "aralikta.txt" in filenames
    assert "cok_yeni.txt" not in filenames


def test_search_endpoint_returns_422_for_invalid_modified_after_format(tmp_path):
    (tmp_path / "dosya.txt").write_text("test")
    session_id = _create_session(selected_folder=str(tmp_path))

    response = client.post(
        "/api/search",
        json={"sessionId": session_id, "modifiedAfter": "not-a-valid-iso-date"},
    )

    assert response.status_code == 422
    assert "modifiedAfter" in response.json()["detail"]


def test_search_endpoint_returns_422_for_invalid_modified_before_format(tmp_path):
    (tmp_path / "dosya.txt").write_text("test")
    session_id = _create_session(selected_folder=str(tmp_path))

    response = client.post(
        "/api/search",
        json={"sessionId": session_id, "modifiedBefore": "invalid-date"},
    )

    assert response.status_code == 422
    assert "modifiedBefore" in response.json()["detail"]


def test_search_endpoint_combines_filters_with_and_logic(tmp_path):
    (tmp_path / "fatura_2026.pdf").write_bytes(b"%PDF-1.4 fake")
    (tmp_path / "fatura_2026.txt").write_text("txt")
    (tmp_path / "rapor_2026.pdf").write_bytes(b"%PDF-1.4 fake")
    session_id = _create_session(selected_folder=str(tmp_path))

    # nameContains="fatura" AND extension="pdf"
    response = client.post(
        "/api/search",
        json={
            "sessionId": session_id,
            "nameContains": "fatura",
            "extension": "pdf",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["results"]) == 1
    assert body["results"][0]["filename"] == "fatura_2026.pdf"


def test_search_endpoint_returns_correct_search_result_item_fields(tmp_path):
    test_file = tmp_path / "test.txt"
    test_file.write_text("merhaba dünya")
    session_id = _create_session(selected_folder=str(tmp_path))

    response = client.post(
        "/api/search",
        json={"sessionId": session_id},
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["results"]) == 1
    result = body["results"][0]

    # SearchResultItem alanlarını kontrol et
    assert "filename" in result
    assert result["filename"] == "test.txt"
    assert "extension" in result
    assert result["extension"] == ".txt"
    assert "modifiedAt" in result
    # ISO 8601 formatında olmalı
    dt.datetime.fromisoformat(result["modifiedAt"])
    assert "sizeBytes" in result
    assert isinstance(result["sizeBytes"], int)
    assert result["sizeBytes"] > 0
    # Mutlak path İSTEMCİYE SIZDIRILMAMALI (Saga #283)
    assert str(tmp_path) not in result["filename"]


def test_search_endpoint_results_are_sorted_by_filename(tmp_path):
    (tmp_path / "zebra.txt").write_text("z")
    (tmp_path / "apple.txt").write_text("a")
    (tmp_path / "banana.txt").write_text("b")
    session_id = _create_session(selected_folder=str(tmp_path))

    response = client.post(
        "/api/search",
        json={"sessionId": session_id},
    )

    assert response.status_code == 200
    body = response.json()
    filenames = [r["filename"] for r in body["results"]]
    assert filenames == ["apple.txt", "banana.txt", "zebra.txt"]


# --- Saga #314: dosya-icerik-arama-encoding-timeout (RED STEP) ---
# `SearchRequest.contentContains` ve `SearchResponse.partial` alanlari henuz
# YOK. Bu yuzden asagidaki testler ya 422 yerine 200 donerek assertion
# hatasi, ya da KeyError (body'de "contentContains"/"partial" gorulmemesi)
# ile KIRMIZI olmalidir — bu BEKLENEN davranistir (atdd.md AC-1,2,4,9).


def test_search_endpoint_content_contains_matches_utf8_and_latin1_and_cp1254(tmp_path):
    (tmp_path / "utf8.txt").write_text("fatura no 12345 kaydı", encoding="utf-8")
    (tmp_path / "latin1.txt").write_bytes("fatura no 12345 kaydi".encode("latin-1"))
    (tmp_path / "cp1254.txt").write_bytes("fatura no 12345 şirket".encode("cp1254"))
    session_id = _create_session(selected_folder=str(tmp_path))

    response = client.post(
        "/api/search",
        json={"sessionId": session_id, "contentContains": "fatura no 12345"},
    )

    assert response.status_code == 200
    body = response.json()
    filenames = {r["filename"] for r in body["results"]}
    assert filenames == {"utf8.txt", "latin1.txt", "cp1254.txt"}


def test_search_endpoint_content_contains_returns_422_for_empty_string(tmp_path):
    (tmp_path / "dosya.txt").write_text("test")
    session_id = _create_session(selected_folder=str(tmp_path))

    response = client.post(
        "/api/search",
        json={"sessionId": session_id, "contentContains": ""},
    )

    assert response.status_code == 422


def test_search_endpoint_content_contains_returns_422_for_whitespace_only(tmp_path):
    (tmp_path / "dosya.txt").write_text("test")
    session_id = _create_session(selected_folder=str(tmp_path))

    response = client.post(
        "/api/search",
        json={"sessionId": session_id, "contentContains": "   "},
    )

    assert response.status_code == 422


def test_search_endpoint_content_contains_returns_422_when_over_500_chars(tmp_path):
    (tmp_path / "dosya.txt").write_text("test")
    session_id = _create_session(selected_folder=str(tmp_path))

    too_long = "a" * 501
    response = client.post(
        "/api/search",
        json={"sessionId": session_id, "contentContains": too_long},
    )

    assert response.status_code == 422


def test_search_endpoint_content_contains_combines_with_other_filters(tmp_path):
    (tmp_path / "fatura_2024.pdf").write_bytes(b"fatura no 12345")
    (tmp_path / "fatura_2024.txt").write_text("fatura no 12345")
    (tmp_path / "invoice.pdf").write_bytes(b"fatura no 12345")
    session_id = _create_session(selected_folder=str(tmp_path))

    response = client.post(
        "/api/search",
        json={
            "sessionId": session_id,
            "nameContains": "fatura",
            "extension": "pdf",
            "contentContains": "fatura no 12345",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["results"]) == 1
    assert body["results"][0]["filename"] == "fatura_2024.pdf"


def test_search_endpoint_content_contains_binary_and_large_files_are_skipped(tmp_path):
    (tmp_path / "app.exe").write_bytes(bytes(range(256)) * 4)
    (tmp_path / "notes.txt").write_text("fatura no 12345", encoding="utf-8")
    session_id = _create_session(selected_folder=str(tmp_path))

    response = client.post(
        "/api/search",
        json={"sessionId": session_id, "contentContains": "fatura no 12345"},
    )

    assert response.status_code == 200
    body = response.json()
    filenames = {r["filename"] for r in body["results"]}
    assert filenames == {"notes.txt"}


def test_search_endpoint_content_contains_no_match_returns_empty_results(tmp_path):
    """Davranis Sozlesmesi satir 8: hicbir sey bulunamadi ama hata da yok."""
    (tmp_path / "file1.txt").write_text("alakasiz icerik", encoding="utf-8")
    session_id = _create_session(selected_folder=str(tmp_path))

    response = client.post(
        "/api/search",
        json={"sessionId": session_id, "contentContains": "fatura no 12345"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["results"] == []


def test_search_endpoint_content_contains_timeout_returns_partial_true(
    tmp_path, monkeypatch
):
    """AC-2: arama 10sn'yi asarsa 200 + partial:true doner (kismi basari,
    Davranis Sozlesmesi satir 6/7).

    `time.monotonic` mock'lamak yerine `backend.file_search.search_files`
    doğrudan `unittest.mock.patch` ile mock'lanıyor: FastAPI/Starlette/anyio
    threadpool altyapısı endpoint koduna ulaşmadan önce `time.monotonic`'i
    belirsiz sayıda kez çağırdığı için sıraya dayalı bir monkeypatch
    kırılgan. Timeout MANTIĞININ kendisi zaten
    `test_search_times_out_and_returns_partial_flag`
    (backend/tests/test_file_search.py) ile kanıtlanmış; bu test sadece
    endpoint'in `search_files`'ın döndürdüğü `partial` bilgisini doğru
    şekilde `SearchResponse.partial`'a yansıttığını (wiring) doğrular.
    """
    from unittest.mock import patch

    (tmp_path / "dosya.txt").write_text("fatura no 12345", encoding="utf-8")
    session_id = _create_session(selected_folder=str(tmp_path))

    with patch(
        "backend.main.search_files",
        return_value=([], True),
    ):
        response = client.post(
            "/api/search",
            json={"sessionId": session_id, "contentContains": "fatura no 12345"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["partial"] is True
