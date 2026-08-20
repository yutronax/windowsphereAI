# Plan — purge-lock-sertlestirme
_Reference: atdd.md_

## Files to Modify
| File | Why | Risk |
|------|-----|------|
| backend/orchestrator.py | AC-1/AC-2/AC-4: `_claim_transaction_status`'ı (satır 485-516) `OperationalError` için retry ile sarmalayan yeni bir jenerik yardımcı fonksiyon (`_retry_on_operational_error`, `_retry_on_transient_io_error`'ın (satır 91-104) BİREBİR aynı desenini — for-loop + son denemede raise + exponential backoff — DB exception'ı için taklit eder) eklenir. AC-3: `_purge_one_transaction_backup`'taki (satır 1318-1342) `except OSError:` bloğuna `logger.warning(...)` eklenir. Dosyanın başına `import logging` + `from sqlalchemy.exc import OperationalError` eklenir, modül seviyesinde `logger = logging.getLogger(__name__)` (main.py'nin `logger = logging.getLogger(__name__)` deseniyle BİREBİR aynı). | medium |
| backend/tests/test_orchestrator.py | AC-1/AC-2/AC-3/AC-4 için yeni testler: `monkeypatch` ile `session.execute`'un ilk N çağrıda `OperationalError` fırlatıp sonra başarılı olmasını simüle eden retry testleri (`time.sleep`'in de `monkeypatch`'lenmesi ZORUNLU — testin gerçekten ~350ms beklememesi için), `caplog` ile rmtree-başarısızlığı loglama testi. | low |

## New Files
Yok.

## Dependencies
- `backend/orchestrator.py`'nin ZATEN VAR OLAN `_retry_on_transient_io_error`
  deseni (satır 86-104: modül-seviyesi sabitler `_TRANSIENT_IO_MAX_ATTEMPTS`/
  `_TRANSIENT_IO_BACKOFF_SECONDS` + for-loop + `time.sleep(backoff * 2**attempt)`)
  YENİ retry fonksiyonunun BİREBİR taklit edeceği emsal — kod tekrarı
  minimize etmek için AYNI ismi (`_retry_on_...`) ve AYNI yapıyı kullan,
  ama İKİ FARKLI exception türü (OSError+winerror vs OperationalError)
  yakaladığı için TEK bir ortak fonksiyona genelleştirmek bu görevin
  kapsamı DIŞINDA (mevcut IO-retry'ye dokunmadan, paralel yeni bir
  fonksiyon eklemek daha güvenli — regresyon riski sıfır).
- `backend/main.py`'nin `logger = logging.getLogger(__name__)` deseni
  (satır 66) — `orchestrator.py`'de AYNI desen kullanılacak, modülün
  kendi `__name__`'i (`backend.orchestrator`) ile.
- `sqlalchemy.exc.OperationalError` — `sqlalchemy` zaten `requirements.txt`'te
  kurulu (SQLAlchemy'nin kendi exception hiyerarşisi), yeni bir bağımlılık
  gerekmiyor.
- `_claim_transaction_status`'ı çağıran 3 yer (satır 571-573 `revert_transaction`,
  1323-1325/1332-1334/1336-1338 `_purge_one_transaction_backup`) — YENİ
  retry mantığı `_claim_transaction_status`'ın İÇİNE eklenir, bu 3 çağrı
  yeri hiç DEĞİŞMEZ (fonksiyon imzası/dönüş tipi aynı kalıyor, sadece
  içindeki `session.execute`/`session.commit()` çağrısı retry-sarmalı
  hale geliyor).

## Migration Required?
Hayır — sadece Python kod, şema/veri değişikliği yok.

## Risks
- (atdd.md'den taşındı) `time.sleep` kullanan retry testlerinin
  `monkeypatch` ile sıfırlanması ZORUNLU — mevcut `_retry_on_transient_io_error`
  testlerinin (`test_retry_on_transient_io_error_retries_on_winerror_32`
  vb., grep ile bulunabilir) NASIL `time.sleep`'i mock'ladığı test-copilot
  için doğrudan bir referans olmalı (muhtemelen `monkeypatch.setattr(orchestrator.time, "sleep", ...)` ya da benzeri — plan aşamasında tam satırı görülmedi, code-copilot bu mevcut testin gerçek deseninden BİREBİR kopyalamalı).
- `OperationalError`'ın `session.commit()` sırasında mı yoksa
  `session.execute()` sırasında mı fırlayabileceği net değil (SQLite'ın
  kilit davranışına göre değişir) — retry sarmalaması HER İKİSİNİ de
  (execute+commit tek bir "deneme" birimi olarak) kapsamalı, sadece birini
  değil (aksi halde execute başarılı ama commit başarısız olduğunda satır
  yarım-yamalak bir durumda kalabilir — `_claim_transaction_status`'ın
  mevcut `expire_on_commit` try/finally bloğunun İÇİNE değil, o bloğu
  SARAN bir retry döngüsü olmalı).

## Open Questions
Yok — atdd.md'deki kullanıcı onaylarıyla (3 deneme/50-100-200ms backoff,
retry tükenince olduğu gibi fırlat, sadece loglama ekle) kapsam net.
