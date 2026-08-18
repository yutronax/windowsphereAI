# Plan — Transient I/O Retry (Saga #310)

## Dosya değişiklikleri
- `backend/orchestrator.py`: yeni `_retry_on_transient_io_error(func, *args, **kwargs)`
  yardımcı fonksiyonu + `_TRANSIENT_IO_WINERRORS`/`_TRANSIENT_IO_MAX_ATTEMPTS`/
  `_TRANSIENT_IO_BACKOFF_SECONDS` sabitleri. `_forward_move`/`_forward_copy`/
  `_forward_delete` içindeki `shutil.move`/`shutil.copy2`/`.unlink()`
  çağrıları bu sarmalayıcıdan geçirildi. `import time` eklendi.
- `backend/tests/test_orchestrator.py`: 5 yeni test
  (`test_retry_on_transient_io_error_*`).

## Yaklaşım
Referans projedeki (`safe_io_call`) fikir alındı, kod taşınmadı — üstel
backoff'lu, en fazla 3 denemeli, sadece WinError 32/5 için retry yapan
minimal bir sarmalayıcı. Kalıcı hatalar (winerror yok veya 32/5 dışı)
davranış değişmeden hemen fırlatılır.

## Araç notu
Test yazımı `aider-bridge` (Ollama + Aider) ile denendi — kısmi başarı,
detaylar `verify_report.md`'de. İmplementasyon (orchestrator.py, büyük
dosya) Aider'ın context sınırını aştığı için Claude tarafından doğrudan
yazıldı.
