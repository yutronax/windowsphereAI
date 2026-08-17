# AI_DEVLOG.md — windows-ai-files

## sqlite-fileoperation-backup-kaydi (Saga #275, epic #25)

**İlk persistence katmanı: SQLAlchemy ORM ile `Transaction`/`FileOperation`.**
`backend/db_models.py`'ye iki tablo eklendi — `Transaction` (id, created_at,
status: pending/committed/rolled_back) ve `FileOperation` (id,
transaction_id FK, operation_type, source_path, destination_path,
backup_path nullable, created_at, status). `backend/db.py`
(`db_path()` → `%APPDATA%\windows-ai-files\app.db`, `config.py`'deki
`config_path()` deseniyle tutarlı) ve `backend/file_operations.py`
(`create_transaction`/`record_file_operation`/`list_file_operations`
CRUD fonksiyonları) eklendi.

**Bilinçli kapsam kararı: gerçek dosya I/O YOK.** Henüz plan-uygulama
(apply/execute) endpoint'i projede yok (Saga #273/#274 hâlâ `todo`) — bu
task SADECE veri modelini/persistence'ı kurdu, `FileOperation` kayıtları
şimdilik hiçbir yerden gerçek bir taşıma sonrası oluşturulmuyor. Gerçek
Orchestrator entegrasyonu Saga #274'e bırakıldı. SQLAlchemy proje
ortamında zaten kuruluydu (2.0.49) ama hiçbir yerde pin'lenmemişti —
requirements.txt eklemek bu task'ın kapsamı dışında tutuldu (projede hiç
Python bağımlılık dosyası yok, bu ayrı ve daha büyük bir konu). 77/77
test yeşil.

## path-derinlik-ve-sistem-klasoru-korumasi (Saga #272, epic #25)

**Security Gate'e iki yeni kural: azami derinlik + kesin sistem kökleri.**
`backend/security.py`'ye `is_path_too_deep` (allowed_root'a göre relative
path bileşen sayısı `MAX_PATH_DEPTH=3`'ü aşarsa reddet) ve
`is_system_protected` eklendi; `validate_plan_paths` her kaynak/hedef için
artık üç kontrolü de (whitelist → sistem-kök → derinlik) sırayla uyguluyor,
`_validate_single_path` yardımcı fonksiyonuyla tekrar önlendi.

**Gerçek bir tasarım hatası test sırasında yakalandı ve düzeltildi.** İlk
yaklaşım "sistem klasörü" tespitini path bileşenlerinde `"appdata"`,
`"programdata"` gibi anahtar kelime arayarak yapıyordu — bu, `allowed_root`
kendisi bu isimlerden birini içeren bir yol altında olduğunda (pytest'in
`tmp_path`'i `%LOCALAPPDATA%\Temp` altında yaşıyor, gerçek dünyada
taşınabilir kurulumlar da benzer olabilir) MEŞRU yolları da reddediyordu —
`test_validate_plan_paths_passes_for_valid_plan` bunu hemen ortaya çıkardı.
Düzeltme: segment-adı eşleştirmesi yerine `%WINDIR%`/`%ProgramFiles%`/
`%ProgramData%`/`$Recycle.Bin` gibi KESİN mutlak kök dizinlerin altında
olup olmadığını `is_path_allowed` ile kontrol eden bir yaklaşıma geçildi;
`%APPDATA%`/`%LOCALAPPDATA%` kasıtlı olarak listeye alınmadı (kullanıcı
verisi de barındırabilirler, whitelist kökü zaten kapsam dışına çıkışı
engelliyor).

**Red-team: 2 bulgu, ikisi de hemen düzeltildi.** (1) Derinlik/traversal
istismarının tek gerçek yüzeyi `pdfFiles[].filename`di ama sadece
runtime'da (security.py) yakalanıyordu — `models.py`'ye
`filename_has_no_path_separators` validator'ı eklendi, artık `/`/`\`
içeren filename'ler şema seviyesinde 422 ile erkenden reddediliyor;
runtime whitelist/derinlik kontrolü artık TEK savunma değil, gerçek bir
defense-in-depth katmanı (tek segmentlik `".."` hâlâ 403 ile whitelist'te
yakalanıyor). (2) `_system_protected_roots()` prod'da (gerçek Windows)
`WINDIR`/`ProgramFiles`/`ProgramData` env değişkenlerinden biri eksikse
sessizce o kök için korumasız kalıyordu — `_warn_if_protected_roots_missing`
ile en az bir kez WARNING logu eklendi, sessiz devre-dışı kalma riski artık
loglanıyor. 70/70 test yeşil.

## allowed-paths-whitelist-security-gate (Saga #271, epic #25)

