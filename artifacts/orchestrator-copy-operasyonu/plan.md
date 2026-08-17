# Plan — COPY Operasyonu (Saga #288)

## Dosya: backend/orchestrator.py

1. `_SUPPORTED_OPERATION_TYPES = {OperationType.MOVE, OperationType.COPY}` sabiti ekle,
   "sadece MOVE" kontrolünü bu sete karşı kontrol edecek şekilde güncelle.
2. İleri uygulama döngüsünde `operation_type`'a göre dallan:
   - MOVE: `shutil.move(source, destination)` (mevcut davranış).
   - COPY: `shutil.copy2(source, destination)` (kaynak kalır).
3. Rollback döngüsünü operation_type-aware yap:
   - MOVE: mevcut davranış (`shutil.move(destination, backup_path)`).
   - COPY: `Path(destination_path).unlink()` (hedefteki kopyayı sil, kaynağa dokunma).
   - Her iki dal da aynı `rollback_failed`/`rolled_back` durum mantığını izler.
4. `_forward_operation`/`_rollback_operation` gibi küçük yardımcı fonksiyonlara
   çıkarmak (dispatch), DELETE (Saga #289) task'ının üçüncü bir dal eklemesini
   kolaylaştırır — ATDD'nin riskler bölümünde belirtildi.

## Test
`test_orchestrator.py`'ye COPY başarı + COPY-sonrası-rollback testleri.

## Doğrulama
pytest (backend/tests) tam suite.
