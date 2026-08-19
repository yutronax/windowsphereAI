"""Saga #337: dosya-arama-ilerleme-gostergesi (RED STEP).

`POST /api/search/scan` ve `GET /api/search/scan/{scan_id}` HENUZ YOK
(backend/main.py'de implementasyon yapilmadi — atdd.md/plan.md'ye gore bu
task'in kod adimi henuz calistirilmadi). Bu dosyadaki TUM testler bu yuzden
KIRMIZI olmalidir: route bulunamadigi icin 404 (route-not-found, session
404'unden AYRI bir sebep) veya `backend.main` icinde olmayan bir isim
(`_scans` gibi) erisilmeye calisildiginda AttributeError.

Referans: artifacts/dosya-arama-ilerleme-gostergesi/atdd.md (AC-1..7, AC-S1)
          artifacts/dosya-arama-ilerleme-gostergesi/plan.md (threading.Thread
          + threading.Lock, lazy cleanup, "zamanlama yerine tamamlanmamis"
          testi onerisi)

Mevcut `/api/search` (senkron) testlerinin fixture/mock deseni
`test_main_integration.py`'den takip edildi — ayri bir dosyada toplanmasinin
sebebi projenin temiz kalmasi (gorev talimati).
"""

import re
import threading
import time
import uuid
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def _create_session(selected_folder: str) -> str:
    response = client.post(
        "/api/session",
        json={"selectedFolder": selected_folder, "requestText": "bir istek"},
    )
    return response.json()["sessionId"]


def _slow_search_files(*args, **kwargs):
    """search_files'i yavaslatan sahte fonksiyon — plan.md'nin AC-1 icin
    onerdigi 'gercek tarama henuz bitmemis' stratejisi, ham ms olcumu degil."""
    time.sleep(0.3)
    return ([], False)


def _instant_search_files(*args, **kwargs):
    return ([], False)


# --- AC-1 [Critical]: POST /api/search/scan yaniti search_files TAMAMLANMADAN doner ---


def test_scan_start_returns_202_and_scan_id_before_search_files_completes(tmp_path):
    session_id = _create_session(str(tmp_path))

    with patch("backend.main.search_files", side_effect=_slow_search_files):
        response = client.post("/api/search/scan", json={"sessionId": session_id})

    assert response.status_code == 202
    body = response.json()
    assert isinstance(body["scanId"], str)
    assert body["scanId"] != ""


# --- AC-2 [Critical]: hemen sonra GET -> status: running ---


def test_scan_status_is_running_immediately_after_start(tmp_path):
    session_id = _create_session(str(tmp_path))

    with patch("backend.main.search_files", side_effect=_slow_search_files):
        start_response = client.post("/api/search/scan", json={"sessionId": session_id})
        scan_id = start_response.json()["scanId"]

        # search_files henuz (0.3sn) bitmeden hemen sorgula.
        status_response = client.get(f"/api/search/scan/{scan_id}")

    assert status_response.status_code == 200
    assert status_response.json()["status"] == "running"


# --- AC-3 [Critical]: tamamlanan tarama -> status: done + results ---


def test_scan_status_is_done_with_results_after_search_files_completes(tmp_path):
    session_id = _create_session(str(tmp_path))

    with patch("backend.main.search_files", side_effect=_instant_search_files):
        start_response = client.post("/api/search/scan", json={"sessionId": session_id})
        scan_id = start_response.json()["scanId"]

        # Arka plan thread'inin bitmesini bekle (gercek zamanlamaya guvenmek
        # yerine kisa bir polling dongusu ile senkronize et).
        deadline = time.monotonic() + 2.0
        status_response = None
        while time.monotonic() < deadline:
            status_response = client.get(f"/api/search/scan/{scan_id}")
            if status_response.json().get("status") == "done":
                break
            time.sleep(0.02)

    assert status_response is not None
    assert status_response.status_code == 200
    body = status_response.json()
    assert body["status"] == "done"
    assert isinstance(body["results"], list)


# --- AC-4 [High]: var olmayan scan_id -> 404 + not_found ---