**İlk Security Gate: `backend/security.py` — canonical path whitelist.**
`is_path_allowed(path, allowed_root)` `Path.resolve()` + `is_relative_to`
kullanıyor (string prefix karşılaştırması DEĞİL — `/allowed` ile
`/allowed-but-not-really` gibi kardeş-dizin sızıntısını önlemek için).
`validate_plan_paths(plan, pdf_files, allowed_root)` her `PdfFileMetadata.
filename`'i (kaynak) ve her `PlanStep.targetFolder`'ı (hedef) sırayla
kontrol ediyor, İLK ihlalde `PathWhitelistError` fırlatıp tüm planı
reddediyor (tek adım reddi değil).

**`POST /api/plan` artık `sessionId`'yi çözüyor.** Önceden endpoint hiç
oturum aramıyordu (`sessionId` sadece echo edilen bir string'di) — bu, plan
üretimini `selectedFolder`'dan (whitelist kökü) tamamen kopuk bırakıyordu.
Şimdi `_sessions`'tan oturum aranıyor (yoksa 404), plan üretildikten sonra
`session.selectedFolder` kök alınarak `validate_plan_paths` çağrılıyor
(ihlalde 403). Mevcut 4 testte (rastgele `sessionId` kullanan) bu nedenle
gerçek bir regresyon çıktı — testler önce `/api/session` ile gerçek bir
oturum oluşturacak şekilde güncellendi.

**Red-team: path traversal bypass bulunamadı, 3 düşük-önem bulgu.**
Windows'ta mutlak path (`C:\Windows\evil.pdf`) veya UNC/backslash-önekli
filename ile bypass denendi — pathlib'in `root / mutlak_path` davranışı
(mutlak operand join'i tamamen ezer) sonucu `is_path_allowed` doğru
reddediyor, gerçek bir açık yok. Düşük-önem bulgular: (1) `targetFolder`
dalı `TARGET_FOLDER_PATTERN` (YYYY-MM) regex'i tarafından zaten API
seviyesinde engellendiği için ulaşılamaz/test edilmemiş ölü koddu —
`PlanStep.model_construct`/`PlanSkeleton.model_construct` ile alan
doğrulamasını atlayan doğrudan bir unit test eklendi. (2) 403 detail
mesajı ham dosya adını/hedef klasörü istemciye yansıtıyor — bugün
exploit edilebilir değil (zaten kendi girdisi), ama gelecekte mesaj
genişletilirse bilgi sızıntısı riski taşıyor, not edildi. (3) Session-lookup
+ whitelist deseni şu an sadece `/api/plan`'a özel — genelleştirilmiş bir
FastAPI dependency değil; bu mimari iyileştirme Saga #283'e (bu task'a
bağımlı, low priority) ayrı task olarak açıldı, #271'i bloklamadı.
62/62 test yeşil.

## plan-tarih-kaynagi-klasor-yapisi-dogrulama (Saga #270, epic #25)

**Plan şeması sıkılaştırıldı — belirsiz plan artık Security'ye geçemiyor.**
`PlanSkeleton`'a zorunlu `dateSource` (`DateSource` enum, tek üye
`created_at`) ve `sortOrder` (`ascending`|`descending`) alanları eklendi;
`PlanStep.targetFolder` artık `YYYY-MM` regex'ine uymak zorunda. Bu alanlar
eksik/geçersizse Pydantic `ValidationError` fırlatıyor, Saga #269'un zaten
var olan `PlanGenerationError` mekanizmasıyla plan Security katmanına
(#271/#272, henüz yazılmadı) hiç ulaşmıyor.

**Red-team: 2 düşük-önemli bulgu, hemen düzeltildi.** (1) Regex "2026-13"
gibi geçersiz ayları kabul ediyordu — bu, kullanıcının onaylamadan önce
göreceği SON kapsam bilgisi olduğu için gerçek bir boşluktu; ay aralığını
(01-12) doğrulayacak şekilde sıkılaştırıldı. (2) Boş-PDF-listesi kısayolunun
sessizce gerçek enum değerleri (`created_at`/`ascending`) döndürmesi,
gelecekteki Security/Orchestrator kodunun bunları anlamlı bir karar gibi
yorumlama riski taşıyordu — `DateSource` sınıfına, bu alanların `steps`
boşken hiçbir gerçek kararı temsil etmediğini açıkça belirten bir docstring
eklendi. 52/52 test yeşil.

## pdf-plan-skeleton-uretimi (Saga #269, epic #25)

**LLM plan-skeleton üretimi backend'e eklendi — metadata-only garanti
yapısal olarak sağlandı.** `backend/plan_generation.py`:
`generate_plan_skeleton(pdf_files, client, model=None)` sadece
`filename`+`createdAt` kullanan bir prompt kuruyor (fonksiyon imzası PDF
içeriği/binary parametresi almıyor — "unutma" riski yok, yapısal garanti).
LLM istemcisi bir `Protocol` (`LLMClient`) arkasında soyutlandı; gerçek
`OpenAICompatibleLLMClient` (openai SDK, BYOK için `base_url` override)
sadece `POST /api/plan` endpoint'inde dependency injection ile bağlanıyor.
Model kimliği `PLAN_LLM_MODEL_ID` env değişkeniyle override edilebilir
(pinlenmiş `DEFAULT_MODEL_ID` placeholder — proje henüz sağlayıcı kararı
vermedi). `backend/models.py`'ye backend-taraflı `PlanStep`/`PlanSkeleton`
Pydantic modelleri eklendi (frontend'deki `validatePlanResponse`, Saga
#280, ile aynı kurallar — order tekil+negatif olmayan, operationType sabit
enum, targetFolder boş olmayan, affectedFileCount negatif olmayan).

**Red-team: 3 düşük-önemli bulgu, hepsi değerlendirildi.** (1) Gelecekte
loglama/APM eklenirse ham SDK exception'ının API anahtarını sızdırma
riski — kabul edildi, şu an loglama yok. (2) FastAPI'de dependency
(503) body validasyonundan (422) önce çözülüyor — gerçek bir güvenlik
açığı değil, sadece yanlış yapılandırmada kafa karıştırıcı bir hata kodu.
(3) `get_llm_client` her istekte yeni client kuruyor — önerilen
`lru_cache` DEĞERLENDİRİLDİ AMA UYGULANMADI: testler `PLAN_LLM_API_KEY`
için `monkeypatch.setenv/delenv` kullanıyor, cache test izolasyonunu
bozardı — düşük-önemli bir verimlilik notu için gerçek bir test-izolasyon
riski almak mantıklı değildi. Gerçek LLM entegrasyonu bu ortamda test
EDİLEMEDİ (API anahtarı yok) — sadece Fake/Stub istemcilerle mock'landı,
verify_report.md'ye açıkça not düşüldü. 40/40 test yeşil.

## pdf-siralama-istek-normalizasyonu (Saga #268, epic #25) — Epic #25'e başlangıç

**Backend Entry katmanı normalizasyonu — gerçek bir bug düzeltildi.**
`SessionRequest.not_blank` validator'ı `requestText` için sadece "boş mu"
kontrolü yapıyordu ama trim edilmiş değeri DÖNDÜRMÜYORDU — task'ın
"istek metni trimlenmeli" AC'siyle doğrudan çelişen bir bug'dı. Yeni
`backend/request_normalization.py` modülü (`normalize_request_text`)
eklendi, `/api/session` artık gerçekten trim edilmiş metni döndürüyor.

**Red-team: 3 düşük-önemli bulgu, hepsi hemen düzeltildi.**
(1) `selectedFolder` trim edilmiyordu ("Windows yolları boşluk almaz"
varsayımı pratikte yanlış — API payload'ı temiz olmayabilir) → paylaşılan
bir `_trim_and_reject_blank` helper'a taşınıp her iki alan da artık trim
ediliyor. (2) Unicode boşluk karakterleri (U+00A0, U+3000) ve
tab/newline-only test edilmemişti → eklendi. (3) İki blank-check yolu
zamanla birbirinden sapabilirdi → tek bir yardımcı fonksiyona birleştirildi.
Gerçek dosya sistemi path-validation'ı (whitelist/traversal) bilinçli
olarak kapsam dışı bırakıldı — bu zaten Saga #271/#272'nin işi. 24/24
test yeşil.

Python ortamı notu: proje için ayrı bir venv yok; `pytest`+`fastapi`
`C:\Users\YUSUF ÇİNAR\AppData\Local\Programs\Python\Python311\python.exe`
kurulumunda mevcut, backend testleri o python ile çalıştırılıyor.

## asistan-mesaj-balonu-stili (Saga #261, epic #24) — Epic #24 tamamlandı

**Asistan mesaj balonu stillendirildi, epic #24 (MVP: Ana sohbet arayüzü)
"todo"daki tüm task'lar bitti.** Nötr yüzey (`#F3F4F6` arka plan + `#111827`
metin, ~16:1 kontrast) eklendi, paralel yapı Saga #260 ile aynı desende.
`line-height: 1.5` ortak `chat-message-bubble` sınıfına eklendi (her iki
rol için okunabilirlik iyileştirmesi).

**Bilinçli kapsam daraltması: markdown/başlık yapısı ertelendi, takip
task'ı açıldı.** Task açıklamasındaki "taranabilir başlıklar ve kısa
paragraflar" gereksinimi markdown ayrıştırma gerektirir (yeni bağımlılık,
dar-kapsam ilkesiyle çelişir) — asistan mesajları şu an sadece test
fixture'ı, gerçek backend entegrasyonu yok. Red-team bu kararı onayladı
ama gerçek LLM entegrasyonu gelmeden ÖNCE bunun izlenmesini istedi; Saga
#282 açıldı. 100/100 test yeşil.

