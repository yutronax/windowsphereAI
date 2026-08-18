---
task_slug: apply-plan-endpoint
priority: critical
coverage_target: "yeni kod: happy path + tüm hata dallarında en az 1 test"
performance_target: "N/A (yerel dosya I/O, ağ değil)"
test_strategy: "70/0/30 (unit backend + unit frontend / e2e yok)"
affected_modules: [backend/main.py, backend/models.py, ui/src/App.tsx, ui/src/components/chat/ChatScreen.tsx]
---

# ATDD — Onaylanan planı gerçekten uygulayan apply endpoint'i (Saga #309)

## Persona
Muhasebeci kullanıcı: bir klasördeki PDF'leri aylara göre otomatik
düzenlemek istiyor. Planı görüp onaylıyor, ama şu an hiçbir şey
gerçekten olmuyor — ürünün TEK gerçek değeri (dosyaları fiilen taşımak)
eksik.

## Goal
`POST /api/plan` ile üretilen ve kullanıcı tarafından onaylanan planı,
gerçekten `backend/orchestrator.apply_plan`'a göndererek diskte
uygulayan bir HTTP endpoint'i + bu endpoint'i çağıran frontend wiring'i
eklemek.

## User Story
Muhasebeci olarak, önerilen planı onayladığımda dosyaların gerçekten
taşınmasını ve sonucun (kaç dosya, hangi klasörlere) ekranda
görünmesini istiyorum, ki uygulama gerçekten iş yapsın.

## Sorular ve Cevaplar (saga-oto tarafından otomatik seçildi)

1. **Endpoint'in request body'si ne taşımalı — sadece transactionId mi,
   yoksa tam PlanSkeleton mı?**
   Cevap: Tam `PlanSkeleton` (steps + dateSource + sortOrder), çünkü
   backend henüz "üretilen planı sunucu tarafında session'a bağlı
   sakla" mekanizmasına sahip değil (`/api/plan` planı DÖNDÜRÜR ama
   kaydetmez) — bunu eklemek kapsam dışı bir mimari genişleme olurdu.
   İstemci, `/api/plan`'dan aldığı HAM yanıtı (fileNames dahil, tüm
   alanlarıyla) sakladığı sürece bunu geri gönderebilir.
   (saga-oto tarafından otomatik seçildi — dar kapsam ilkesi: yeni bir
   sunucu-taraflı plan-saklama katmanı EKLEMEMEK.)

