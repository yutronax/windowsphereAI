# Plan — diff-tray-onizleme-ui
_Reference: atdd.md_

## Files to Modify
| File | Why | Risk |
|------|-----|------|
| backend/models.py | `TransactionSummary`e yeni `preview` alanı eklenecek (AC-2). Mevcut model açıkça "tam path İÇERMEZ, sadece klasör ADLARINI taşır" (Saga #283 ilkesi) diyor — preview de aynı ilkeye uymalı: sadece dosya ADI (`Path(...).name`), tam path yok. | low |
| backend/main.py | `_transaction_to_summary` (main.py:247) preview alanını doldurmalı: `transaction.operations`daki her `FileOperation`den `source_path`/`destination_path`in sadece `.name`ini al, ilk 10 ile sınırla, `empty`/`available`/`unknown` durumlarını hesapla (AC-1..AC-6). | medium |
| ui/src/components/chat/ResultCard.tsx | Hover önizlemesini göstermek için — AMA bkz. Open Questions: bu bileşen şu an SADECE en son tamamlanan tek transaction'ı gösteriyor, çoklu geçmiş listesi değil. | medium |

## New Files
Yok — mevcut şema ve endpoint üzerine alan ekleniyor, yeni dosya gerekmiyor.

## Dependencies
- `db_models.FileOperation.source_path` / `.destination_path` (main.py:44-45) — preview'in "önce/sonra" verisinin tek kaynağı. Tam path DB'de saklı ama istemciye asla gönderilmez (Saga #283 ilkesi, models.py:1024-1027 yorumu) — preview de `Path(...).name` ile sınırlanmalı.
- `db_models.FileOperation.backup_path` (main.py:46) — DELETE operasyonlarında fiziksel yedek yolu; `purge_expired_delete_backups` (orchestrator.py:1380) bunu SÜRESİ DOLUNCA fiziksel olarak siliyor ama **DB satırını silmiyor** (sadece `.windows-ai-files-backup/` klasöründeki dosyayı `shutil.rmtree` ile temizliyor). Bu, atdd.md'nin "snapshot mevcut değil" (`available: false`) senaryosunun gerçek veri modelinde tam karşılığının olmadığı anlamına gelir — bkz. Open Questions #2.
- `_transaction_to_summary` (main.py:247-257) — mevcut path-sızdırmama deseni (`.parent.name`) zaten var, preview aynı deseni `.name` için tekrar kullanmalı.

## Migration Required?
Hayır. `Transaction`/`FileOperation` şemasında yeni kolon gerekmiyor — preview, mevcut `source_path`/`destination_path`/`backup_path` alanlarından istek anında (on-the-fly) hesaplanabilir. Şema değişikliği olmadığı için projenin migration kısıtları (Saga #301 tartışması) burada devreye girmiyor.

## Risks
- (atdd.md'den taşındı) Çok dosyalı transaction'larda <1000ms hedefi aşılabilir — preview hesaplaması DB'den ek sorgu gerektirmiyor (`transaction.operations` zaten relationship ile geliyor), bu riski azaltıyor ama frontend'de N>10 durumunda render maliyeti hâlâ var.
- Path-sızdırma riski: `source_path`/`destination_path`in TAM halinin yanlışlıkla `preview`e konması (örn. `.name` yerine ham path) Saga #283 ilkesini ihlal eder — kod incelemesinde/red-team'de özellikle kontrol edilmeli.

## Open Questions

1. **"Geçmiş paneli" şu an yok.** Kod taramasında GET `/api/transactions` (plural, Saga #294) frontend'de HİÇ tüketilmiyor — `ResultCard.tsx` sadece az önce tamamlanan TEK transaction'ı gösteriyor (`TransactionResult` tipi, App.tsx'ten prop olarak geliyor), çoklu geçmiş transaction listesi yok. atdd.md'nin "ResultCard/geçmiş panelinde göster" ifadesi bu ikisini birlikte anıyor ama epic #28'de ayrı bir "geçmiş listesi UI'ı" task'ı da yok (task_list ile kontrol edildi: #293/#294/#295/#300/#301/#302/#308/#317/#318). Seçenekler:
   - (a) Bu task kapsamına minimal bir "geçmiş listesi" bileşeni (transaction'ları listeleyen, her satırı hover edilebilir) eklemeyi de dahil et — kapsam büyür.
   - (b) Hover'ı sadece ResultCard'ın gösterdiği TEK (en son) transaction'a uygula — "geçmiş" kelimesi yanıltıcı olur ama mevcut UI'a en küçük dokunuşla uyar.
   - (c) Backend'i tamamla (preview alanı), frontend kısmını AYRI bir Saga task'ına böl.
   code-copilot'a geçmeden netleştirilmeli.

2. **"Snapshot mevcut değil" (`available: false`) durumu gerçek veri modelinde ne zaman oluşur?** `FileOperation` DB satırları hiçbir zaman silinmiyor (`purge_expired_delete_backups` sadece fiziksel `backup_path` dosyasını siliyor, satırı değil) — yani `source_path`/`destination_path` string'leri her zaman DB'de mevcut. Bu durumda atdd.md'deki durum 3 (`preview: {available: false, reason: "snapshot_missing"}`) hangi gerçek senaryoda tetiklenir? İki olası yorum:
   - (a) Bu durum aslında hiç oluşmaz — tabloda bırakılabilir ama pratikte "her zaman available: true" olur (gelecekte DB temizliği eklenirse diye savunma amaçlı).
   - (b) "Mevcut değil" aslında DELETE operasyonlarında fiziksel `backup_path` purge edilmişse tetiklenmeli (dosyanın gerçekten geri getirilemeyeceği anlamına gelir) — bu durumda "snapshot_missing" yerine "backup_purged" gibi daha isabetli bir `reason` kullanılmalı ve sadece DELETE+purged operasyonlar için, MOVE/RENAME/COPY için hiç uygulanmamalı.
   Bu ayrım code-copilot'un ne yazacağını doğrudan etkiliyor, netleştirilmeli.

## Kararlar (kullanıcı onayı)

1. **Kapsam: sadece ResultCard.** Hover önizlemesi sadece ResultCard'ın gösterdiği tek (en son) transaction'a uygulanır — çoklu geçmiş listesi ayrı bir Saga task'ına bırakılır (bu task'ın "Files to Modify" listesinden bağımsız bir "geçmiş listesi bileşeni" YAZILMAYACAK).
2. **"Önizleme mevcut değil" sadece purge edilmiş DELETE yedekleri için tetiklenir.** `reason: "backup_purged"` — sadece DELETE operasyonunun `backup_path`i fiziksel olarak silinmişse (`purge_expired_delete_backups` sonrası dosya artık diskte yok) oluşur. MOVE/RENAME/COPY operasyonlarında bu durum hiç tetiklenmez (onlarda `backup_path` kavramı zaten yok/farklı).

Bu kararlar atdd.md'nin Davranış Sözleşmesi tablosuna da yansıtıldı (bkz. atdd.md güncellemesi).