## kullanici-mesaj-balonu-stili (Saga #260, epic #24)

**Kullanıcı mesaj balonu stillendirildi.** Mesaj metni artık ayrı bir
`chat-message-bubble` div'ine sarmalanıyor (PlanCard balonun dışında,
konumu değişmedi); kullanıcı rolü için koyu mavi (`#1E3A8A`) arka plan +
beyaz metin, 16px padding, 14px köşe yarıçapı, `max-width: 65ch`. Asistan
mesajları bu task'ta görsel olarak değişmedi (Saga #261'e bırakıldı, dar
kapsam), sadece aynı yapısal sınıfı paylaşıyor.

**Red-team: temiz geçti.** Kontrast oranı hesaplandı (~10.36:1, AAA
seviyesinin bile üzerinde). PlanCard/hint/loading/error göstergelerinde
regresyon yok (özel bir regresyon testiyle doğrulandı). Tek not: inline
`<style>` bloğu büyüyor, ileride bir CSS modülüne/token dosyasına
taşınması önerildi (bu task için gerekli değil). 99/99 test yeşil.

## plan-skeleton-sinir-sema-dogrulamasi (Saga #280, epic #24)

**LLM plan-skeleton yanıtı için boundary şema doğrulaması eklendi (yeni
bağımlılık yok).** Saga #262'nin red-team bulgusuna (PlanCard'ın
backend verisini doğrulamadan render etmesi) cevaben `validatePlanResponse`
saf fonksiyonu eklendi (`ui/src/components/chat/planValidation.ts`). zod
gibi bir kütüphane KULLANILMADI — proje zaten böyle bir bağımlılığa sahip
değil, tek bir fonksiyon için yeni bağımlılık eklemek dar-kapsam ilkesiyle
çelişirdi; el yazımı, 14 test case'le kapsanan bir doğrulayıcı yazıldı.
`order` (negatif olmayan tamsayı + tekil), `operationType` (sabit enum),
`targetFolder` (boş olmayan string), `affectedFileCount` (negatif olmayan
tamsayı) fail-closed doğrulanıyor.