2. **Frontend şu an ürettiği planı (`Plan` tipi, PlanCard için) apply
   için yeterli mi?**
   Cevap: HAYIR — `planValidation.ts` sadece `order/operationType/
   targetFolder/affectedFileCount` alanlarını tutuyor, `fileNames`
   (backend'in `apply_plan`i için ZORUNLU) dahil değil. Çözüm: App.tsx
   `/api/plan` yanıtının HAM (doğrulanmadan/budanmadan önceki) JSON
   gövdesini `ChatMessage`e yeni bir `rawPlan` alanıyla ayrıca saklar
   (sadece App.tsx içinde kullanılır, `ChatScreen`/`PlanCard`
   render'ını ETKİLEMEZ — ekrana hâlâ budanmış `Plan` gösterilir).
   `handleApprovePlan` bu `rawPlan`'ı `/api/transactions/apply`e
   gönderir.
   (saga-oto tarafından otomatik seçildi — mevcut render sözleşmesini
   bozmayan en dar veri-taşıma çözümü.)

3. **`allowed_root` nereden gelmeli?**
   Cevap: SUNUCU tarafında, `SessionContext.selectedFolder`'dan — Saga
   #301'in `revert_transaction` için kurduğu ilkeyle birebir aynı,
   istemciden ASLA alınmaz. Session lookup `/api/plan`in kullandığı
   `get_session_or_404` deseniyle aynı (ama farklı bir body şeması
   olduğu için ayrı, küçük bir dependency fonksiyonu — mevcut
   `get_session_or_404`'u genel bir Protocol'e çevirmek gereksiz bir
   refactor olurdu).
   (saga-oto tarafından otomatik seçildi.)

4. **"0 işlem ama başarı" false-positive'i nasıl önlenir?**
   Cevap: `apply_plan` tamamen boş bir `steps` listesini veya sadece
   `LIST` (salt okunur, hiç `FileOperation` üretmeyen) adımlardan oluşan
   bir planı REDDETMİYOR — böyle bir planı sorunsuzca "committed" olarak
   işaretler (0 `FileOperation` ile). Bu tam olarak eski projenin
   "hiçbir dosya işlenmedi ama success döndü" hata sınıfı. Orchestrator
   ATOMIK olduğu için (herhangi bir adım patlarsa TÜMÜ geri alınır, asla
   kısmi "committed" dönmez) gerçek bir kısmi-başarı senaryosu apply_plan
   seviyesinde zaten imkânsız — TEK boşluk, "hiç gerçek işlem içermeyen
   bir plan"ın kendisi. Çözüm: endpoint, `apply_plan`ı ÇAĞIRMADAN ÖNCE,
   planın en az bir `LIST`-DIŞI adım içerip içermediğini kontrol eder;
   yoksa 422 ile reddeder. `apply_plan`in kendisi DEĞİŞTİRİLMEZ.
   (saga-oto tarafından otomatik seçildi — orchestrator.py'ye
   dokunmadan endpoint seviyesinde precondition.)

5. **Geçici I/O hataları (WinError 32/5) için retry gerekli mi?**
   Cevap: `apply_plan` zaten HER dosya operasyonunu tek bir
   try/except'e sarıp, herhangi bir istisnada TÜM tamamlanmış adımları
   ters sırayla geri alıyor (atomik transaction) — bu, "sessiz tek
   deneme başarısızlığı" sınıfını zaten önlüyor (kullanıcı en azından
   NET bir hata + tutarlı bir DB durumu görür, sessiz kısmi başarı YOK).
   Gerçek bir bounded retry-with-backoff (kilitli dosya/AV geçici
   engeli için) `orchestrator.py`nin `_FORWARD_OPERATIONS` dispatch
   noktasına eklenebilir ama bu, "apply_plan'ı yeniden yazma" kapsamına
   giriyor — görev açıkça bunu yasaklıyor. Bu yüzden BU TASK'TA retry
   EKLENMİYOR, sadece davranış-sözleşmesi satırı olarak belgeleniyor
   (aşağıdaki tablo) ve ayrı bir takip-task için Risk olarak not
   düşülüyor.
   (saga-oto tarafından otomatik seçildi — dar kapsam, orchestrator.py
   dokunulmaz.)

6. **Yanıt şekli ResultCard/transactionResult.ts ile nasıl eşleşir?**
   Cevap: `transactionResult.ts`'in beklediği `{status, operations:
   [{destination_path, status}]}` şekli zaten mevcut ve test edilmiş
   (Saga #277) — backend yanıt modeli birebir bunu üretir, artı
   `id` (revert butonu için `transactionId`). App.tsx, `toTransactionResult`
   çıktısına `transactionId: body.id` ekleyerek `message.result`e yazar.
   (saga-oto tarafından otomatik seçildi.)

7. **Path-dışı-allowed_root senaryosu yeniden mi doğrulanmalı?**
   Cevap: `apply_plan` zaten `validate_plan_paths`ı EN BAŞTA çağırıyor
   (Saga #283 deseniyle aynı whitelist mantığı) — endpoint bunu
   TEKRARLAMAZ, sadece `PathWhitelistError`ı yakalayıp 403'e çevirir
   (aynı `/api/plan`'daki gibi, tam path istemciye SIZDIRILMAZ).
   (saga-oto tarafından otomatik seçildi.)

## Kabul Kriterleri (öncelik sırasıyla)

1. **[P0]** Onaylanan bir plan `/api/transactions/apply`e gönderildiğinde
   dosyalar GERÇEKTEN diskte taşınır/kopyalanır/vb. ve yanıt, kaç
   dosyanın işlendiğini + hangi klasörlere gittiğini doğru yansıtır.
2. **[P0]** `allowed_root` her zaman sunucu-taraflı session'dan gelir,
   istemcinin gönderdiği hiçbir alan `allowed_root` olarak KULLANILMAZ.
3. **[P0]** Sadece `LIST` adımlarından oluşan veya boş bir plan 422 ile
   reddedilir — asla "0 dosya işlendi, başarı" şeklinde bir committed
   transaction OLUŞMAZ.
4. **[P1]** allowed_root dışına çıkan bir path içeren plan 403 ile
   reddedilir (mevcut whitelist mantığı korunur, yeniden yazılmaz).
5. **[P1]** Frontend'de "Planı onayla" butonuna basınca gerçekten bu
   endpoint çağrılır ve sonuç `ResultCard` ile render edilir (mevcut
   `onSendMessage`/`/api/plan` wiring deseniyle aynı disiplinde: stale-
   response koruması gerekmez çünkü tek bir onay aksiyonu, ama hata
   durumunda kullanıcıya görünür bir mesaj gösterilir).
6. **[P2]** Geçersiz/bulunamayan session (404) ve artık var olmayan
   klasör (410) durumları `/api/plan`deki gibi ele alınır.

## Davranış Sözleşmesi Tablosu

| Senaryo | Girdi | Beklenen HTTP/Sonuç |
|---|---|---|
| Başarı | Geçerli session + geçerli whitelist içi plan, en az 1 gerçek (LIST-dışı) adım | 200, `status: "committed"`, `operations` gerçekten taşınan dosyaları listeler, `fileCount > 0` |
| Sıfır-işlem reddi | `steps: []` VEYA tüm adımlar `LIST` | 422, hiçbir `Transaction`/`FileOperation` DB'ye YAZILMAZ (apply_plan hiç çağrılmaz) |
| Path whitelist ihlali | Bir adımın `fileNames`'i `pdf_files` taramasında yok / targetFolder whitelist dışı | 403, tam path istemciye sızdırılmaz (sadece `reason`) |
| Kısmi başarı (orchestrator seviyesinde) | Bir adım disk hatasıyla patlar | `apply_plan` TÜM tamamlanmış adımları geri alır, `PlanApplicationError` fırlatır → endpoint bunu yakalayıp `status: "rolled_back"` + boş `operations` ile 200 döner (ResultCard bunu "failed" gösterir, `transactionResult.ts`'in mevcut `rolled_back→failed` eşlemesiyle) — asla "partial success" gibi göstermez |
| Geçici I/O hatası (WinError 32/5, kilitli dosya/AV) | `shutil.move` transient exception fırlatır | `apply_plan`in MEVCUT atomik rollback'i devreye girer (yukarıdaki "Kısmi başarı" satırıyla AYNI davranış) — bu task'ta AYRI bir retry mekanizması EKLENMEZ (bkz. Soru 5), sadece bu satırla davranış sabitlenir |
| Geçersiz session | Bilinmeyen `sessionId` | 404 |
| Klasör artık yok | `session.selectedFolder` diskte yok | 410 |

## Risks / Assumptions / Unknowns

- **Assumption:** İstemcinin `/api/plan` yanıtını olduğu gibi
  (fileNames dahil) sakladığı ve değiştirmeden geri gönderdiği
  varsayılıyor — kullanıcı planı "değiştiremiyor" zaten (mevcut UI'da
  düzenleme yok), bu yüzden round-trip güvenli.
- **Risk (kapsam dışı, gelecek task için not):** 20+ dosyayı etkileyen
  toplu (bulk) işlemler için EK bir onay adımı YOK — bu task bunu
  BİLİNÇLİ OLARAK kapsam dışı bırakıyor (görev tanımında açıkça
  belirtildi). Gelecekte bir "bulk confirm threshold" task'ı
  açılabilir.
- **Risk (kapsam dışı, gelecek task için not):** Gerçek bounded
  retry-with-backoff (kilitli dosya/AV geçici engeli için)
  `orchestrator.py`ye eklenmedi — bu task orchestrator.py'ye
  dokunmuyor. `apply_plan`in mevcut atomik rollback'i "sessiz tek
  deneme başarısızlığı" sınıfını zaten önlediği için P0 değil, ama
  kullanıcı deneyimi (bir kilitli dosya YÜZÜNDEN TÜM planın geri
  alınması) gelecekte bir retry-wrapper task'ı ile iyileştirilebilir.

## Test Strategy
- Backend: `backend/tests/test_main_integration.py`e yeni testler
  (mevcut `TestClient` + in-memory SQLite deseni, `apply_plan`
  import'u zaten orada).
- Frontend: `ui/src/App.test.tsx`e `handleApprovePlan`in gerçekten
  fetch çağırdığını ve `ResultCard`i render ettiğini doğrulayan testler.

## Benchmark
N/A — yerel dosya I/O, performans hedefi yok.