def test_scan_status_returns_404_not_found_for_unknown_scan_id():
    response = client.get(f"/api/search/scan/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json()["status"] == "not_found"


# --- AC-5 [High]: iki ayri scan -> farkli scan_id, birbirini ezmez ---


def test_two_scans_get_independent_scan_ids_and_can_both_be_queried(tmp_path):
    session_id = _create_session(str(tmp_path))

    with patch("backend.main.search_files", side_effect=_instant_search_files):
        first = client.post("/api/search/scan", json={"sessionId": session_id})
        second = client.post("/api/search/scan", json={"sessionId": session_id})

        first_id = first.json()["scanId"]
        second_id = second.json()["scanId"]
        assert first_id != second_id

        first_status = client.get(f"/api/search/scan/{first_id}")
        second_status = client.get(f"/api/search/scan/{second_id}")

    assert first_status.status_code == 200
    assert second_status.status_code == 200


# --- AC-6 [High]: /api/search/scan gecersiz sessionId/allowed_root -> mevcut /api/search ile BIREBIR ayni ---


def test_scan_start_returns_404_for_unknown_session_id_same_as_sync_search():
    response = client.post(
        "/api/search/scan",
        json={"sessionId": str(uuid.uuid4())},
    )

    assert response.status_code == 404


def test_scan_start_returns_410_when_selected_folder_no_longer_exists_same_as_sync_search(tmp_path):
    missing_folder = tmp_path / "silinmis-klasor"
    session_id = _create_session(str(missing_folder))

    response = client.post(
        "/api/search/scan",
        json={"sessionId": session_id},
    )

    assert response.status_code == 410


# --- AC-7 [Medium]: suresi gecmis bir kayit -> not_found (gercek 5dk beklemeden) ---


def test_scan_status_returns_not_found_for_an_expired_record(tmp_path, monkeypatch):
    """`backend.main._scans` dict'ine dogrudan erisip bir kaydin zaman
    damgasini gecmise cekerek 5 dakikalik temizlik mantigini gercek zaman
    beklemeden simule eder (plan.md'nin lazy-cleanup onerisi)."""
    import backend.main as main_module

    session_id = _create_session(str(tmp_path))

    with patch("backend.main.search_files", side_effect=_instant_search_files):
        start_response = client.post("/api/search/scan", json={"sessionId": session_id})
        scan_id = start_response.json()["scanId"]

        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline:
            if client.get(f"/api/search/scan/{scan_id}").json().get("status") == "done":
                break
            time.sleep(0.02)

    # `_scans` henuz backend.main'de tanimli degil (bu RED step'in bir parcasi) —
    # bu erisim su an AttributeError ile kirmizi olmali.
    scan_record = main_module._scans[scan_id]
    scan_record.completed_at = scan_record.completed_at - 301  # 5 dakikadan fazla gecmis

    response = client.get(f"/api/search/scan/{scan_id}")

    assert response.status_code == 404
    assert response.json()["status"] == "not_found"


# --- Red-team fix [Medium] (artifacts/dosya-arama-ilerleme-gostergesi/red_team.json):
# search_files() beklenmedik bir exception firlatirsa scan sonsuza kadar
# "running" kalmamali, "done" olarak isaretlenmeli ---


def _raising_search_files(*args, **kwargs):
    raise OSError("simulated filesystem error")


def test_scan_status_is_done_not_stuck_running_when_search_files_raises(tmp_path):
    session_id = _create_session(str(tmp_path))

    with patch("backend.main.search_files", side_effect=_raising_search_files):
        start_response = client.post("/api/search/scan", json={"sessionId": session_id})
        scan_id = start_response.json()["scanId"]

        # Arka plan thread'inin (exception yakalayip state'i yazan) bitmesini
        # bekle — gercek zamanlamaya guvenmek yerine kisa bir polling dongusu
        # ile senkronize et (mevcut testlerdeki desenle ayni).
        deadline = time.monotonic() + 2.0
        status_response = None
        while time.monotonic() < deadline:
            status_response = client.get(f"/api/search/scan/{scan_id}")
            if status_response.json().get("status") != "running":
                break
            time.sleep(0.02)

    assert status_response is not None
    assert status_response.status_code == 200
    body = status_response.json()
    assert body["status"] == "done"
    assert body["status"] != "running"


# --- AC-S1 [High]: scan_id tahmin edilemez (uuid), sirali/artan degil ---


_UUID4_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", re.IGNORECASE
)


def test_scan_ids_are_uuid_formatted_not_sequential(tmp_path):
    session_id = _create_session(str(tmp_path))

    with patch("backend.main.search_files", side_effect=_instant_search_files):
        first = client.post("/api/search/scan", json={"sessionId": session_id})
        second = client.post("/api/search/scan", json={"sessionId": session_id})

    first_id = first.json()["scanId"]
    second_id = second.json()["scanId"]

    assert _UUID4_RE.match(first_id), f"scan_id uuid4 formatinda degil: {first_id}"
    assert _UUID4_RE.match(second_id), f"scan_id uuid4 formatinda degil: {second_id}"
    # Sirali/artan bir sayac DEGIL (ornegin "1", "2") — threat-model AC-S1.
    assert first_id != "1" and second_id != "2"