**Red-team: MEDIUM bulgu — fonksiyon henüz hiçbir yere bağlı değil,
takip task'ı açıldı (bloke edilmedi).** Doğrulayıcının kendisi güvenli
(prototype pollution yok, NaN/Infinity doğru reddediliyor, hata mesajları
saldırgan girdisini yansıtmıyor) ama gerçek bir backend/fetch entegrasyon
noktası projede henüz olmadığı için bağlanamıyor — #264-267 ile aynı
"henüz bağlanmamış prop" deseni. Saga #281 açıldı: gerçek backend
entegrasyonu geldiğinde `validatePlanResponse` ChatScreen'e bağlanacak
ve `PlanCard`'ın `operationType` tipi enum'a sıkılaştırılacak. 96/96 test
+ `tsc --noEmit` temiz.

## sohbet-hata-durumu-tekrar-dene (Saga #267, epic #24)

**Hata durumu + "Tekrar dene" eklendi, epic #24 (MVP: Ana sohbet arayüzü)
"todo"daki tüm high-priority task'lar tamamlandı.** `ChatScreen`'e
`planError`/`onRetry` prop'ları eklendi (yine dışarıdan kontrol edilen,
dar kapsam deseni — #264/#265/#266 ile aynı). Hata görünürken `role="alert"`
ile hemen duyuruluyor, "Tekrar dene" sadece `onRetry` çağırıyor, kendiliğinden
kaybolmuyor; textarea/gönder düğmesi (yükleniyor durumundan farklı olarak)
kilitlenmiyor. `isGeneratingPlan` true ise hata göstergesi bastırılıyor
(yükleniyor önceliklidir, çelişkili UI önlenir).

**Red-team: temiz geçti, bulgu yok (sadece 2 düşük-önemli ileriye dönük not).**
PlanCard'ın render yolu bu prop'lardan tamamen bağımsız olduğu için "hata
durumunda asla onay açılmaz" ilkesi tasarım gereği (convention değil,
construction ile) korunuyor. React'ın JSX text escape'i XSS riskini
otomatik kapatıyor. 82/82 test yeşil.

## otomatik-kaydirma-alt-durumu (Saga #266, epic #24)

**Otomatik kaydırma + "En yeni mesaja dön" düğmesi eklendi.** Mesaj listesine
scroll takibi eklendi (24px eşik ile "en altta mı" tespiti); kullanıcı en
alttaysa yeni mesajlarda liste otomatik en alta kayıyor, değilse otomatik
kaydırma yapılmıyor ve bunun yerine bir "En yeni mesaja dön" düğmesi
görünüyor.

