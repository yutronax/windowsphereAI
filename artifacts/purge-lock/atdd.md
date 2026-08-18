---
task_slug: purge-lock
priority: low
coverage_target: race-path only (concurrent revert_transaction vs purge_expired_delete_backups)
performance_target: n/a (correctness fix, no perf requirement)
test_strategy: two-DB-session simulation using raw sqlite3 connections / two SQLAlchemy sessions against the same sqlite file, interleaved manually (no real threads needed since SQLite serializes writes — the test proves the ORM-level compare-and-swap, not OS-level thread safety)
affected_modules: [backend/orchestrator.py]
---

# ATDD — purge_expired_delete_backups / revert_transaction row-level kilitleme

Saga task #302 (epic #28, low priority). Kaynak: Saga #300 red-team bulgusu
(medium, bloklayıcı değil — fonksiyon henüz hiçbir scheduler'a bağlı değil).
Bu görev, GELECEKTEKİ bir cron/scheduler bağlama işinden ÖNCE, iki bağımsız
DB session'ının aynı `Transaction` satırını yarışarak güncellemesini
(lost-update) önleyecek kilitlemeyi ekliyor.

## Persona
Bir kullanıcı `/api/transactions/{id}/revert` çağırdığı ANDA, (gelecekte
bağlanacak) bir arka plan scheduler'ı da aynı transaction için
`purge_expired_delete_backups`'ı çalıştırıyor olabilir.

## Goal
İki bağımsız DB session'ı aynı `Transaction.id` üzerinde `status == "committed"`
şartını AYNI ANDA doğru okuyup, biri "reverted" biri "backup_purged" yazarak
DB'yi tutarsız/kayıp-güncelleme durumuna düşürmesin.

## User Story
Bir DELETE-only transaction hem revert edilmeye hem purge edilmeye
çalışıldığında, sadece BİRİ başarılı olmalı; diğeri temiz bir "çakışma"
hatası almalı (dosya sistemi bozulmamalı, DB tutarsız durumda kalmamalı).

## Kabul Kriterleri (öncelik sırası)

1. **(P0)** `revert_transaction`, transaction'ı `"committed"`dan işleme
   almadan önce ATOMİK bir koşullu UPDATE (`WHERE id=? AND status='committed'`)
   ile satırı "claim" eder. rowcount == 0 ise (satır artık `"committed"`
   değil — örn. az önce purge edilmiş veya zaten revert edilmiş) HİÇBİR
   dosyaya dokunmadan `TransactionRevertError` fırlatır.
2. **(P0)** `purge_expired_delete_backups`, fiziksel `shutil.rmtree` işleminden
   ÖNCE aynı atomik koşullu UPDATE deseniyle transaction'ı claim eder
   (`WHERE id=? AND status='committed'` → yeni bir ara durum). rowcount == 0
   ise (örn. tam o anda revert edilmeye başlanmış) o adayı ATLAR — hiçbir
   dosya silmez, transaction'a dokunmaz.
3. **(P1)** İki fonksiyondan sadece BİRİ claim'i kazanabilir (aynı satır için
   aynı anda iki başarılı claim mümkün değil) — bu, ORM seviyesinde
   `session.execute(update(...).where(...))` + `result.rowcount` kontrolüyle
   kanıtlanır (SQLite dosya seviyesinde zaten writer'ları serialize eder;
   testin kanıtladığı şey ORM'in "oku-sonra-yaz" yerine "koşullu-yaz" deseni
   kullandığıdır).
4. **(P2)** Var olan tüm davranış (başarılı revert, başarılı purge, mixed-op
   transaction'ların atlanması, farklı `allowed_root` koruması — Saga #300)
   AYNEN korunur; regression yok.

## Davranış Sözleşmesi Tablosu

| Senaryo | Girdi durumu | Beklenen sonuç |
|---|---|---|
| Normal revert (yarış yok) | `status="committed"` | claim başarılı → revert çalışır → `status="reverted"`/`"revert_failed"` |
| Normal purge (yarış yok) | `status="committed"`, DELETE-only, backup_dir var | claim başarılı → `rmtree` çalışır → `status="backup_purged"` |
| Revert, satır az önce purge edilmiş | `status="backup_purged"` (başka session commit etti) | claim rowcount=0 → `TransactionRevertError`, hiçbir dosyaya dokunulmaz |
| Purge, satır az önce revert edilmeye başlanmış (claim edilmiş) | `status` artık `"committed"` değil | claim rowcount=0 → o transaction atlanır, `purged_ids`'e girmez, hiçbir dosya silinmez |
| Purge, transaction zaten `"backup_purged"` | `status="backup_purged"` | zaten `WHERE status='committed'` filtresine girmediği için baştan aday bile değil |

## Riskler / Varsayımlar / Bilinmeyenler
- **(saga-oto tarafından otomatik seçildi)** DB engine: SQLite (backend/db.py
  → `sqlite:///...app.db`). SQLAlchemy `with_for_update()` SQLite'ta
  desteklenmiyor (no-op/hataya yakın) — bu yüzden **koşullu UPDATE
  (compare-and-swap: `UPDATE ... SET status=X WHERE id=? AND status=Y`,
  `result.rowcount` kontrolü)** deseni seçildi. Bu, ek bir versiyon
  kolonu gerektirmez, mevcut `status` alanını hem veri hem de kilit
  olarak kullanır — minimal, mevcut şemayla uyumlu.
- **(saga-oto tarafından otomatik seçildi)** `revert_transaction` için ara
  durum adı `"reverting"` seçildi (sonunda `"reverted"`/`"revert_failed"`e
  geçer). Bu yeni durumun başka hiçbir yerde (`recover_incomplete_transactions`,
  UI) `status=="committed"` varsayımını bozmadığı doğrulandı — sadece
  `revert_transaction` ve `purge_expired_delete_backups`in kendi
  guard'ları `"committed"` kontrolü yapıyor.
- Gerçek çoklu-thread/çoklu-process testi bu MVP kapsamı dışı (fonksiyon
  henüz hiçbir scheduler'a bağlı değil) — test, iki bağımsız `Session`
  nesnesiyle manuel interleaving simüle eder (B'nin claim UPDATE'i A'nın
  claim'inden SONRA çalıştırılır, A'nın commit'i B'nin execute'undan ÖNCE
  tamamlanmış olur — gerçekçi "az farkla kaybetme" senaryosu).
