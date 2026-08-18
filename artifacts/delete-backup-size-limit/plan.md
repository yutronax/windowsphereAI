# Plan — DELETE yedek toplam boyut sınırı (Saga #312)

## Dosya değişiklikleri
- `backend/orchestrator.py`:
  - Ortak yardımcı `_purge_one_transaction_backup(session, transaction,
    backup_dir) -> bool` — mevcut `purge_expired_delete_backups`'ın CAS+
    rmtree gövdesi buraya çıkarılır (başarılıysa True, transaction.status
    "backup_purged" olur).
  - `purge_expired_delete_backups` bu yardımcıyı çağıracak şekilde
    refactor edilir (davranış DEĞİŞMEZ, sadece kod tekrarı kaldırılır).
  - Yeni `purge_oversized_delete_backups(session, allowed_root, *,
    max_total_mb=2000.0) -> list[int]` — adayları created_at artan
    sırayla toplar, toplam boyutu `_purge_backup_dir_size_mb` gibi bir
    yardımcıyla hesaplar, eşik altına inene kadar `_purge_one_transaction_backup`'ı
    çağırır.
- `backend/tests/test_orchestrator.py`: yeni testler.

## Sıra
1. Test yazımı (Haiku subagent, red) — atdd.md'yi hedefler.
2. İmplementasyon (Haiku subagent, green) — testleri geçirir.
3. Ana oturum: gerçek pytest çalıştırması, git diff incelemesi (düşük
   risk, sadece purge mantığı genişliyor, gerçek kullanıcı-tetikli bir
   endpoint'e bağlı değil).