**Red-team: MEDIUM bulgu bulundu ve hemen düzeltildi (dormant risk).**
Auto-scroll tetikleyicisi sadece `messages.length`'e bakıyordu — bir mesajın
İÇERİĞİ (ör. plan `securityStatus`'u approved/rejected'e dönerse) aynı
uzunlukta güncellenirse tetiklenmiyordu. Bugün hiçbir kod bu şekilde
mesaj mutasyonu yapmadığı için "uykuda" bir risktir, ama ucuz bir düzeltme
olduğu için hemen kapatıldı: tetikleyici artık mesaj sayısı + son mesajın
id/plan.securityStatus/metin uzunluğunu içeren bir "parmak izi"ne bağlı
(77/77 test yeşil).

## plan-hazirlaniyor-yukleniyor-durumu (Saga #265, epic #24)

**Yükleniyor göstergesi + çift-gönderim kilidi eklendi.** `ChatScreen`'e
dışarıdan kontrol edilen `isGeneratingPlan` prop'u eklendi; true iken
"Plan hazırlanıyor…" + 3 nokta CSS animasyonu gösteriliyor
(`prefers-reduced-motion: reduce` ile animasyon durduruluyor), textarea
ve gönder düğmesi disabled kalıyor.

**Red-team: MEDIUM bulgu bulundu ve hemen düzeltildi.** İlk halde
`PlanCard`'ın "Planı değiştir"/"Onayla" düğmeleri `isGeneratingPlan`'a
bağlı değildi — kullanıcı yeni plan üretilirken eski planı değiştirmeye
çalışabiliyor, "Plan hazırlanıyor…" ile "Planı değiştirmek için yazın"
ipucu aynı anda çelişkili gösteriliyordu. `isGeneratingPlan` prop'u
`PlanCard`'a da geçirildi, her iki düğme de o sırada disabled; regresyon
testi her iki test dosyasına eklendi (73/73 yeşil).

## plani-degistir-duzenleme-baglami (Saga #264, epic #24)

**"Planı değiştir" düğmesi eklendi, onaydan tamamen izole.** `PlanCard`'a
yeni bir düğme eklendi; tıklanınca sadece `onChangePlan` çağrılıyor,
`onApprove` ile hiçbir kod yolu paylaşmıyor. `ChatScreen` textarea'yı
focus'luyor ve kısa bir düzenleme ipucu gösteriyor; kullanıcı yeni mesaj
gönderdiğinde ilgili plan `staleMessageIds`'e eklenip o planın onay
düğmesi kalıcı olarak disabled kalıyor.

**Red-team: iki düşük-önemli, zaten kapsam-dışı bırakılmış bulgu.**
(1) Stale işaretleme sadece istemci-taraflı state — backend entegrasyonu
henüz yok, atdd.md'de zaten açık risk olarak not düşülmüştü. (2)
`editingPlanMessageId` tekil bir skaler — aynı anda iki farklı plan
"değiştir" beklerse ikincisi birincinin üzerine yazar. İkisi de atdd.md
"Risks/Assumptions" bölümünde önceden kabul edilmiş dar-kapsam kararları,
düzeltme gerektirmedi (ready_to_commit: evet).

## vite-vitest-guvenlik-guncellemesi (Saga #278, epic #23)

**Saga #250'de ertelenen güvenlik borcu kapatıldı.** `npm audit fix --force`
ile `vite` (5.4.10→8.2.1) ve `vitest` (2.1.9→4.1.10) yükseltildi (3+2 major
sürüm); `npm audit` artık 0 zafiyet raporluyor (öncesi: 3 moderate, 1 high,
1 critical, esbuild dev-server CORS zinciri). Hiçbir uygulama kodu
değişmedi, tüm mevcut testler (13 pytest + 42 vitest + 26 playwright)
yeşil kaldı.

**Red-team'in bulduğu — ifşa edilmesi gereken, ama düzeltilmesi gerekmeyen
iki boşluk.** (1) `npm ls`, `@vitejs/plugin-react@4.7.0`'ın `vite@8`'i
henüz resmi peer aralığında desteklemediğini gösteriyor (`ELSPROBLEMS`/
`invalid`) — kurulum çalışıyor ve testler yeşil ama npm'in kendi
çözümleyicisi ağacı geçersiz sayıyor. (2) Bu proje bir Tauri masaüstü
uygulaması ama `src-tauri/` henüz yok (Saga #279); mevcut test paketi
(jsdom + tarayıcı-içi Playwright) gerçek native webview runtime'ını hiç
egzersiz etmiyor, dolayısıyla bu yükseltmenin paketlenmiş uygulamada
sorunsuz çalıştığı test EDİLEMEDİ. İkisi de kod değişikliği gerektirmiyor
— `verify_report.md`'ye açıkça ifşa edildi, ikincisi ayrıca #279'un
açıklamasına ("gerçek Tauri build adımında bunu da doğrula") not düşüldü.

## ilk-istek-oturum-baglami (Saga #258, epic #23)

**İlk `saga-oto` (tam otonom, çok-task'lı) koşusu.** Bu task, yeni
oluşturulan `saga-oto` skill'i altında işlendi — ATDD/plan netleştirme
soruları kullanıcıya sorulmadı, en makul (Recommended) seçenekler
otomatik seçildi (bkz. `artifacts/ilk-istek-oturum-baglami/atdd.md`
"Sorular ve Cevaplar" bölümü, 10 soru).

**İlk backend değişikliği — Entry katmanı gerçekten bağlandı.** Frontend'in
`onContinue={() => {}}` no-op'u (Saga #255'ten beri bilinçli olarak
bekletiliyordu) artık gerçek bir `POST /api/session` çağrısı yapıyor.
Backend'de `backend/models.py` (bu projede ilk Pydantic `BaseModel`
kullanımı) + `backend/main.py`'a yeni bir route eklendi; session'lar
in-memory bir `dict`'te tutuluyor (MVP kapsamı, DB yok).

