---
task_slug: purge-lock-sertlestirme
jira_id: null
saga_task_id: 308
priority: low
coverage_target: 90
performance_target: "<350ms ek gecikme (retry tükendiğinde)"
memory_target: null
test_strategy:
  unit: 90
  integration: 10
  e2e: 0
affected_modules:
  - backend/orchestrator.py
  - backend/tests/test_orchestrator.py
---

# ATDD — purge-lock-sertlestirme

## Jira Kaynağı
Jira'ya bağlı değil — yerel görev (Saga #308, epic #28 "Undo / Geri Alma
Kullanıcı Arayüzü" altında).

## Persona
Bu deponun geliştiricileri — gelecekte `purge_expired_delete_backups`'ı
bir scheduler'a/cron'a bağlayacak kişi. Ayrıca dolaylı olarak son
kullanıcı — geçici bir DB kilitlenmesi yüzünden bir purge/revert
işleminin sessizce/anlaşılmaz şekilde başarısız olmaması.

## Hedef (Neden)
Saga #302'nin red-team incelemesi 2 low-severity bulgu bıraktı (bloklayıcı
değildi çünkü fonksiyon henüz hiçbir scheduler'a bağlı değildi): (1)
`_claim_transaction_status`'taki compare-and-swap UPDATE, SQLAlchemy
`OperationalError` (DB kilit çakışması/timeout) için hiçbir retry/backoff
içermiyor — geçici bir kilitlenme, tekrar denenirse başarılı olabilecek
bir işlemi gereksiz yere başarısız kılıyor. (2) `_purge_one_transaction_backup`'taki
`rmtree` başarısızlığı sessizce CAS ile geri alınıyor, hiçbir iz/log
bırakmıyor — geliştirici/kullanıcı neden bir transaction'ın purge
edilmediğini asla bilemiyor. Scheduler wiring'i (gelecekteki bir görev)
öncesinde bu iki nokta ele alınmalı.

## User Story
As a bu backend'i işleten/bakımını yapan geliştirici
I want geçici DB kilitlenmelerinin gereksiz yere işlem başarısızlığına yol
açmamasını VE rmtree başarısızlıklarının sessizce kaybolmamasını
So that scheduler'a bağlandığında bu iki nokta gizli, iz bırakmayan
hatalara dönüşmesin

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. [Critical] Given `_claim_transaction_status` çağrılırken `session.execute`/
   `session.commit()` bir `OperationalError` fırlatır, When bu geçicidir ve
   3 deneme içinde (50ms/100ms/200ms exponential backoff ile) başarılı
   olur, Then fonksiyon normal `bool` sonucunu döner — çağıran taraf
   hiçbir farkı görmez.
2. [High] Given `OperationalError` 3 denemenin HEPSİNDE de tekrarlanırsa,
   When retry tükenir, Then `OperationalError` OLDUĞU GİBİ (sarmalanmadan/
   yutulmadan) çağırana yükselir — `revert_transaction`/
   `_purge_one_transaction_backup` bu görevin kapsamında YENİ bir except
   eklemez, hata olduğu gibi yükselmeye devam eder.
3. [High] Given `_purge_one_transaction_backup`'ta `shutil.rmtree` bir
   `OSError` fırlatır, When bu yakalanıp CAS ile `"purging"`→`"committed"`e
   geri dönülür (mevcut davranış DEĞİŞMEZ), Then `logging.warning` ile
   transaction id'si VE hata mesajı loglanır — sessiz kaybolma YOK.
4. [Medium] Given `_claim_transaction_status`'a verilen `from_status`/
   `to_status` zaten TUTMUYORSA (rowcount=0, normal "yarışı kaybettik"
   senaryosu — OperationalError DEĞİL), When fonksiyon çalışır, Then
   mevcut davranış (retry YAPMADAN, sadece `False` dönmek) AYNEN korunur
   — bu, OperationalError'dan TAMAMEN farklı bir durumdur, retry mantığı
   SADECE OperationalError'a uygulanır.

