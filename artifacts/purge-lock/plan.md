# Plan — purge_expired_delete_backups / revert_transaction row-level kilitleme

## Kapsam
Tek dosya değişikliği: `backend/orchestrator.py`. Şema değişikliği YOK (yeni
kolon eklenmiyor — `status` alanı hem veri hem kilit anahtarı olarak
kullanılıyor, `_add_missing_columns` shim'ini tetiklemez).

## Değişiklikler

### 1. `backend/orchestrator.py` — yeni yardımcı fonksiyon
```python
def _claim_transaction_status(session: Session, transaction_id: int, *, from_status: str, to_status: str) -> bool:
    """Atomik koşullu UPDATE (compare-and-swap): `status` sütununu SADECE
    hâlâ `from_status` ise `to_status`a çevirir ve hemen commit eder.
    SQLite'ta `with_for_update()` desteklenmediği için (Saga #302) bu, iki
    bağımsız session'ın aynı Transaction satırını yarışarak güncellemesini
    engelleyen minimal desen: rowcount==1 → bu session'ın satırı "kilitlediği"
    anlamına gelir, rowcount==0 → satır artık beklenen durumda değil (başka
    bir session onu değiştirdi), çağıran hiçbir dosyaya dokunmadan pes eder."""
    result = session.execute(
        update(Transaction)
        .where(Transaction.id == transaction_id, Transaction.status == from_status)
        .values(status=to_status)
    )
    session.commit()
    return result.rowcount == 1
```
`from sqlalchemy import update` import edilecek (mevcut `select` importunun
yanına).

### 2. `revert_transaction` — claim en başta
- Mevcut `if transaction.status != "committed": raise ...` kontrolünü KORU
  (hızlı/ucuz erken-red — DB'ye gitmeden bariz durumları eler).
- HEMEN ardından atomik claim: `_claim_transaction_status(session,
  transaction.id, from_status="committed", to_status="reverting")`.
  - `False` dönerse: `transaction.status`ı DB'den yenile (`session.refresh
    (transaction)` veya doğrudan mesajda "committed" varsay) ve
    `TransactionRevertError` fırlat — hiçbir `_rollback_completed_operations`
    çağrılmaz.
  - `True` dönerse: `transaction.status = "reverting"` (in-memory senkron,
    ORM nesnesini DB ile hizala) ve devam et.
- Fonksiyonun geri kalanı AYNI kalır (`_rollback_completed_operations` +
  final `transaction.status = "reverted"/"revert_failed"` + `session.commit()`).
  Bu son commit zaten var olan davranışla aynı — artık sadece başlangıç
  durumu `"committed"` değil `"reverting"`.

### 3. `purge_expired_delete_backups` — claim, rmtree'den ÖNCE
- `backup_dir.exists()` kontrolünden SONRA, `shutil.rmtree(backup_dir)`
  çağrısından ÖNCE: `_claim_transaction_status(session, transaction.id,
  from_status="committed", to_status="backup_purged")`.
  - `False` dönerse: `continue` (bu adayı atla, `purged_ids`'e ekleme,
    hiçbir dosyaya dokunma — ATDD tablosundaki "purge, satır az önce revert
    edilmeye başlanmış" senaryosu).
  - `True` dönerse: `shutil.rmtree(backup_dir)` çalıştır, `purged_ids.append
    (transaction.id)`. (`transaction.status` zaten DB'de `"backup_purged"` —
    in-memory nesne de `_claim_transaction_status` içindeki `update()`
    sonrası otomatik senkron OLMAYABİLİR çünkü Core `update()` ORM identity
    map'i otomatik invalide etmez ÖNEMLİ: bu yüzden claim başarılı olduğunda
    `transaction.status = "backup_purged"` satırını da EKLE, mevcut testler
    dönüş değeri `transaction` nesnesinin `.status`ını okumuyor olsa bile
    tutarlılık için.)
- Fonksiyon sonundaki döngü-dışı `session.commit()` KALIR ama artık no-op
  olabilir (her claim zaten kendi commit'ini yapıyor) — zararsız, dokunma.

### 4. Test dosyası
`backend/tests/test_orchestrator.py`e yeni bir test eklenecek (ayrı
subagent tarafından, RED önce): iki bağımsız `Session` nesnesi (aynı
`engine`e bağlı, `sessionmaker`den iki kez `Session()` çağrısıyla) kullanarak
"B'nin claim'i A'nın commit'inden SONRA çalıştırılır" interleaving'i simüle
et. Assert: sadece biri claim kazanır (rowcount==1), diğeri rowcount==0 alır
ve hiçbir dosya sistemi yan etkisi (rmtree / dosya taşıma) tetiklenmez.

## Bağımlılıklar / Migration
Yok — yeni kolon yok, yeni tablo yok. `"reverting"` yeni bir string değer,
şema değişikliği gerektirmiyor (status zaten serbest metin `String`).

## Riskler
- `"reverting"` durumunun `recover_incomplete_transactions` veya başka bir
  yerde YANLIŞLIKLA `"committed"` gibi ele alınmadığını doğrulamak gerekir
  (grep ile kontrol edildi — sadece `revert_transaction` ve
  `purge_expired_delete_backups` `status=="committed"` kontrolü yapıyor).
- Eğer claim başarılı olduktan SONRA `_rollback_completed_operations` bir
  istisna fırlatırsa (dosya sistemi hatası dışında bir şey), transaction
  `"reverting"` durumunda asılı kalabilir — ama mevcut kod zaten
  `_rollback_completed_operations`i try/except İÇİNDE çağırmıyor (sadece
  OSError/ValueError/KeyError kendi içinde yakalanıyor), bu MEVCUT davranışla
  aynı risk profili, bu görevin kapsamı dışı.