**Bulunan ve düzeltilen bug — atılan sessionId (red-team, MEDIUM).**
Backend'in ürettiği gerçek `sessionId` (UUID) frontend'e ulaşır ulaşmaz
atılıyordu — `onContinue()` parametresiz çağrılıyordu, `App.tsx` sadece
bir boolean (`sessionStarted`) tutuyordu. ATDD'nin kendi AC-5'i
("başarı iddiası doğrulanabilir bir kimliğe dayanmalı") bu yüzden sadece
testte doğrulanıyor, çalışan uygulamada hiç tutulmuyordu. Düzeltme ucuzdu
(2 dosya, `onContinue` imzasına bir parametre eklemek) — commit öncesi
uygulandı, `App.tsx` artık gerçek `sessionId`'yi state'te tutuyor.

**Bilinçli kapsam kararları.** Decision/Planner (LLM) katmanına gerçek bir
çağrı yapılmadı — backend'de henüz böyle bir modül yok, ayrı bir MVP task'ı
(muhtemelen epic #24). Session persistence/expiry yok (in-memory, restart'ta
kaybolur) — tek-kullanıcılı masaüstü MVP'si için kabul edilebilir, red-team
tarafından da onaylandı (düşük öncelikli, engelleyici değil).

## ilk-acilis-klasor-secimi-ekrani (Saga #250, epic #23)

**Zorluk — Codex kotası tükendi task ortasında.** Tooling scaffold'u yazdıktan
sonra Codex (`gpt-5.6-terra`) kullanım limitine ulaştı (Eylül 15'e kadar
kullanılamaz durumda). Kalan düzeltmeler (test cleanup/matcher kaydı, 3 e2e
hatası, red-team bulguları) `efektor` subagent'ına devredildi — pipeline'ın
öngördüğü yedek yol (bkz. proje hafızası "Copilot → Codex Geçişi").

**Bulunan bug — CORS/relative-path fetch (red-team, HIGH).** Frontend
`fetch('/api/health')` gibi göreli yollar kullanıyordu; backend'de CORS
middleware yoktu. Bu, 17 testin tamamı backend'i mock'ladığı için hiç
yakalanmamıştı — paketlenmiş Tauri uygulamasında webview origin'i
(`tauri://localhost`) ile FastAPI sidecar origin'i (`127.0.0.1:8000`) farklı
olacağından, onboarding ekranı gerçek kullanıcıda sonsuza kadar
"Başlatılıyor…" da takılı kalabilirdi. Düzeltme: mutlak URL + açık CORS
origin listesi + gerçek FastAPI `TestClient` entegrasyon testi eklendi
(`backend/tests/test_main_integration.py`) — atdd.md'nin vaat ettiği %30
integration coverage'ı artık gerçekten mock'suz karşılıyor.

**Bilinçli kapsam kararı.** Tauri/Rust iskeleti (`src-tauri/`) ve `unit_test`
tarzı ikinci bir test klasörü bu task'tan bilinçli olarak çıkarıldı — bu task
yalnızca `docs/DESIGN_DECISIONS.md`'nin frontend/backend katmanlarını
gerçekten çalışır kılmayı hedefledi, native masaüstü paketleme ayrı bir task.

## onboarding-istek-placeholder (Saga #254, epic #23)

**Zorluk — Codex kotası task başlamadan önce tamamen doluydu.** #250'de
kota task ortasında tükenmişti (yukarı bakınız); bu task'ta ise ilk
`write_tests()` çağrısı anında `ERROR: You've hit your usage limit... try
again at Sep 15th, 2026` ile başarısız oldu — hiç Codex bütçesi
harcanamadı. Kullanıcıya soruldu (dar kapsam: tek dosya, ~5 satır
implementasyon), kullanıcı onayıyla testler VE implementasyon istisnai
olarak Claude (ana asistan) tarafından yazıldı — normal test-copilot/
code-copilot kuralı ("her satır Codex'ten gelir") bu tek task için bilinçli
olarak esnetildi. Riski azaltmak için: red-team incelemesi `obss-red-team`
subagent'ı ile bağımsız çalıştırıldı ve gerçek `git diff`'i code_diff.md/
test_diff.md iddialarıyla birebir karşılaştırdı (verdict: approve,
ready_to_commit: true).