## Davranış Sözleşmesi (hangi durumda ne döner)
| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path: claim ilk denemede başarılı | `True` (rowcount==1) | DB satırı güncellenir | Etkilenmez (mevcut davranış) | — |
| 2 | Girdi geçersiz: rowcount==0 (yarış kaybedildi, from_status artık tutmuyor) | `False` | Yok | Çağıran fonksiyon kendi mantığına göre devam eder (mevcut davranış) | AC-4 |
| 3 | Kaynak yok: transaction_id DB'de yok | `False` (rowcount==0, `from_status` eşleşmez) | Yok | Aynı (case 2 ile aynı yol) | AC-4 |
| 4 | Yetkisiz erişim | Uygulanmıyor — tek kullanıcılı masaüstü uygulaması, DB seviyesinde yetkilendirme yok. | — | — | — |
| 5 | Dış bağımlılık hatası: `OperationalError` geçici (ör. eşzamanlı bir başka session kilit tutuyor) | 3 deneme içinde başarılı olursa normal `bool`; hepsi başarısız olursa `OperationalError` yükselir | Retry sırasında hiçbir yarım-yamalak DB yazısı olmaz (her deneme kendi tam UPDATE+commit'i) | Geçiciyse fark etmez; kalıcıysa çağıran tarafın (gelecekteki API/scheduler) hata işleme mantığına düşer | AC-1, AC-2 |
| 6 | Zaman aşımı | `OperationalError`'ın bir alt-sınıfı/nedeni olarak ele alınır — case 5 ile aynı yol, ayrı bir dal YOK. | — | — | AC-1, AC-2 |
| 7 | **Kısmi başarı**: `rmtree` bazı dosyaları sildi ama tamamlanamadan hata verdi | `OSError` yakalanır, CAS `"committed"`e geri döner (mevcut davranış), YENİ: `logging.warning` ile loglanır | Backup klasörü kısmen silinmiş kalabilir (dosya sisteminin kendi davranışı, bu görev bunu DEĞİŞTİRMİYOR) | Loglanır ama kullanıcıya bir hata GÖSTERİLMEZ (bu fonksiyon henüz hiçbir API/UI'a bağlı değil) | AC-3 |
| 8 | **Hiçbir şey yapılamadı ama hata da yok** | Olanaksız — `_claim_transaction_status` ya `True`/`False` döner ya `OperationalError` fırlatır (retry tükendiğinde); `_purge_one_transaction_backup` ya `True`/`False` döner, sessiz "başarı" görünümü üretecek bir dal YOK (loglama eklenmesiyle case 7 zaten "sessiz" olmaktan çıkıyor). | — | — | AC-3 |

Kısmi başarı: 7. satırda tanımlı — mevcut CAS geri-dönüş davranışı
korunuyor, sadece loglama ekleniyor (davranışsal değişiklik yok, gözlemlenebilirlik
ekleniyor).
Hiçbir şey yapılamadı ama hata da yok: Olanaksız — case 8'de açıklandığı
gibi her yol ya sonuç döner ya hata fırlatır, üçüncü sessiz bir dal yok.
Boş sonuç ↔ hata ayrımı: Uygulanmıyor — bu fonksiyonlar bir sorgu/liste
döndürmüyor, `bool`/exception ikiliği yeterli.

## Test Strategy
Unit: 90% — `_claim_transaction_status`'ın retry mantığı `monkeypatch`
ile `session.execute`'un ilk N çağrıda `OperationalError` fırlatıp
sonra başarılı olmasını simüle ederek test edilir (gerçek zaman
beklemeden — `time.sleep`'i de `monkeypatch`'leyerek testin saniyeler
sürmesi engellenir). `_purge_one_transaction_backup`'ın loglama davranışı
`caplog`/`monkeypatch` ile `shutil.rmtree`'yi `OSError` fırlatacak şekilde
simüle ederek test edilir.
Integration: 10% — gerçek SQLite DB ile normal happy-path claim + gerçek
bir dosya sistemi rmtree başarısızlığı (ör. dosyayı açık tutarak Windows'ta
kilitleme — eğer pratikte zorsa, mock ile integration seviyesinde
`purge_expired_delete_backups`'ın tüm zincirini test etmek yeterli).
E2E: 0% — backend-only, UI/API'a henüz bağlı değil (kullanıcı onayı,
kabul kriteri otomatik testlerle sağlanıyor).

## Benchmark / Başarı Ölçütü
Coverage Target: 90% (değişen kod yollarına göre).
Performance Target: retry tükendiğinde toplam ek gecikme <350ms (50+100+200ms).
Diğer ölçülebilir kriterler:
- Retry mantığı gerçek zaman beklemeden (mock'lanmış `time.sleep`) test
  edilebilir olmalı — test süitinin saniyeler sürmesi kabul edilemez.
- `_claim_transaction_status`'ın mevcut TÜM davranışı (rowcount==0/1
  senaryoları) regresyonsuz kalmalı.

## Kapsam Dışı
- `revert_transaction`/`purge_expired_delete_backups` seviyesinde YENİ bir
  hata yakalama/fallback mekanizması — bu görev SADECE `_claim_transaction_status`
  ve `_purge_one_transaction_backup`'ın içini sertleştiriyor, çağıran
  fonksiyonlar `OperationalError`'ı olduğu gibi görmeye devam eder
  (kullanıcı onayı).
- Scheduler/cron wiring'i (gelecekteki bir Saga #286/#287 benzeri görev) —
  bu görev sadece scheduler'a bağlanmadan ÖNCE gereken sertleştirmeyi
  yapıyor, bağlama işi ayrı.
- Kalıcı bir "başarısız-purge deneme sayısı" DB kaydı — sadece loglama
  yeterli kabul edildi (kullanıcı onayı), şema değişikliği yok.
- `purge_oversized_delete_backups`'ın (Saga #312, `_purge_one_transaction_backup`'ı
  ZATEN paylaşan ayrı bir fonksiyon) kendi mantığına dokunmak — paylaşılan
  `_purge_one_transaction_backup`'a yapılan düzeltme otomatik olarak onu
  da kapsar, ayrı bir değişiklik gerekmiyor.

## Etkilenen Dosyalar/Modüller (bilinen)
- `backend/orchestrator.py` (`_claim_transaction_status` satır 485-516,
  `_purge_one_transaction_backup` satır 1318-1342)
- `backend/tests/test_orchestrator.py` (yeni testler)

## Rollback Beklentisi
Hata durumunda (retry tükenmesi) `OperationalError` olduğu gibi yükselir
— DB'de hiçbir yarım-yamalak yazı kalmaz çünkü her deneme kendi tam
UPDATE+commit döngüsü (ya tam başarılı ya hiç). `rmtree` başarısızlığında
mevcut CAS geri-dönüş davranışı (transaction `"committed"`e geri döner)
değişmiyor — bu görev sadece görünürlük (loglama) ekliyor.

## Risks
- SQLite'ın gerçek `OperationalError` fırlatma davranışı ortam/versiyon
  bağımlı olabilir — test-copilot'un gerçek bir eşzamanlı erişim senaryosu
  kurması (2 thread/process aynı satırı claim etmeye çalışırken) zor
  olabilir, bu yüzden Test Strategy'de `monkeypatch` tabanlı simülasyon
  tercih edildi (gerçek race condition'ı üretmek yerine).
- `time.sleep` kullanan bir retry mantığı test'lerde yavaşlığa yol
  açmamalı — `monkeypatch` ile sıfırlanmalı, plan/code-copilot aşamasında
  bu dikkate alınmalı.

## Assumptions
- Retry backoff değerleri (50ms/100ms/200ms) kullanıcı onayıyla
  belirlendi, SQLite'ın tipik kilitlenme sürelerine göre makul bir
  tahmindir — gerçek prod ortamında ayarlanması gerekebilir (bu görevin
  kapsamı dışı, sabit değer olarak başlanıyor).

## Unknowns
- Yok — kullanıcı onaylarıyla kapsam net.

## Sorular ve Cevaplar (ham kayıt)
1. OperationalError davranışı? → 3 deneme + kısa backoff, sonra fırlat.
2. rmtree loglama? → `logging.warning`, mevcut CAS davranışı değişmez.
3. Guard kapsamı genişletilmeli mi? → Hayır, mevcut `except OSError` zaten
   yeterli geniş, asıl eksik loglamaydı.
4. Test stratejisi? → unit %90 / integration %10 / e2e %0.
5. Retry parametreleri? → 3 deneme, 50ms/100ms/200ms exponential backoff.
6. Çağıran fonksiyonlar (revert_transaction vb.) yeni bir fallback eklemeli
   mi? → Hayır, OperationalError olduğu gibi yükselsin, bu görevin kapsamı
   dışı.
7. Kabul kriteri sahibi? → Otomatik testler yeterli (backend-only, UI yok).
8. Persona/Hedef/Happy path/Bağımlılıklar → Saga #308 görev açıklamasından
   (kullanıcı mesajından, tekrar sorulmadı).
