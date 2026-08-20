# Code Diff — purge-lock-sertlestirme

Codex kotası dolu olduğu için (15 Eylül 2026'ya kadar) bu değişiklik
kullanıcı onayıyla Claude Haiku alt ajanı (`efektor` subagent) tarafından
yazıldı, commit atmadı (doğrulandı).

## Değiştirilen dosyalar
- `backend/orchestrator.py`:
  - `import logging`, `from sqlalchemy.exc import OperationalError`,
    `logger = logging.getLogger(__name__)` eklendi (main.py'nin deseniyle
    tutarlı).
  - `_OPERATIONAL_ERROR_MAX_ATTEMPTS`/`_OPERATIONAL_ERROR_BACKOFF_SECONDS` +
    `_retry_on_operational_error` — `_retry_on_transient_io_error`'ın
    (satır 91-104) birebir aynı deseni, `OperationalError` için (AC-1/AC-2).
  - `_claim_transaction_status`: `session.execute`+`session.commit()`
    TEK bir closure'a (`_do_claim`) sarılıp `_retry_on_operational_error`
    ile çağrılıyor — plan.md'nin özellikle vurguladığı "execute+commit
    tek deneme birimi olmalı" riski doğru ele alınmış (kod okunarak
    doğrulandı, satır 536-544).
  - `_purge_one_transaction_backup`: `except OSError` bloğuna
    `logger.warning(transaction.id, exc)` eklendi, mevcut CAS geri-dönüş
    davranışı korunmuş (AC-3, kod okunarak doğrulandı, satır 1361-1366).
- `backend/tests/test_orchestrator.py`: 4 yeni test.

## Doğrulama
```
./.venv/Scripts/python.exe -m pytest backend/tests/test_orchestrator.py -k "retry_on_operational_error or purge_one_transaction or claim_transaction_status_retries" -v
4 passed

./.venv/Scripts/python.exe -m pytest backend/
574 passed, 5 skipped in 38.47s
```
Bağımsız olarak (subagent raporundan ayrı) yeniden çalıştırıldı, 0 FAIL.

## Red-team follow-up: test-gap'lar kapatıldı + gizli bir test-hatası bulundu
Bağımsız red-team turu koordinatörün 2 test-gap bulgusunu doğruladı.
Koordinatör (alt ajanın oturum limitine takılma riskini almadan) bu iki
küçük/mekanik testi kendisi ekledi:
- `test_purge_one_transaction_backup_logs_warning_on_rmtree_failure` —
  `caplog` ile transaction id + hata mesajının gerçekten loglandığını
  kanıtlıyor (AC-3).
- `test_claim_transaction_status_integration_retries_via_session_execute` —
  `session.execute`'u (sadece `Update` sorgularını hedefleyerek, ORM'nin
  iç SELECT'lerine dokunmadan) monkeypatch'leyip `_claim_transaction_status`'ın
  KENDİSİNİN retry mekanizmasına gerçekten bağlı olduğunu kanıtlıyor (AC-1).

**Bu testleri yazarken gizli bir ikinci hata bulundu:** mevcut
`test_purge_one_transaction_backup_returns_false_on_rmtree_failure`
testi, `_purge_one_transaction_backup`'ı çağırmadan ÖNCE transaction'ı
elle `"purging"`e taşıyordu — bu, fonksiyonun KENDİ İÇ claim'inin
(committed→purging) hemen başarısız olup `rmtree`'ye HİÇ ulaşmadan
`False` dönmesine yol açıyordu. Test PASS oluyordu ama iddia ettiği
senaryoyu (rmtree başarısızlığı) hiç tetiklemiyordu — sahte-yeşil bir
test. Düzeltildi: transaction artık `"committed"` bırakılıyor, gerçek
rmtree-başarısızlığı yolu tetikleniyor, `transaction.status == "committed"`
(CAS geri-dönüşü) ek olarak assert ediliyor.

Bağımsız olarak doğrulandı: `pytest -k "purge_one_transaction or
claim_transaction_status or retry_on_operational_error"` → 6/6 PASS,
tüm suite → 576 passed, 5 skipped, 0 FAIL.