**Kalıcı öneri (red-team'den, bu task'ta uygulanmadı).** Placeholder metni
("Bu klasördeki PDF'leri tarihe göre sırala") 3 dosyada literal string
olarak tekrarlanıyor (component, unit test, e2e test). Saga #257/#258 veya
i18n bu ekrana dokunursa, ortak bir sabite (`PLACEHOLDER_TEXT` gibi)
çıkarılması önerilir — bu task'ın dar kapsamı için gerekli görülmedi.

## bos-istek-engelleme (Saga #255, epic #23)

**Codex kotası hâlâ dolu (2026-09-15'e kadar).** #254'teki gibi, `saga` skill
Bölüm C override'ı uygulandı: testler VE implementasyon Claude (ana asistan)
tarafından doğrudan yazıldı, `test-copilot`/`code-copilot` (Codex) çağrılmadı.
Bağımsız doğrulama yine `obss-red-team` subagent'ı ile yapıldı — gerçek
`git diff`'i code_diff.md/test_diff.md iddialarıyla karşılaştırdı, 21 unit +
16 e2e testi ve `tsc --noEmit`'i kendi bağlamında yeniden çalıştırıp PASS
buldu (verdict: ready_to_commit: evet).

**CSS özgüllük tuzağı önceden öngörüldü ve çözüldü.** `.onboarding-textarea:focus`
(odak kenarlığı, mavi) ile yeni `.onboarding-textarea.has-error` (hata
kenarlığı, kırmızı) aynı CSS özgüllüğüne (0,2,0) sahipti — hangisinin
kazanacağı sadece stylesheet'teki tanım sırasına bağlı kalırdı (kırılgan).
`.onboarding-textarea.has-error:focus` (0,3,0) eklenerek hata durumunun
odaklanmışken de kırmızı kalması garanti edildi; red-team bunu elle
doğrulayıp doğru bulduğunu teyit etti.

**Codex vision-test de kota nedeniyle kullanılamadı.** Standart `vision-test`
skill'i de Codex'e bağımlı olduğu için, görsel doğrulama Codex vision yerine
gerçek Vite dev server + Playwright ile alınan bir ekran görüntüsünün
(`artifacts/bos-istek-engelleme/empty_request_error_state.png`) Claude
tarafından doğrudan incelenmesiyle yapıldı — bu istisna verify_report.md'de
açıkça not edildi.

**Kalıcı öneri (red-team'den, bu task'ta uygulanmadı — low severity).**
(1) `trim()` zero-width Unicode karakterleri (ör. U+200B) temizlemiyor,
sadece bu tür karakterlerden oluşan bir istek teknik olarak "boş değil"
sayılabilir. (2) `aria-live="polite"` container'ı koşullu mount ediliyor
(her zaman DOM'da olup sadece içeriği değişen bir container yerine) — bazı
ekran okuyucu/tarayıcı kombinasyonlarında duyuru güvenilirliğini
etkileyebilir. İkisi de bu task'ın dar kapsamı (client-side, backend
validasyonu yok) için engelleyici değil, ayrı bir iyileştirme task'ı olarak
değerlendirilebilir.

## gecersiz-klasor-reddi (Saga #256, epic #23)

**Codex kotası hâlâ dolu — aynı override deseni devam ediyor.** Testler ve
implementasyon yine Claude tarafından doğrudan yazıldı, bağımsız doğrulama
`obss-red-team` subagent'ı ile yapıldı.

**Mimari keşif — src-tauri/ ve @tauri-apps/plugin-fs hiç yok.** Bu görev
"klasörün erişilebilir olduğunu doğrula" istiyordu, ama projede gerçek bir
Tauri native kabuğu (`src-tauri/`) veya dosya sistemi plugin'i henüz
scaffold edilmemiş (#250'de bilinçli olarak dışarıda bırakılmıştı).
Kullanıcıya soruldu, kullanıcı "mock'lanabilir Tauri invoke ile ilerle"
seçeneğini onayladı: yeni kod `invoke('plugin:fs|exists', {path})`
çağırıyor ama bu şu an sadece testlerde (`__TAURI_INTERNALS__` / vi.mock)
karşılık buluyor, gerçek bir dosya sistemi kontrolü yok.

**Bulunan risk — HIGH, red-team'den (bu task'ın kendi hatası değil, proje
geneli bir eksiklik).** Eğer uygulama gerçek `plugin-fs` bağlanmadan
paketlenip (`tauri build`) kullanıcıya ulaşırsa, `invoke` reddedilir ve kod
bunu "erişilemez" sayıp HER klasörü reddeder — onboarding kalıcı bir çıkmaz
sokak olur, hiçbir testte görünmez çünkü tüm testler mock'lanmış IPC
katmanını kullanıyor. Bu, 2026-08-16'daki Codex "success:True ama hiçbir
şey yapmadı" olayıyla aynı sınıftan bir risk — sadece test zamanında değil,
paketleme zamanında ortaya çıkıyor. **Aksiyon:** Saga task #279
("RELEASE-BLOCKER: Gerçek @tauri-apps/plugin-fs entegrasyonu", critical,
#256'ya `depends_on`) oluşturuldu — bu task tamamlanmadan `.exe`/installer
paketleme yapılmamalı.

**Bulunan ve düzeltilen bug — TOCTOU boşluğu (red-team, MEDIUM).** İlk
implementasyonda, kullanıcı zaten geçerli bir klasör seçmişken (Devam
aktif) yeni bir klasör seçtiğinde, yeni `exists` kontrolü sonuçlanana kadar
geçen asenkron pencerede eski `isFolderInvalid=false` durumu geçerli
kalıyordu — "Devam" doğrulanmamış yeni bir klasörle tıklanabilir kalıyordu,
tam da bu task'ın önlemeye çalıştığı senaryonun bir zamanlama varyantı.
Düzeltme: `isValidatingFolder` state'i eklenip "Devam"ın `disabled`
koşuluna dahil edildi; bunu doğrulayan test eklenirken mevcut bir testte
(AC-5) senkron `isFolderInvalid(false)` sıfırlamasının yarattığı stale-DOM
eşleşme yarışı da ortaya çıktı ve `waitFor` sıralaması düzeltilerek
giderildi.

**Bilinçli kapsam kararı.** "Yok" ile "izinsiz" hata nedenleri ayrı ele
alınmadı (tek "erişilemez" mesajı), kapsamlı path normalization (case,
symlink) yapılmadı — sadece trailing slash/backslash temizlendi. Red-team
kök sürücü path'lerinde (`C:\` → `C:`) bu minimal normalize'ın bir edge
case'i kaçırdığını (low severity) not etti, düzeltilmedi.

## klavye-ile-form-gezintisi (Saga #257, epic #23)

**Codex kotası hâlâ dolu — aynı override deseni.** Testler ve
implementasyon Claude tarafından doğrudan yazıldı, bağımsız doğrulama
`obss-red-team` subagent'ı ile yapıldı.

**Bulunan ve düzeltilen bug — doğrulama atlatma (red-team, MEDIUM).**
`handleContinueClick`, "Devam" butonunun `disabled` özniteliğindeki
`isFolderInvalid`/`isValidatingFolder` kontrollerini içermiyordu — bu
kontrol sadece JSX'teki `disabled` ifadesinde vardı, fonksiyonun kendi
mantığında değil. Bu görev kapsamında `selected-folder-path` elementine
Enter-ile-submit eklenince (klasör durumundan bağımsız her zaman
odaklanabilir bir eleman), klavye kullanıcısı geçersiz bir klasör
seçiliyken bu elemana Tab'layıp Enter'a basarak `onContinue()`'u
tetikleyebiliyordu — fare kullanıcısının disabled buton sayesinde
atlayamadığı bir kontrolü klavye kullanıcısı atlatabiliyordu. Tam da
erişilebilirlik odaklı bir görevin önlemesi gereken türden bir
mouse/klavye asimetrisi. **Düzeltme:** `canSubmit` adında tek bir
paylaşılan predicate çıkarıldı (`isReady && selectedFolder && !isFolderInvalid
&& !isValidatingFolder`), hem butonun `disabled`'ında hem
`handleContinueClick`'in başında kullanıldı — kural artık tek yerde
tanımlı, bir regresyon testiyle doğrulandı.

**Mimari keşif — native buton Enter davranışına güvenme kararı doğrulandı.**
`atdd.md`/`plan.md` aşamasında, "Klasör Seç" ve "Devam" butonlarına Enter
için ayrı `onKeyDown` eklenip eklenmeyeceği bir Unknown olarak
işaretlenmişti (jsdom'da native Enter→click davranışı güvenilir simüle
edilemiyor). Gerçek Playwright/Chromium'da test edilince bu varsayım
doğrulandı — ek kod gerekmedi, sadece native buton olmayan tek odaklanabilir
eleman olan `selected-folder-path`'e `onKeyDown` eklendi. Red-team ayrıca
gerçek paketlemede Tauri'nin WebView2 (Windows) kullanacağını, bunun
Playwright'ın Chromium'undan farklı bir motor olabileceğini not etti —
bu, henüz gerçek Tauri paketlemesi olmadığı için (Saga #279, release-blocker)
doğrudan test edilemedi, ileride #279 kapatılınca yeniden doğrulanmalı.
