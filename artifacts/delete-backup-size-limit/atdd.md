# ATDD — DELETE yedek klasörüne toplam boyut sınırı (Saga #312)

## Goal
`backend/orchestrator.py`'deki `purge_expired_delete_backups`'a (veya
yeni, aynı dosyadaki bir fonksiyona) süre-bazlı temizliğe EK olarak bir
toplam-boyut sınırı eklenmeli: `allowed_root/.windows-ai-files-backup/`
altındaki TÜM yedeklerin toplam boyutu bir eşiği (varsayılan 2000 MB)
aşarsa, süresi henüz dolmamış olsa bile EN ESKİ (created_at artan) saf-
DELETE `"committed"` transaction'lardan başlayarak, toplam boyut eşiğin
ALTINA inene kadar veya aday kalmayana kadar purge edilir.

## Acceptance Criteria
1. **P0** — Yeni fonksiyon `purge_oversized_delete_backups(session,
   allowed_root, *, max_total_mb: float = 2000.0) -> list[int]` eklenir.
   Mevcut `purge_expired_delete_backups`'ın imzası/davranışı DEĞİŞMEZ —
   bu ayrı, tamamen ek bir fonksiyon.
2. **P0** — Toplam boyut hesaplaması `allowed_root/.windows-ai-files-backup/`
   altındaki TÜM alt-klasörlerin (her biri bir transaction_id) toplam
   disk kullanımını (`rglob` ile dosya boyutları toplamı) kapsar.
3. **P0** — Toplam boyut `max_total_mb`'yi AŞMIYORSA fonksiyon hiçbir şey
   yapmaz, boş liste döner (dosya sistemine hiç dokunulmaz).
4. **P0** — Aşıyorsa, adaylar (status=="committed", TÜM operasyonları
   DELETE olan, bu `allowed_root` altında backup_dir gerçekten var olan —
   `purge_expired_delete_backups`'taki AYNI filtreleme mantığı) EN ESKİ
   `created_at`ten başlanarak sırayla, toplam boyut eşiğin ALTINA
   İNENE KADAR veya aday tükenene kadar purge edilir.
5. **P0** — Her purge edilen transaction, `purge_expired_delete_backups`
   ile AYNI güvenlik disiplinini kullanır: `_claim_transaction_status`
   ile 3 durumlu CAS (`committed`→`purging`→`backup_purged`), `rmtree`
   KİLİT TUTULMADAN çağrılır, başarısızlıkta telafi edici geri-dönüş.
   Bu mantık `purge_expired_delete_backups`'tan KOPYALANMAZ — ortak bir
   yardımcıya (`_purge_one_transaction_backup` gibi) çıkarılıp HER İKİ
   fonksiyon da onu çağırır (kod tekrarı yok).
6. **P1** — Karışık operasyonlu transaction'lar (DELETE dışı adım içeren)
   PURGE EDİLMEZ — `purge_expired_delete_backups`'taki AYNI kısıtlama.
7. **P1** — Çok-kök senaryosu: `backup_dir.exists()` false olan adaylar
   (başka bir `allowed_root`'a ait) DOKUNULMADAN atlanır.

## Behavior-Contract Table
| Senaryo | Beklenen |
|---|---|
| Toplam boyut < max_total_mb | Hiçbir şey silinmez, boş liste |
| Toplam boyut > max_total_mb, 3 aday (eski→yeni) | En eskiden başlanarak, sınırın altına inene kadar silinir |
| Tüm adaylar silinse bile hâlâ sınırın üstündeyse | Aday tükenince durur, kalan liste döner |
| Karışık operasyonlu transaction | Hiç dokunulmaz, boyut hesabına dahil olmaz (zaten backup_dir yok) |

## Test Strategy
`backend/tests/test_orchestrator.py`'ye eklenir — gerçek dosya sistemi
(tmp_path) ile: birkaç sahte transaction+backup_dir (bilinen boyutlarda
dosyalarla) oluşturulur, fonksiyon çağrılır, hangi transaction'ların
purge edildiği + kalan toplam boyut doğrulanır.

## Risks/Assumptions
- `max_total_mb` varsayılanı (2000 MB) referans projeden fikir alındı
  (kod taşınmadı), konfigüre edilebilir parametre olarak bırakıldı.
- Bu fonksiyon henüz hiçbir scheduler'a bağlanmıyor (mevcut
  `purge_expired_delete_backups`'la AYNI emsal, Saga #286/#287).
