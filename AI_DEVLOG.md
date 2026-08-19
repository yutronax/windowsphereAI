# AI_DEVLOG.md — windows-ai-files

## Dosya arama için asenkron ilerleme göstergesi (Saga #337, epic #27)

**Geriye dönük uyumluluk bilinçli tercih.** Asenkron/polling modeli
`/api/search`'ün response sözleşmesini kökten değiştirirdi (sonuç yerine
scan_id) — bu, #334'teki SearchPanel'i ve mevcut testleri kırardı. ATDD
sorusunda kullanıcıyla netleştirilip mevcut `/api/search` AYNEN bırakıldı,
paralel yeni bir çift eklendi: `POST /api/search/scan` (anında scan_id) +
`GET /api/search/scan/{scan_id}` (polling). Frontend'in bunu kullanması
KAPSAM DIŞI bırakıldı, ayrı bir takip görevi gerekiyor.

**Bağımsız red-team turu gerçek bir hata-yönetimi boşluğu buldu.** İlk
implementasyonda `_run_scan()` (arka plan thread'i) `search_files()`
çağrısını try/except olmadan yapıyordu — bir exception olursa thread
sessizce ölüyor, `ScanState.status` SONSUZA KADAR "running" kalıyordu ve
5 dakikalık TTL temizliği sadece "done" kayıtları hedeflediği için bu
asla temizlenmiyordu (her çökme için kalıcı bellek sızıntısı). İkinci
subagent turu try/except ekleyip hata durumunda da status="done" (+
partial=True) yazacak şekilde düzeltti; bağımsız red-team ikinci turda
doğruladı.

**Mimari karar: threading, asyncio değil.** `backend/main.py`'deki tüm
endpoint'ler `def` (senkron) — FastAPI bunları zaten kendi threadpool'unda
çalıştırıyor. Bu yüzden arka plan taraması için `threading.Thread` +
`threading.Lock` seçildi (asyncio.to_thread değil), mevcut kod tabanının
senkron doğasıyla tutarlı.

360/360 backend test yeşil (4 skip, Windows-only).

## Dosya aramayı recursive'e çevirme (Saga #336, epic #27)

**Kapsam çelişkisinden doğan bölünme.** Saga #315 ("büyük klasör taramalarında
ilerleme göstergesi") kendi açıklamasında "recursive taramalarda" diyordu, ama
Saga #313/#314'teki arama BİLİNÇLİ olarak non-recursive'ti. Kullanıcıyla
netleştirilip #315, #336 (recursive tarama) ve #337 (ilerleme göstergesi,
#336'ya bağımlı) olarak ikiye bölündü.

**ATDD sorusunda kendi hatam: yanlış derinlik sabiti.** Kullanıcıya derinlik
sınırını sorarken "security.py'deki MAX_PATH_DEPTH ile aynı (5)" dedim — gerçek
değer 3'tü. Plan aşamasında koda bakılırken fark edildi, atdd.md/plan.md'deki
TÜM referanslar (5→3, "6. seviye"→"4. seviye") düzeltildi. Ders: emsal bir
sabite atıfta bulunurken kodu OKUMADAN sayı vermemeli.

**Test fixture'ında ikinci bir hata (bu kez subagent'ta), plan aşamasında
öngörülmüştü.** AC-4 testi (`content_contains` recursive çalışıyor mu) fixture'ı
`2024/Q1/Ocak/fatura.txt` (derinlik 4) kullanmıştı — bu AC-2'nin kendi sınırıyla
(derinlik 3) matematiksel olarak çelişiyordu: aynı dosya hem "bulunmalı" hem
"hariç tutulmalı" olamaz. İmplementasyon doğruydu (derinlik 4'ü doğru hariç
tutuyordu), fixture derinliği `2024/Ocak/fatura.txt`e (derinlik 3) küçültülerek
düzeltildi.

**Döngü koruması iki katmanlı test edildi.** plan.md'nin önerisiyle, gerçek
symlink gerektirmeyen bir birim test (ziyaret-edilen-path setinin çekirdek
mantığını izole doğrulayan) + gerçek döngüsel symlink testi (Windows'ta skip)
birlikte yazıldı — böylece AC-3'ün (sonsuz döngü koruması, en kritik AC)
çekirdek mantığı Windows'ta da gerçekten doğrulanmış oldu, sadece "gerçek
symlink" entegrasyonu platform sınırlaması nedeniyle atlandı.

120/120 backend test yeşil (4 skip, Windows-only).

## Dosya Arama frontend UI (Saga #334, epic #27)

**Bağımsız red-team turu gerçek bir sözleşme boşluğu buldu.** İlk implementasyon
turu, `atdd.md`'nin Davranış Sözleşmesi tablosunda tanımlı 3 ayrı hata mesajını
(422 → backend `detail`, 410 → "klasör artık yok", ağ hatası → "sunucuya
ulaşılamadı") tek jenerik "Arama sırasında bir hata oluştu." mesajına
indirgemişti. `SearchPanel.test.tsx` sadece hata testid'inin VARLIĞINI kontrol
ettiği için (metin içeriğini değil) bu sapma testlerde yeşil geçmişti — ikinci
bir subagent turu `response.status`'a göre dallanan mantığı ekledi, testler
`toHaveTextContent` ile metin içeriğini doğrulayacak şekilde güçlendirildi.
Bağımsız red-team ikinci turda düzeltmeyi doğruladı (`ready_to_commit: true`).

**`sessionId` App→ChatScreen'e hiç geçirilmiyordu.** Plan aşamasında koda
bakılarak bulunan bir boşluk — ATDD'nin "Unknowns" bölümünde işaretlenmişti,
`App.tsx`/`ChatScreen.tsx` ikisi de güncellendi.

**Bilinen sınırlama:** Gerçek Tauri+backend ortamında canlı görsel doğrulama
yapılamadı (dev server tarayıcı önizlemesinde `@tauri-apps/plugin-dialog`
native klasör seçici çalışmıyor, akış "Backend ulaşılamadı"da tıkanıyor) —
151 geçen RTL testi yeterli görüldü ama kullanıcı gerçek uygulamada bir kez
manuel kontrol etmeli.

`npx vitest run` (proje geneli): 151 passed, 0 failed.

## Naive tarih string'i 500 hatası düzeltmesi (Saga #335, epic #27)

Saga #313'ün `verify_report.md`'sinde bilinen sınırlama olarak not düşülmüştü:
`modifiedAfter`/`modifiedBefore` offset'siz (timezone-naive) bir ISO string
ile gönderilirse, `file_search.py`'nin tz-aware (UTC) `st_mtime`
karşılaştırmasıyla çakışıp `TypeError`→500'e düşüyordu. `backend/main.py`'de
parse sonrası `tzinfo is None` ise UTC atanacak şekilde 4 satırlık minimal
düzeltme yapıldı — `file_search.py`'ye dokunulmadı. 113/113 test yeşil (3 yeni).

## Dosya içeriğinde arama: timeout + encoding toleransı (Saga #314, epic #27)

**Encoding fallback sırası — plan aşamasında bulunan risk.** `search_files()`
için ilk akla gelen sıra utf-8→latin-1→cp1254 olurdu, ama latin-1 (ISO-8859-1)
256 kod noktasının hepsini tanımladığı için PRATİKTE HİÇ `UnicodeDecodeError`
fırlatmaz — yanlış sırada denenirse cp1254 gerektiren Türkçe içerik sessizce
yanlış decode edilip aranan metin hiç bulunamazdı. Plan adımında fark edilip
sıra `utf-8 → cp1254 → latin-1` (latin-1 EN SON) olarak düzeltildi.

**Threat-model'in eklediği 2 güvenlik kriteri.** `atdd` sonrası çalıştırılan
`threat-model` adımı, içerik aramasının dosya İÇERİĞİNİ okuduğunu (sadece
dosya adı değil) fark edip iki somut AC ekledi: (1) `allowed_root` dışına
işaret eden symlink'lerin içeriği taranmıyor (veri sızıntısı önleme), (2)
`contentContains` 500 karakterle sınırlı (aşırı büyük payload ile DoS
önleme). İkisi de implementasyona girdi; Windows'ta ikisinin de testi
(symlink oluşturma ve chmod, POSIX-only semantik gerektirdiği için) skip
edildi — red-team bunu "kodu okundu ama bu döngüde gerçekten çalıştırılmadı"
diye medium-severity bulgu olarak işaretledi, Linux/CI'da tekrar doğrulanması
gerekiyor.

**Test-fixture hataları implementasyon hatasıyla karıştırılmadı.** Green
adımından sonra 3 test kırmızı kaldı; ayrı bir subagent turu bunların
implementasyon değil TEST verisi hatası olduğunu doğruladı: (1) latin-1'de
temsil edilemeyen bir Türkçe karakter (`ş`) içeren fixture, (2)
`os.chmod(0o000)`'ın Windows NTFS'te POSIX gibi davranmaması, (3) FastAPI
TestClient'ın threadpool'unun `time.monotonic()` monkeypatch sırasını
bozması. Üçü de implementasyon dosyalarına dokunulmadan, sadece test
tarafında düzeltildi — 110 passed, 2 skipped (gerekçeli), 0 failed.

`test_file_search.py` + `test_main_integration.py`: 110 passed, 2 skipped
(Windows-only sınırlama, gerekçeli), 0 failed.

## Dosya Arama MVP (Saga #313, epic #27) — epic'in ilk kapsam kararı + ilk backend dilimi

**Kapsam kararı (task'ın kendi ilk sorusu).** Arama, `/api/plan`
akışından TAMAMEN AYRI, yeni bir salt-okunur `POST /api/search`
endpoint'i olarak modellendi — `plan_generation`in LIST operationType'ına
ENTEGRE EDİLMEDİ. Gerekçe: plan/apply akışı "onayla → gerçekten uygula"
(mutasyon) akışı, arama ise doğrudan sonuç isteyen salt-okunur bir
sorgu — plan/onay adımından geçirmek gereksiz karmaşıklık olurdu.

**Yeni `backend/file_search.py`** — non-recursive, `discover_pdf_files`
ile aynı stil (gizli dosya atlama), `nameContains`/`extension`/
`modifiedAfter`/`modifiedBefore` filtreleri AND mantığıyla birleşiyor.
Sonuçta MUTLAK PATH SIZDIRILMIYOR (Saga #283 konvansiyonu) — sadece
filename/extension/modifiedAt/sizeBytes.

**Bulunup düzeltilen sorun (3 Haiku subagent turundan ikisinde
gerçekleşti).** İlk implementasyon turu, ATDD'de HİÇ olmayan bir "fuzzy
substring" (1 karakter farkına izin veren) eşleştirme icat etmişti —
"fatura" araması "vatura" gibi ilgisiz dosyalarla da eşleşebilirdi. Ana
oturumun diff incelemesi bunu yakaladı, dördüncü bir Haiku çağrısıyla
düz substring'e döndürüldü. Bu, Saga #312'deki "bilinmeyen yedek
klasörü" hackiyle AYNI örüntü — Haiku'nun bazen testini geçirmek için
ATDD'nin dışına çıkan kısayollar icat edebildiğini gösteriyor, ana
oturumun her turda diff'i GERÇEKTEN okuması (subagent'ın "yaptım"
iddiasına güvenmemesi) bu yüzden vazgeçilmez.

**Kapsam dışı bırakılan (zaman bütçesi, bilinçli karar).** Frontend
"basit sonuç listesi UI'ı" (ATDD'nin kendi P1 kriteri) bu koşuda
YAPILMADI, backend MVP'nin kendisi önce tamamlandı — ayrı bir takip
task'ı açıldı. Ayrıca `modifiedAfter`/`modifiedBefore` timezone-naive
bir ISO string ile gönderilirse 500'e düşebileceği (testler sadece
tz-aware string kapsadı) bilinen bir sınırlama olarak not düşüldü.

320/320 backend test yeşil (52 yeni: 38 arama mantığı + 14 endpoint).

## DELETE yedek toplam boyut sınırı (Saga #312, epic #26) — kod yazımı ilk kez Haiku subagent'larıyla

**Süreç notu.** 2026-08-18'de kullanıcı kalıcı bir kural netleştirdi: kod/
test yazımı HER ZAMAN Haiku modelli ayrı bir subagent'a devredilir, ana
oturum (Sonnet) kendisi asla `Edit`/`Write` ile implementasyon yazmaz —
sadece keşif+ATDD/plan+doğrulama+red-team-benzeri inceleme yapar. Bu, o
kuralla yapılan ilk task.

**Bulduğu değer: ana oturumun bağımsız incelemesi gerçek bir sorunu
yakaladı.** İlk Haiku implementasyon turu, ATDD'de HİÇ olmayan bir
"bilinmeyen yedek klasörü" özel-durumu icat etmişti — threshold zaten
altına inildiğinde bile TÜM bilinen adayları körü körüne siliyordu
(gereğinden fazla veri kaybı riski, boyut sınırının amacını boşa
çıkarıyordu). Kök neden: yazdığı testin kendi varsayımı ("phantom"
klasörlü senaryoda İKİ transaction'ın da silinmesi gerektiği) aslında
basit/doğru mantıkla (her purge sonrası gerçek toplam boyutu yeniden
hesapla, eşik altına inince dur) çelişiyordu — implementasyon bu
çelişkiyi "her zaman tümünü sil" gibi tehlikeli bir kısayolla çözmüştü.
Üçüncü bir Haiku çağrısıyla hem kod hem test doğru mantığa göre
düzeltildi: fonksiyon artık HER purge sonrası gerçek boyutu yeniden
ölçüp eşik altına inince duruyor.

**Özellik:** `purge_oversized_delete_backups` — mevcut süre-bazlı
`purge_expired_delete_backups`e (Saga #300/#302) ek olarak, DELETE
yedek klasörünün TOPLAM boyutu bir eşiği (varsayılan 2000 MB) aşarsa
en eski `committed` saf-DELETE transaction'lardan başlayarak, eşik
altına inene kadar purge eder. CAS+rmtree güvenlik deseni ortak bir
yardımcıya (`_purge_one_transaction_backup`) çıkarılıp iki fonksiyon
arasında paylaşıldı, kod tekrarı yok. 268/268 test yeşil (7 yeni).

## Bulk-onay eşiği (Saga #311, epic #26) — süreç değişikliği: yalın mimariyle ilk task

**Süreç notu (asıl önemli kısım).** 2026-08-18'de kullanıcıyla birlikte
`saga-oto`'nun mimarisi yeniden şekillendirildi — önceki "her task için
ayrı, kendi içinde yine subagent'lar çağıran otonom bir pipeline agent'ı"
deseni kaldırıldı (bkz. Saga #309/#319/#320/#324'te 100-170K token/task).
Bu task, yeni yalın akışla (ana oturum kendisi keşfeder+ATDD/plan yazar+
küçük görevlerde doğrudan kodu/testi yazar+doğrular+commit eder, sadece
gerçekten büyük/riskli görevlerde ayrı subagent/red-team) yapılan İLK
task — hiçbir Agent-tool subagent'ı ÇAĞRILMADI, tüm iş bu oturumun
kendi bağlamında yapıldı.

**Özellik:** `PlanCard`'da toplam `affectedFileCount` 20'yi aşan planlar
artık tek tıkla değil, `ResultCard`'ın revert onayındaki AYNI iki-aşamalı
desenle (confirm/cancel çift buton) onaylanıyor — "yanlış klasör, 1000
dosya" riskine karşı ek bir görsel/etkileşimsel fren. Backend'e hiç
dokunulmadı, `affectedFileCount` zaten mevcut şemada. 141/141 frontend
test yeşil (3 yeni).

## Kilitli-dosya/antivirüs geçici I/O toleransı (Saga #310, epic #26) — ilk aider-bridge denemesi

**Token maliyetini düşürmek için yeni bir araç denendi: Aider + Ollama
(yerel, ücretsiz `qwen2.5-coder:7b`).** `C:\Users\...\.claude\skills\aider-bridge\`
altında kurulan köprü, Codex/Copilot kotası dolduğunda Agent-tool
subagent delegasyonunun yerine geçmesi için tasarlandı. Bu görev ilk
gerçek denemesiydi.

**Sonuç: kısmi başarı, kritik bir tuzak canlı bulundu ve düzeltildi.**
Test yazımı (küçük, yeni içerik) sorunsuz çalıştı — ama iki tur
"düzeltme" çağrısı sırasında Aider'ın Ollama modelleri için varsayılan
**"whole edit format"**i, `backend/tests/test_orchestrator.py`'nin
(1800+ satır, MOVE/COPY/DELETE/MERGE/SPLIT/REDACT/EXCEL_SORT testleri
dahil) neredeyse TAMAMINI sessizce sildi (58 satıra indirdi,
`returncode: 0`, hiçbir hata/uyarı yok). Commit edilmemiş olduğu için
`git checkout --` ile anında geri alındı, kayıp yaşanmadı — ama bu,
"Aider'in sonucunu MUTLAKA doğrula" disiplininin (`aider_bridge.py`
docstring'i, `SKILL.md`) neden var olduğunu somut şekilde kanıtladı.

**İkinci bulgu: `qwen2.5-coder:7b`'nin context penceresi (32K), 700+
satırlık `backend/orchestrator.py`'ye küçük bir fonksiyon eklemek için
bile yetersiz kaldı** ("possibly exhausted context window", jenerasyon
yarıda kesildi — ama `diff` edit formatı sayesinde geçersiz/yarım bir
blok dosyaya hiç UYGULANMADI, `orchestrator.py` sağlam kaldı). Bu
implementasyon (tek fonksiyon + 3 çağrı noktası) sonunda Claude
tarafından doğrudan yazıldı.

**Sonuç olarak `SKILL.md`'ye kalıcı bir kural eklendi:** Aider, SADECE
yeni dosyalar veya küçük (<150 satır) mevcut dosyalar için kullanılmalı;
büyük/mevcut dosyalara küçük ekleme gerektiğinde Claude'un kendisi
`Edit` kullanmalı — "kod yazımı modele ait" kuralının bilinçli bir
istisnası, çünkü bu boyuttaki dosyalarda araç güvenilir değil.

**Asıl özellik:** `_retry_on_transient_io_error` — `_forward_move`/
`_forward_copy`/`_forward_delete` içindeki `shutil`/`os` çağrılarını
sarmalayan, WinError 32 (kilitli dosya)/5 (antivirüs geçici bloğu)
için üstel backoff'lu (en fazla 3 deneme) retry uygulayan bir yardımcı.
Diğer tüm `OSError` türleri hiç retry edilmeden hemen fırlatılır —
kalıcı hata davranışı değişmedi. 261/261 test yeşil (5 yeni).

## Excel sıralama + formül güvenlik ağı (Saga #324, epic #29) — projenin ilk Excel desteği

**Finansal veri bozulması riski kapatıldı.** Referans projedeki
(`referans/windows-ai-files-eski/core/agents/excel_agent.py` — kod
taşınmadı) bilinen ders: openpyxl formülü düz metin olarak taşır; satır
fiziksel olarak yer değiştirdiğinde formül metnindeki hücre
referansları (`=C2+C3`) OTOMATİK GÜNCELLENMEZ — sıralama sonrası formül
artık BAŞKA bir satırın verisini sessizce (hata vermeden) hesaplar.
Muhasebeci kullanıcılar için bu doğrudan bir finansal hata riski.

**Yeni `backend/excel_sort.py`, projenin ilk Excel operasyonu.**
`OperationType.EXCEL_SORT` MERGE/SPLIT/REDACT ile aynı desende
(`PlanStep` alanları + validator'lar, `_SUPPORTED_OPERATION_TYPES`,
geçici-dosya-yaz + atomik `Path.replace`) eklendi. Path doğrulaması
merkezi kaldı (Saga #307/#319 konvansiyonu, `DESIGN_DECISIONS.md` §6)
— `excel_sort.py` hiçbir whitelist mantığı içermiyor.

**Sütun çözümleme: önce başlık metni, sonra harf.** Kullanıcı doğal
olarak sütun başlığıyla konuşur ("Tutar sütununa göre sırala") — bu
yüzden `resolve_sort_column` önce header satırında (case-insensitive)
tam metin eşleşmesi dener, bulamazsa bare Excel sütun harfi ("C", "AA")
olarak yorumlar.

**Formül tespiti gerçek (`cell.data_type == "f"`), string-heuristik
değil.** Sıralanacak veri aralığında herhangi bir hücre formülse
işlem SIFIR satır değiştirmeden reddedilir, çıktı dosyası hiç
yazılmaz — sessiz kısmi/yanlış sonuç yerine açık hata.

Token bütçesi kısıtı nedeniyle bu görevde ayrı bir bağımsız red-team
turu ATLANDI (ana akış tarafından kod doğrudan gözden geçirildi,
testler kendi çalıştırıldı) — düşük-risk, göreceli izole bir modül
olduğu için kabul edilebilir bir istisna. 256/256 test yeşil (openpyxl
requirements.txt'e eklendi).

## PDF gerçek redaksiyon / KVKK (Saga #320, epic #29) — güvenlik-kritik, rasterize+karart, sahte siyah kutu DEĞİL

**Güvenlik motivasyonu.** Referans projedeki (`referans/windows-ai-files-eski/core/agents/pdf_agent.py`)
`_redact`, PDF üzerine sadece siyah bir dikdörtgen ÇİZİYORDU — metin
katmanı hâlâ metin katmanı olarak kalıyordu, yani kopyala-yapıştır veya
`extract_text()` ile hassas veri (TC kimlik no, hesap no, vergi no —
KVKK kapsamı) hâlâ çıkarılabiliyordu. Yarım bir redaksiyon, hiç
redaksiyon yapmamaktan DAHA KÖTÜ — kullanıcı (mali müşavir/avukat) dosyayı
güvenli sanıp paylaşır. Bu görev, o koddan HİÇBİR SATIR kopyalamadan,
sıfırdan yeni bir `OperationType.REDACT` tasarladı: hedef sayfa rasterize
edilir (pdf2image), belirtilen bölge(ler) üzerine opak kutu çizilir
(PIL), ve o TEK sayfa çıktı PDF'inde orijinal vektör/metin sayfasının
YERİNE (yanına değil) konur — diğer sayfalar dokunulmadan vektör/aranabilir
kalır.

**Path validasyonu merkezi kaldı.** `backend/pdf_redact.py` hiçbir
allowed_root/whitelist mantığı içermiyor — MERGE/SPLIT/OCR'daki AYNI
ders (Saga #306/#307) uygulanarak, `redactedFileName` doğrulaması
doğrudan `backend/security.py`'nin `validate_plan_paths`/yeni
`validate_redact_destinations`'ına eklendi, `orchestrator.py`'nin
`apply_plan`'ı kaynak+hedef için `is_path_allowed` üzerinden geçiyor.

**Bağımsız red-team turu 1 HIGH + 1 MEDIUM bulgu buldu, ikisi de aynı
görevde düzeltildi (regresyon testleriyle):** (1) `RedactionRegion`'ın
dokümante ettiği koordinat uzayı (PDF nokta, sol-alt orijin) ile
`redact_pdf_page`'in GERÇEKTE çizdiği uzay (ham piksel, sol-üst orijin,
sabit DPI) TUTARSIZDI — dokümante edilen sözleşmeyi izleyen bir
kullanıcı/LLM kutuyu YANLIŞ yere çizerdi, metin katmanı yok olsa da
hassas veri GÖRSEL OLARAK açıkta kalabilirdi (kritik: "metin gitti" ile
"güvenli" AYNI ŞEY DEĞİL). Düzeltme: gerçek `mediabox` (nokta) boyutu
render edilen görüntünün piksel boyutuna oranlanıp her bölge doğru
piksel konumuna (Y-flip dahil) dönüştürülüyor. (2) Sayfa dışı bölge
kontrolü yoktu (AC7) — artık gerçek sayfa boyutunu aşan bölge çizim
başlamadan `ValueError` ile reddediliyor. Ayrıntı: `artifacts/pdf-redact/verify_report.md`.

**Kapsam dışı bırakılan (bilinçli karar).** Otomatik PII tespiti (TC
kimlik no'yu kendiliğinden bulup önerme) bu görevde YAPILMADI —
kullanıcı/LLM bölgeyi açıkça belirtmeli. Ayrı bir gelecek görev olarak
Saga'ya not edildi (depends_on: [320]).

## Format Agent parametre güvenlik ağı (Saga #319, epic #29) — kod boşluğu yok, konvansiyon + wiring testleri eklendi

**Keşif sonucu: bug sınıfı bu projede henüz yok.** Referans projedeki
(`referans/windows-ai-files-eski`) tekrarlayan hata — şemanın bir alan
adı bildirmesi, orchestrator'ın FARKLI bir isim okuyup alanı sessizce
yoksaması — bu projede `PlanStep.newFileNames` (RENAME) ve
`PlanStep.mergedFileName` (MERGE) için ARANDI ve BULUNAMADI: her ikisi
de `orchestrator.apply_plan`'da gerçekten okunuyor
(`destination_path = allowed_root / step.mergedFileName`,
`dict(zip(step.fileNames, step.newFileNames))`). Bu yüzden kod
değişikliği yapılmadı — görev, AST/statik-analiz gibi orantısız bir
otomatik kontrol kurmak yerine, gelecekteki format-agent görevleri
(#320-#329, Word/Excel/Image/Zip) için dökümante edilmiş bir test
konvansiyonu (`docs/DESIGN_DECISIONS.md` §6) + iki somut "alanı
değiştir, çıktının değiştiğini gör" testi teslim etti.

**Red-team bulgusu → takip task'ı.** Bağımsız inceleme, testlerin
gerçekten wiring'i kanıtladığını onayladı (`ready_to_commit: true`) ama
gelecekteki 5+ benzer testin kopyala-yapıştır'a dönüşeceğini işaret
etti — bu görevi bloklamadı, Saga #332 (depends_on: [319], low öncelik)
olarak ayrı bir takip task'ı açıldı.

## apply-plan endpoint (Saga #309, epic #25) — ürünün ilk gerçek uçtan uca dosya işlemi

**Kilometre taşı: uygulama artık gerçekten bir şey yapıyor.** `POST
/api/plan` planı önerebiliyordu, `PlanCard` onaya sunabiliyordu, ama
`onApprovePlan` kasıtlı bir no-op'tu (Saga #287) — hiçbir dosya asla
gerçekten taşınmıyordu. Bu görev `POST /api/transactions/apply`
endpoint'ini ekleyip mevcut, olgun `orchestrator.apply_plan`'a (atomik
transaction + rollback + backup_path, zaten 200+ testle kapsanıyordu)
bağladı ve frontend'i (`App.tsx`'in `handleApprovePlan`'ı) gerçekten bu
endpoint'i çağırıp `ResultCard`'ı render edecek şekilde bağladı.
`orchestrator.py`/`security.py`/`db_models.py`'ye HİÇ dokunulmadı —
görev kasıtlı olarak sadece HTTP + frontend kablolama katmanıydı.

**Frontend'in eksik veri sorunu.** `planValidation.ts`'in ürettiği
budanmış `Plan` tipi (PlanCard için) `fileNames`i (backend'in
`apply_plan`i için ZORUNLU) taşımıyordu. Yeni bir sunucu-taraflı
plan-saklama katmanı eklemek yerine (kapsam dışı mimari genişleme),
`/api/plan`in HAM yanıtı `ChatMessage.rawPlan` alanında (sadece
App.tsx içinde kullanılır, PlanCard render'ını etkilemez) ayrıca
saklandı ve onay anında bu geri gönderildi.

**Sıfır-işlem-ama-başarı false-positive'i önceden kapatıldı.**
`apply_plan` boş/`LIST`-sadece bir planı sorunsuzca "committed" (0
`FileOperation`) sayıyordu — eski projenin bilinen hata sınıfı. Endpoint,
`apply_plan`ı çağırmadan ÖNCE plan en az bir gerçek (LIST-dışı) adım
içerip içermediğini kontrol ediyor, yoksa 422 ile reddediyor,
`orchestrator.py`'ye dokunulmuyor.

**Red-team bulgusu — race condition, düzeltildi.** İlk implementasyon,
"whitelist-benzeri geçersiz plan" (transaction hiç oluşmadı, 403 olmalı)
ile "gerçek rollback" (transaction oluştu ve geri alındı, 200 olmalı)
ayrımını `Transaction` tablosunun global satır sayısını ÖNCESİ/SONRASI
karşılaştırarak yapıyordu — eşzamanlı bir istek araya girip transaction
oluşturursa, bu isteğin YANLIŞ transaction'ın id/status'unu (başka bir
isteğe ait) döndürmesine yol açabilirdi (TOCTOU). Düzeltme:
`orchestrator._distribute_files_to_steps`'i (private ama import edilebilir)
`apply_plan`dan ÖNCE doğrudan çağırıp deterministik bir ön-kontrol
yapıldı — sayaç karşılaştırması tamamen kaldırıldı, `orchestrator.py`'ye
yine dokunulmadı.

Test (red) ve implementasyon (green) adımları ayrı genel-amaçlı
subagent'lara delegasyon disipliniyle yazdırıldı; bağımsız `obss-red-team`
incelemesi gerçek git diff'e karşı çalıştırıldı, bulunan race condition
aynı disiplinle (ayrı bir subagent'a) düzeltildi ve yeniden doğrulandı.

Backend: 209/209 yeşil (`backend/tests/test_main_integration.py`, 5 yeni
test). Frontend: 138/138 yeşil (`ui/src/App.test.tsx`, 3 yeni test + 1
artık geçersiz no-op-varsayımı test güncellendi).

**Kapsam dışı bırakılan riskler (ayrı task adayları):** 20+ dosyalık
toplu işlemler için ek onay eşiği yok; kilitli dosya/AV geçici engeli
(WinError 32/5) için ayrı bir bounded-retry mekanizması eklenmedi
(`apply_plan`in mevcut atomik rollback'i "sessiz tek deneme
başarısızlığı" sınıfını zaten önlüyor, ama TÜM planın geri alınması UX
açısından gelecekte iyileştirilebilir).

## purge-lock (Saga #302, epic #28)

**Saga #300'ün bıraktığı orta önemli bulgu, scheduler'a bağlanmadan ÖNCE
kapatıldı:** `purge_expired_delete_backups` ve `revert_transaction` aynı
`Transaction` satırını iki bağımsız DB session'ından yarışarak
güncelleyebiliyordu (lost-update) — henüz hiçbir cron/scheduler'a
bağlanmadığı için gerçek risk yoktu, ama bu iş o bağlanmadan önce bitirildi.

**Kilitleme deseni:** proje SQLite kullanıyor (`backend/db.py`), SQLAlchemy
`with_for_update()` SQLite'ta desteklenmiyor. Bunun yerine yeni bir
`_claim_transaction_status` yardımcı fonksiyonu eklendi — atomik koşullu
`UPDATE ... WHERE id=? AND status=from_status` (compare-and-swap),
`rowcount` kontrolüyle "kazanan"ı belirliyor. Yeni kolon/migration YOK,
mevcut `status` sütunu hem veri hem kilit anahtarı olarak kullanılıyor.

- `revert_transaction`: dosya rollback'i bittikten sonra, DB'ye son durumu
  yazmadan önce bu atomik claim'i dener; kaybederse hiçbir şeyin üzerine
  yazmadan `TransactionRevertError` fırlatır.
- `purge_expired_delete_backups`: `shutil.rmtree`den ÖNCE üç durumlu bir
  claim zinciri kullanır (`"committed"` → `"purging"` → `"backup_purged"`,
  fiziksel silme başarısız olursa telafi edici `"purging"` → `"committed"`)
  — böylece DB yazma kilidi `rmtree` süresince AÇIK TUTULMUYOR (ilk
  taslakta öyleydi, bağımsız red-team incelemesi SQLite'ın tüm `app.db`
  dosyası üzerindeki kilidin uzun bir dosya sistemi çağrısı boyunca
  tutulacağını, uygulama genelinde başka yazmaları bloklayacağını tespit
  etti — düzeltildi).

**Red-team bulgusu (aynı oturumda düzeltildi):** `revert_transaction`in
claim'i yarışı kaybettiğinde, `POST /api/transactions/{id}/revert`
endpoint'i bellekteki BAYAT `transaction.status` değerini (claim öncesi,
ör. hâlâ `"committed"`) döndürüyordu — DB'deki GERÇEK değerle (kazananın
yazdığı, ör. `"backup_purged"`) uyumsuzdu. `main.py`ye
`db.refresh(transaction)` eklendi, regresyon testi eklendi.

**Test:** `backend/tests/test_orchestrator.py`e iki bağımsız `Session`
nesnesiyle (aynı sqlite dosyasına bağlı) her iki yarış yönünü de simüle eden
tek bir regresyon testi eklendi; `backend/tests/test_main_integration.py`e
endpoint seviyesinde bayat-durum bulgusunu kanıtlayan ayrı bir test eklendi.

## transaction-allowed-root (Saga #301, epic #28)

**Saga #295'in bıraktığı mimari bulgu kapatıldı:** `POST
/api/transactions/{id}/revert` artık `allowed_root`'u istemcinin request
body'sinden ALMIYOR. `Transaction` modeline nullable bir `allowed_root`
kolonu eklendi, `apply_plan`/`create_transaction` sırasında server
tarafında (gerçek çözümlenmiş kökten) dolduruluyor; `revert_transaction`
artık `allowed_root` parametresi almıyor, kendi `transaction.allowed_root`
alanını kullanıyor. `RevertTransactionRequest`'ten `allowedRoot` alanı
tamamen kaldırıldı (artık boş bir Pydantic modeli) — spoofed/geniş bir
`allowedRoot` (ör. `"C:\\"`) gönderilse bile Pydantic'in varsayılan
`extra="ignore"` davranışıyla yok sayılıyor.

**Migration yok, mevcut shim kullanıldı:** proje Alembic KULLANMIYOR —
`backend/db.py::_add_missing_columns` (Saga #284) yeni nullable kolonu
otomatik `ALTER TABLE ADD COLUMN` ile ekliyor, ek migration kodu
yazılmadı.

**Red-team bulgusu (aynı oturumda düzeltildi):** `allowed_root IS NULL`
olan (migration öncesi) `committed` bir transaction için revert isteği
ilk implementasyonda genel `except TransactionRevertError: pass` bloğuna
düşüp durumu DEĞİŞTİRMEDEN 200 dönüyordu — ATDD'nin belgelediği net 409
yerine belirsiz bir "hiçbir şey olmadı ama 200" yanıtı. `main.py`'ye
`transaction.allowed_root is None` için AYRI, önceden bir 409 kontrolü
eklendi (mevcut 404/409 precondition desenine uygun), regresyon testi
eklendi.

**Frontend:** `ResultCard.tsx`'in revert fetch'i artık boş body (`{}`)
gönderiyor; `canShowRevert`/erken-çıkış kontrolü sadece `transactionId`'ye
bakacak şekilde sadeleşti (`selectedFolder` artık zorunlu değil — task
açıklamasındaki dar kapsam kararıyla `selectedFolder` prop'unun kendisi
component'ten kaldırılmadı, sadece zorunlu-kontrolden çıkarıldı).

## pdf-ocr-path-validation (Saga #307, epic #29)

**Saga #306'nın bıraktığı gerçek bir güvenlik açığı kapatıldı:**
`backend/pdf_ocr.py::ocr_pdf_file` hiçbir endpoint'e bağlı değildi ve
ham bir `Path` alıyordu — MERGE/SPLIT/DELETE'in tersine `allowed_root`/
`is_path_allowed` doğrulamasından hiç geçmiyordu. `OperationType.OCR`
eklenip `apply_plan`'a MERGE/SPLIT ile AYNI desende (dosya sayısı tam
1, `is_path_allowed` kontrolü ÖNCE, `ocr_pdf_file` çağrısı SONRA)
kablolandı.

**`pdf_ocr.py` bilinçli olarak DEĞİŞTİRİLMEDİ** — red-team'in Saga
#293'teki emsale dayanan açık gerekliliği: güvenlik kontrol noktası
`orchestrator.py`'de MERKEZİ kalmalı, `pdf_ocr.py`'de tekrarlanmamalı.

**OCR, LIST gibi "inert" tasarlandı** — hiçbir `FileOperation` kaydı
oluşturmaz, rollback listesine girmez (OCR sonucu bu task kapsamında
hiçbir yere yazılmıyor/dönülmüyor — henüz hiçbir endpoint OCR'ı
tetiklemiyor, bu ayrı bir gelecek task'ın kapsamı).

Test+implementasyon iki ayrı genel kodlama subagent'ına red→green
disipliniyle delegasyon edildi, ana akış sonucu bağımsız `pytest`
çalıştırmasıyla doğruladı (196/196 yeşil). Bağımsız red-team incelemesi
`ready_to_commit: yes` verdi, tek düşük-önem bulgu (negatif testin genel
`Exception` yerine spesifik `PathWhitelistError` beklemesi gerektiği)
hemen düzeltildi ve testler yeniden yeşile alındı.

## pdf-bolme-split-operasyonu (Saga #305, epic #29)

**Sayfa aralığı DEĞİL, sayfa başına bölme seçildi — task'ın kendi
sunduğu iki seçenekten en dar kapsamlısı.** Sayfa aralığı, LLM'in plan
üretim ANINDA (henüz gerçek sayfa sayısını bilmediği bir aşamada,
Saga #292'nin çözdüğü AYNI kısıt) geçerli/çakışmasız aralıklar
üretmesini gerektirirdi. Sayfa-başına bölme bu sorunu TAMAMEN ORTADAN
KALDIRIYOR: hiçbir yeni şema alanı gerekmiyor, çıktı adları kaynak
dosya adından TÜRETİLİYOR (`kaynak.pdf` → `kaynak_1.pdf`, ...).

**MERGE'in (Saga #304) TAM SİMETRİK TERSİ olarak inşa edildi** — MERGE
"N kaynak → 1 hedef" idi, SPLIT "1 kaynak → N hedef". Rollback için
SPLIT'e ÖZEL yeni bir fonksiyon GEREKMEDİ — her sayfa BAĞIMSIZ bir
`FileOperation` kaydı olduğu için COPY'nin `_rollback_copy`si (sadece
hedefi sil, kaynağa dokunma) HER kayıt için ayrı ayrı çalışıyor.

**Çıktı adı çakışması ÖNCEDEN değil, ÇALIŞMA ZAMANINDA tespit
ediliyor** — gerçek sayfa sayısı sadece dosya AÇILDIĞINDA bilindiği
için `validate_plan_paths` (plan onaylanmadan ÖNCE çalışır) bunu
öngöremez. Bilinçli bir sapma: RENAME/MERGE'in ön-doğrulama desenine
karşı, her sayfa yazılmadan HEMEN ÖNCE `output_path.exists()` kontrolü
+ varsa tüm transaction'ı reddetme.

**Saga #304'ün red-team dersi doğrudan uygulandı:** her çıktı sayfası
MERGE'in düzeltilmiş `_forward_merge`iyle AYNI geçici-dosya-yaz +
atomik-taşı desenini kullanıyor — yarıda kesilen bir yazma hiçbir
zaman gerçek hedefte yarım dosya bırakmıyor.

Codex/Copilot kotası dolu olduğu için test+implementasyon yine genel
bir kodlama subagent'ına delegasyon disipliniyle yazdırıldı (red→green
sırası gözlemlendi: 9 test önce kırmızı, sonra yeşil), ana akış
sonucu bağımsız olarak kendi `pytest` çalıştırmasıyla ayrıca doğruladı.

**Red-team, 0 sayfalı bir kaynak PDF'in SESSİZCE hiçbir şey yapmadan
"committed" dönmesini buldu** (sıfır çıktı, sıfır kayıt, kullanıcıya
hiçbir gösterge yok) — HEMEN düzeltildi: `PdfReader`in sayfa sayısı 0
ise `PlanApplicationError` fırlatılıyor, sessiz no-op yerine temiz bir
hata. İki riskli kategori (self-overlap, Windows dosya kilidi) AÇIKÇA
izlendi ve bug OLMADIĞI doğrulandı. Toplam 10 yeni test, 187/187 yeşil.

## pdf-birlestirme-merge-operasyonu (Saga #304, epic #29)

**Yeni bir "format agent" katmanı İCAT EDİLMEDİ — MERGE mevcut
Orchestrator dispatch desenine, LIST'e benzer bir özel durum olarak
entegre edildi.** Asıl mimari zorluk: mevcut per-dosya forward/rollback
sözleşmesi (`_FORWARD_OPERATIONS[op](source_path, destination_path)`)
KESİNLİKLE "1 kaynak → 1 hedef" varsayıyordu — MERGE ise "N kaynak → 1
hedef" (N PDF okunur, TEK yeni bir dosya yazılır). `apply_plan`'ın ana
döngüsüne LIST'e benzer (ama gerçekten iş yapan) bir özel dal eklendi:
adım başına TEK bir `FileOperation` kaydı (N tane değil).

**Kaynaklara dokunulmaz — MERGE, COPY'nin rollback semantiğini
paylaşıyor.** En az sürpriz ilkesi: "birleştir" isteği orijinal
dosyaları SİLMEZ/TAŞIMAZ, sadece yeni bir birleşik dosya oluşturur.
Rollback bu yüzden `_rollback_copy`yi (sadece hedefteki yeni dosyayı
sil) doğrudan yeniden kullanıyor — kod tekrarı yok.

**RENAME'in güvenlik disiplini (Saga #290) MERGE'e birebir genişletildi:**
`mergedFileName` hem whitelist/derinlik/sistem-koruması hem de
çakışma/zincir kontrollerinden (`validate_merge_destinations`,
`validate_rename_destinations`in kardeşi) geçiyor.

**`PLAN_SYSTEM_PROMPT`a "birleştir" → "Birleştir" eşlemesi eklendi**
(Saga #292'nin çözdüğü AYNI boşluk sınıfı) — bu olmadan LLM gerçek bir
kullanıcı isteğinden MERGE'i asla seçemezdi.

Codex/Copilot kotası dolu olduğu için (2026-09-15'e kadar, proje
hafızası) test+implementasyon genel bir kodlama subagent'ına
delegasyon disipliniyle (2026-08-18 saga-oto kalıcı kuralı) yazdırıldı
— red→green sırası subagent tarafından gözlemlendi (14 test önce
kırmızı, sonra yeşil), ana akış sonucu BAĞIMSIZ olarak kendi
`pytest` çalıştırmasıyla ayrıca doğruladı.

**Red-team GERÇEK bir HIGH bulgu buldu, HEMEN düzeltildi:**
`mergedFileName`, AYNI step'teki bir kaynak dosyayla çakışabiliyordu —
RENAME'in zaten var olan self-overlap koruması MERGE'e HİÇ taşınmamıştı.
Bu, `_forward_merge`in bir kaynak dosyayı hem okuyup hem AYNI path'e
yazmasına, kaynağı BOZMASINA yol açabilirdi ("kaynaklara dokunulmaz"
garantisinin ihlali). Düzeltme: `models.py`ye RENAME'inkiyle AYNI
desende bir çakışma reddi eklendi. İlişkili bir bulgu da (yarıda
kesilen yazmanın hedefte yarım dosya bırakması) aynı turda düzeltildi:
`_forward_merge` artık geçici-dosya-yaz + atomik-taşı deseni kullanıyor.
4 yeni regresyon testi. Toplam 18 yeni test, 177/177 yeşil.

## requirements-txt-pdf-kutuphane-secimi (Saga #303, epic #29)

**Proje ilk kez bir `requirements.txt`'e kavuştu** — backend şimdiye
kadar sadece elle kurulmuş paketlerle çalışıyordu, hiçbir yerde
sabitlenmiş değildi.

**PDF merge/split için `pypdf` seçildi, `PyMuPDF` DEĞİL.** Ortamda her
ikisi de kuruluydu ama `PyMuPDF`in AGPL-3.0 lisansı, projenin planlanan
ticari satış modeliyle (proje hafızası: "Ürünleştirme Planı") gerçek
bir hukuki risk taşıyordu — AGPL, kaynağı kapalı ticari dağıtım için
uygun değil. `pypdf` saf Python + izin verici lisanslı, hız farkı bu
ölçekte gözlemlenebilir bir sorun değil. `PyMuPDF`/`pypdfium2`
(ortamda kurulu ama kullanılmayacak) bilinçli olarak `requirements.txt`e
EKLENMEDİ.

Bağımsız bir subagent'a delegasyon disiplini (2026-08-18 saga-oto
kuralı) burada da uygulandı — dosya yazımı ve kurulum doğrulaması bir
subagent tarafından yapıldı, ana akış sonucu KENDİ bağımsız
`pip install -r requirements.txt` çalıştırmasıyla ayrıca doğruladı.

**Red-team önerisiyle runtime/test bağımlılıkları ayrıldı:**
`requirements.txt` artık sadece runtime paketlerini (fastapi, uvicorn,
sqlalchemy, openai, pydantic, pypdf) içeriyor; yeni `requirements-dev.txt`
(`-r requirements.txt` ile) `pytest`/`pytest-mock`u ekliyor — proje
ticari kapalı-kod dağıtımı planladığı için gelecekteki bir paketleme
adımının test bağımlılıklarına hiç ihtiyacı olmamalı.

## delete-backup-retention-politikasi (Saga #300, epic #28)

**Kod keşfinde task'ın kendi açıklamasından daha kritik bir bulgu
ortaya çıktı:** yedek fiziksel olarak silinip `Transaction.status`
`"committed"` bırakılsaydı, `revert_transaction`in
`_rollback_completed_operations`i "hedef fiziksel olarak yok → zaten
geri alınmış" kısayolunu (Saga #293) kullanıp bunu SESSİZCE
`"rolled_back"` işaretlerdi — kullanıcı "geri aldım" sanır ama dosya
GERÇEKTE SONSUZA DEK KAYBOLMUŞ olurdu. Çözüm: purge edilen
transaction'lar YENİ bir `"backup_purged"` durumuna geçiriliyor —
`revert_transaction`in ZATEN VAR OLAN "sadece committed transaction'lar
geri alınabilir" guard'ı (Saga #293) bunu hiçbir kod değişikliği
gerekmeden OTOMATİK OLARAK reddediyor.

**Politika: otomatik, 30 gün, SADECE saf-DELETE transaction'lar.**
Karışık operasyonlu (DELETE + MOVE gibi) transaction'lar PURGE
EDİLMİYOR — MOVE/RENAME adımlarının backup_path'i gizli klasör DEĞİL
orijinal konum, bunları da purge etmek hâlâ geri alınabilir adımları
haksız yere kilitlerdi (dar kapsam kararı, kısmi-purge desteklenmiyor).

**`recover_incomplete_transactions`in (Saga #286/#287) AYNI deseni:**
`purge_expired_delete_backups` saf bir çağrılabilir fonksiyon, henüz
hiçbir zamanlayıcı/startup event'ine BAĞLANMADI — projenin hiçbir
yerinde gerçek bir zamanlama mekanizması yok, icat etmek bu task'ın
kapsamını aşardı.

**Red-team GERÇEK bir HIGH bulgu buldu ve HEMEN düzeltildi:** DB
sorgusu TÜM köklerdeki committed transaction'ları döndürüyordu, ama
fiziksel silme SADECE tek bir `allowed_root` altında kontrol
ediliyordu — çok-kök bir kurulumda başka bir köke ait bir transaction
hiçbir şey silinmeden `"backup_purged"` işaretlenip SONSUZA DEK geri
alınamaz hale gelirdi (asıl güvenlik mekanizmasının kendisini tersine
çeviren bir bug). Düzeltme: sadece GERÇEKTEN silinen transaction'lar
durumunu değiştiriyor. Medium-önem bir eşzamanlılık bulgusu (fonksiyon
henüz scheduler'a bağlı olmadığı için bloklamadı) Saga #302 olarak
takip task'ına açıldı. 5 yeni test, 159/159 yeşil.

## son-islemi-geri-al-ui (Saga #295, epic #28)

**Task'ın kendi varsaydığı "backend'in yeni revert-transaction
endpoint'i" HENÜZ YOKTU** — sadece çağrılabilir `revert_transaction()`
(Saga #293) ve salt-okunur `GET /api/transactions` (Saga #294) vardı.
Bu task, dar kapsamlı bir `POST /api/transactions/{id}/revert`
endpoint'ini de İÇERDİ (butonun çağıracağı gerçek bir şey olması için
doğrudan gereken önkoşul).

**`allowedRoot` istemciden geliyor, DB şemasında saklanmıyor** —
`revert_transaction`in `allowed_root` parametresi ZORUNLU (Saga #293
red-team kararı) ama `Transaction`da bir `session_id`/`allowed_root`
kolonu yok (Saga #294'teki AYNI dar-kapsam kararıyla tutarlı: şema
değişikliği yok). İstek gövdesinde `allowedRoot` doğrudan istemciden
gelir (istemci zaten kendi session'ının `selectedFolder`'ını bilir).

**Hata sınıflandırması string-parse ETMEDEN yapıldı:** endpoint,
`revert_transaction`i çağırmadan ÖNCE transaction'ın durumunu kontrol
eder (bulunamadı→404, committed değil→409) — bu sayede
`revert_transaction`den gelen `TransactionRevertError`nun TEK olası
sebebi "precondition geçti ama fiziksel geri alma kısmen başarısız
oldu" olur, bu da 200 + `{"status": "revert_failed"}` ile döner (bir
istemci hatası değil, gerçek bir operasyon sonucu).

**Frontend: iki aşamalı inline onay, modal İCAT EDİLMEDİ (YAGNI).**
Task, PlanCard'ın fail-closed deseniyle tutarlı bir "onay" istiyordu —
ama PlanCard'ın riski FARKLI (backend onayı olmadan buton devre dışı),
burada risk SADECE kullanıcının yanlışlıkla tıklaması. Çözüm: ilk
tıklama butonu "Emin misiniz?" + "Evet, geri al"/"Vazgeç" çiftine
çevirir, SADECE ikinci tıklama gerçek isteği gönderir — mevcut kod
tabanında (`PlanCard`'ın `hasApproved` state deseni) zaten var olan bir
örüntüye tutarlı.

**Buton `transactionId`/`selectedFolder` ikisi de verilmezse hiç
gösterilmiyor** (fail-closed UX kolaylığı — asıl güvenlik sınırı
backend'de zaten var). Gerçek bir apply endpoint'i (Saga #287) hâlâ
olmadığı için `ChatScreen`in bu prop'ları GERÇEKTEN dolduran bir akışı
henüz yok — bu task sadece bileşenin/endpoint'in kendisini doğru inşa
etti, uçtan uca bağlanması ayrı bir iş.

8 yeni backend testi (404/409/200-reverted/200-revert_failed), 11 yeni
frontend testi (görünürlük, iki aşamalı onay, başarılı/kısmi/ağ hatası
senaryoları). Backend 154/154, frontend 135/135, `tsc --noEmit` temiz.

## gecmis-transaction-listesi-endpoint (Saga #294, epic #28)

**Global `/api/transactions`, session-bazlı DEĞİL.** ATDD'de netleşen
gerçek: `Transaction`'ın DB şemasında bir `session_id` FK'sı YOK,
`SessionContext` zaten sadece bellek-içi bir dict (`main.py: _sessions`)
— DB'ye hiç yazılmıyor, süreç yeniden başlayınca kaybolur. Session-bazlı
bir filtre önce yeni bir migration + `apply_plan`'ın her çağrısına
`session_id` geçirmesini gerektirirdi — henüz var olmayan bir apply
endpoint'iyle (Saga #287 bekliyor) birlikte netleşecek bir mimari
genişleme, bu task'ın dar kapsamını aşıyordu. Global liste mevcut
şemaya SIFIR değişiklikle uyumlu.

**Yanıt sadece klasör ADLARINI taşıyor, tam path YOK** (`targetFolders`,
`Path(...).parent.name`) — Saga #283'teki "tam path istemciye
sızdırılmaz" ilkesiyle tutarlı, ayrı bir testle (`test_transactions_endpoint_never_leaks_absolute_paths_only_folder_names`)
doğrulandı.

**`get_db_session` dependency'si, mevcut `get_llm_client` deseniyle
BİREBİR aynı:** her istekte engine/session TAZE oluşturulur, modül
seviyesinde cache YOK — bu, test izolasyonunu (her testin kendi
APPDATA/DB'sini kullanabilmesini) basitçe sağlıyor.

**İki test-altyapısı tuzağı bulunup düzeltildi:** (1) FastAPI generator
dependency'lerinin override'ı da bir GENERATOR fonksiyonu olmalı —
`lambda: iter([session])` FastAPI tarafından "generator değil" olarak
tanınıp override'ın DÖNÜŞ DEĞERİ (iterator'ın kendisi) doğrudan `db`
parametresine bağlandı (`AttributeError: 'list_iterator' object has no
attribute 'scalars'`). (2) `TestClient` endpoint'i bir threadpool
worker thread'inde çalıştırıyor — varsayılan in-memory sqlite engine'i
`check_same_thread=True` ile oluştuğu için "SQLite objects created in a
thread can only be used in that same thread" hatası verdi;
`StaticPool` + `check_same_thread=False` ile çözüldü. (3) Ayrıca hızlı
ardışık iki transaction aynı milisaniyede oluşabildiği için
`created_at.desc()` TEK BAŞINA sıralamayı garanti etmiyordu —
`Transaction.id.desc()` ikincil anahtar olarak eklendi. 150/150 test
yeşil (3 yeni test).

**Red-team önerisiyle `get_db_session` DEĞİŞTİRİLDİ:** ilk taslak
`get_llm_client` ile aynı "her istekte taze oluştur" desenini
kullanıyordu, ama `create_db_engine` her çağrıda tam şema
introspection/`ALTER TABLE` taraması yapıyor — bu, `get_llm_client`'ın
(sadece bir HTTP istemcisi kurmak) maliyet profilinden FARKLI, sık
poll'lanabilecek bir "geçmiş" endpoint'i için gereksiz I/O. Engine/
session-factory artık süreç başına bir kez (lazy) oluşturuluyor.

## rollback-bagimsiz-fonksiyon (Saga #293, epic #28)

**`apply_plan`'ın kendi hata-anı rollback mantığı `_rollback_completed_operations`
paylaşılan yardımcısına çıkarıldı**, üstüne yeni bir `revert_transaction`
public fonksiyonu eklendi — kullanıcının BAŞARIYLA TAMAMLANMIŞ
("committed") bir transaction'ı SONRADAN manuel geri alabilmesinin
önkoşulu (epic 28: Undo/Geri Alma UI'ının temel taşı).

**Yeni durum sözlüğü:** `"reverted"` (tam başarılı manuel geri alma),
`"revert_failed"` (kısmi/tam başarısız) — `apply_plan`'ın kendi
`"rolled_back"` durumundan KASITLI OLARAK ayrı tutuldu, çünkü ikisi
farklı olayları temsil ediyor ("plan hiç commit edilemedi" vs "commit
edilmiş bir işlem sonradan geri alındı").

**Savunma derinliği eklendi:** `revert_transaction`, DB'den okuduğu
`destination_path`/`backup_path`'i doğrudan `shutil.move`'a vermeden
ÖNCE `allowed_root` içinde kaldığını `is_path_allowed` ile tekrar
doğruluyor — `apply_plan`'ın kendi çağrısı sırasındaki `validate_plan_paths`
TAZE değil (DB satırları teorik olarak sonradan bozulmuş olabilir).
Path kök dışındaysa operasyon hiç denenmeden `"rollback_failed"`.

**Kısmi başarısız revert senaryosu testle doğrulandı:** hedef konuma
bilinçli bir çakışma (klasör) yerleştirilip `shutil.move`'un OSError
fırlatması sağlandı — transaction'ın `"revert_failed"` işaretlendiği
VE daha önce başarıyla geri alınan operasyonların durumunun
kaybolmadığı doğrulandı. 8 yeni test, 147/147 yeşil.

## plan-generation-coklu-operasyon-destegi (Saga #292, epic #26)

**ATDD'de bulunan asıl boşluk task'ın kendi tanımından daha temeldi:**
`generate_plan_skeleton` kullanıcının `requestText`'ini hiç almıyordu —
session bu veriyi zaten taşıyordu (`SessionContext.requestText`) ama
`main.py: create_plan` onu LLM'e hiç geçirmiyordu. Bu, epic 26'da
eklenen COPY/DELETE/RENAME/LIST'in (Saga #288-291) gerçek bir kullanıcı
isteğiyle ASLA tetiklenemeyeceği anlamına geliyordu — LLM sadece dosya
adı+tarih görüyor, "sırala mı yedekle mi sil mi" istendiğini bilme
imkânı yoktu.

**Çözüm:** `generate_plan_skeleton`/`build_metadata_prompt`'a
`request_text` parametresi eklendi, `main.py` `session.requestText`'i
geçiriyor. `PLAN_SYSTEM_PROMPT`'a kaba bir doğal-dil→operationType
eşleme rehberi ("sil/temizle/kaldır" → Sil, "kopyala/yedekle" → Kopyala
vb.) ve `newFileNames` şema açıklaması eklendi. Katı bir regex/keyword
eşleştirici YAZILMADI — LLM'in doğal dil anlama gücüne güvenildi.

**Canlı DeepSeek doğrulaması yapıldı (kullanıcı API ödemesini yaptı,
oturum içinde talep etti).** İki gerçek istekle test edildi: "Bu eski
PDF dosyalarini sil" → doğru şekilde `operationType: "Sil"` seçti;
"Bu dosyalarin ismini X ve Y olarak degistir" → doğru şekilde
`operationType: "Yeniden Adlandır"` + doğru sırada/uzunlukta
`newFileNames` üretti. Yeni prompt rehberinin gerçek bir LLM'le
çalıştığı uçtan uca doğrulandı (ATDD'deki "bilinmeyen" riski kapatıldı).
139/139 test yeşil.

## orchestrator-list-operasyonu (Saga #291, epic #26)

**LIST tamamen salt okunur/inert — epic 26'nın en dar kapsamlı task'ı.**
ATDD'de netleştirilen karar: "listeleme" zaten `/api/plan` sırasında
oluyor (backend `discover_pdf_files` ile tarıyor, `PlanCard` gösteriyor,
Saga #262/#277) — `OperationType.LIST`'in `apply_plan`'da (onaydan
SONRA çalışan, dosya sistemini mutasyona uğratan katman) yapması
gereken TEK şey hiçbir şey yapmamak. Ayrı bir "envanter" DB kaydı ya da
özel bir sohbet gösterimi icat edilmedi (YAGNI) — LIST step'leri ana
döngüde `continue` ile tamamen atlanıyor: hiçbir dosya sistemi çağrısı,
hiçbir `FileOperation` kaydı.

`OperationType` enum'undaki tüm 5 değer (MOVE/COPY/DELETE/RENAME/LIST)
artık destekleniyor — "desteklenmeyen operationType" test senaryosu
(önceden LIST örnek olarak kullanılıyordu) artık anlamsız hale geldi,
kaldırıldı.

**Red-team: 2 bulgu belgelendi, biri test-kapsamı boşluğu hemen
kapatıldı.** (1) `_SUPPORTED_OPERATION_TYPES` kontrolü artık ölü kod —
enum'daki tüm değerler destekleniyor, gerçek bir enum değeriyle
tetiklenemiyor. Bu, gelecekte enum'a yeni bir tür eklenip bu set'in
güncellenmesi UNUTULURSA devreye girecek meşru bir defense-in-depth
guard'ı — silinmedi, ama testsiz kalmıştı; `_SUPPORTED_OPERATION_TYPES`'ı
monkeypatch ile daraltan bir regresyon testi eklendi. (2) LIST'in
`_distribute_files_to_steps`'in "dosya başına tek step" münhasırlığına
tabi olması, "şu dosyaları listele VE taşı" gibi tek bir meşru isteği
(aynı dosya hem LIST hem MOVE'da) reddediyor — mimari bir sınırlama
olarak belgelendi (LIST'i transaction akışından TAMAMEN çıkarmak daha
temiz olurdu ama bu task'ın dar kapsamını aşıyor, kapsam dışı bırakıldı).
136/136 test yeşil (3 yeni: LIST-only plan, karışık LIST+MOVE planı,
dead-code guard regresyonu).

## orchestrator-rename-operasyonu (Saga #290, epic #26)

**Gerçek şema boşluğu kapatıldı: `PlanStep.newFileNames`.**
`targetFolder` (YYYY-MM'e kilitli) RENAME için tamamen anlamsızdı — yeni
dosya adını taşıyacak hiçbir alan yoktu. `PlanStep`e `newFileNames:
list[str] | None = None` eklendi — `fileNames` ile PARALEL bir liste
(Saga #286'nın "isimle eşleştirme" desenini genişletiyor). Şema
seviyesinde sıkı kurallar: `operationType==RENAME` ise ZORUNLU +
uzunluk eşleşmesi + tekillik (iki dosya aynı yeni isme çakışmasın —
aksi halde dosya sistemi seviyesinde sessiz veri kaybı olurdu) +
path-separator-free (Saga #272 defense-in-depth deseni); başka bir
operationType'ta `None` OLMALI (şema netliği).

**Orchestrator tarafı: RENAME, MOVE'un fiziksel ikizi.** `_forward_move`/
`_rollback_move` AYNEN paylaşılıyor — tek fark `destination_path`'in
NASIL hesaplandığı: MOVE için `target_dir/dosya`, RENAME için
`allowed_root/yeni_isim` (aynı klasör, farklı isim). DELETE'teki gibi
`targetFolder` RENAME için de kullanılmıyor (bilinen sınırlama, Saga
#292'ye bırakıldı).

**Red-team: HIGH severity gerçek veri kaybı bug'u bulundu ve deneysel
olarak doğrulandı — commit DURDURULDU, hemen düzeltildi.** İlk
implementasyon üç gerçek boşluk taşıyordu: (1) `shutil.move`, RENAME
hedefinde ZATEN VAR OLAN bir dosyayı (planın hiç dokunmadığı, ör.
kullanıcının önemli bir dosyası) hiçbir hata vermeden SESSİZCE üzerine
yazıyordu — red-team bunu gerçekten deneyerek kanıtladı. Düzeltme:
`backend/security.py: validate_rename_destinations()` eklendi
(`validate_plan_paths` içinden otomatik çağrılıyor) — hedef isim
`allowed_root`'ta zaten varsa VE planın bilmediği bir dosyaysa tüm plan
reddedilir. (2) Aynı step'in `fileNames`'i içinde tekrar eden bir isim
(`["a.pdf","a.pdf"]`) `dict(zip(fileNames, newFileNames))`'in bir
eşlemeyi sessizce kaybetmesine yol açardı — `PlanStep`e
`file_names_have_no_duplicates` validator'ı eklendi. (3) `newFileNames`
aynı step'in `fileNames`'iyle (kaynaklarla) ÇAKIŞABİLİYORDU (ör.
a.pdf→b.pdf VE b.pdf→c.pdf aynı step'te) — "zincirleme rename",
b.pdf'in orijinal içeriğinin sessizce kaybolmasına yol açardı; bu artık
şema seviyesinde tamamen yasak.

**Red-team devam etti: 2 tur daha, 2 ayrı HIGH severity bug daha
deneysel kanıtlandı — toplam 4 tur, 3 HIGH severity gerçek veri kaybı
bug'u.** Bu, projenin şimdiye kadarki en yoğun red-team döngüsüydü.
- **Tur 2:** Yukarıdaki (3) numaralı düzeltme SADECE aynı step İÇİNDE
  çalışıyordu — FARKLI step'ler arasında zincir hâlâ mümkündü (step 0:
  a.pdf→b.pdf, step 1: b.pdf→c.pdf). `apply_plan` uçtan uca gerçek
  dosyalarla çalıştırılıp DENEYSEL OLARAK kanıtlandı: b.pdf'in orijinal
  içeriği hiçbir yerde iz bırakmadan kayboluyordu. Kök neden:
  `_distribute_files_to_steps`'in çapraz-step tekillik kontrolü bunu
  YAKALAMIYORDU çünkü b.pdf gerçekten `pdf_files`'ta (disk taramasından)
  var — sadece AYNI ZAMANDA başka bir step'in YAZDIĞI isimle çakışıyor.
  → `validate_rename_destinations`'a PLAN GENELİNDE "bir isim hem
  RENAME kaynağı hem RENAME hedefi olamaz" kontrolü eklendi.
- **Tur 3:** Tur 2'nin düzeltmesi CASE-SENSITIVE'ti — Windows
  case-insensitive olduğu için `a.pdf→B.PDF` + `b.pdf→c.pdf` zinciri
  (sadece harf farkı) hâlâ kaçıyordu (deneysel kanıtlandı). AYRICA bu
  düzeltme kendisi yeni bir false-positive yarattı: meşru bir "sadece
  harf büyüklüğü değiştir" rename'i (`a.pdf`→`A.pdf`) da yanlışlıkla
  reddetmeye başlamıştı. → `os.path.normcase` ile TÜM isim
  karşılaştırmaları normalize edildi (hem `security.py` hem
  `models.py`), ÇİFT-bazlı (pair-exclusion, `dest_index !=
  source_index`) mantıkla kendi-kendine rename ile gerçek zincir ayırt
  edildi.
- **Tur 4 (doğrulama):** Pair-exclusion mantığının kendisi yeni bir
  regresyon açıp açmadığı (3'lü rotasyon senaryosu — a→b→c→a — dahil)
  deneysel olarak doğrulandı, açık bulunmadı, `ready_to_commit: true`,
  döngü kapatıldı.

Kök neden deseni (3 turun ortak paydası): dosya adı karşılaştırmaları
Python string eşitliğiyle yapılıyordu ama gerçek çakışma kararını
işletim sisteminin (Windows) dosya sistemi semantiği veriyordu. 134/134
test yeşil (25 yeni test toplamda). Mevcut bir test
(`test_apply_plan_rejects_non_move...`) artık RENAME yerine LIST'i
"desteklenmeyen" örneği olarak kullanıyor.

## orchestrator-delete-operasyonu (Saga #289, epic #26)

**DELETE eklendi — mevcut MOVE/COPY sözleşmesi hiç değiştirilmeden.**
Kritik tasarım kararı: `destination_path`/`backup_path` alanlarının
anlamı TÜM operationType'larda AYNI kalıyor —
`destination_path` = "forward işlem sonrası dosyanın fiziksel olarak
bulunduğu yer", `backup_path` = "rollback'in geri yükleyeceği konum".
DELETE için bu: `destination_path` = gizli yedek konumu
(`allowed_root/.windows-ai-files-backup/<txn_id>/<dosya>`, derinlik 3,
`MAX_PATH_DEPTH`'i aşmıyor), `backup_path` = orijinal kaynak konumu. Bu
sözleşme sayesinde DELETE'in rollback'i AYRI bir fonksiyon YAZMADAN
`_rollback_move`'u (zaten "hedefi backup_path'e taşı" yapıyor) doğrudan
kullanabildi — Saga #288'in dispatch mimarisinin gerçekten yeniden
kullanılabilir olduğu bu task'ta kanıtlandı.

`_forward_delete` önce fiziksel yedeği alır (`shutil.copy2`), SONRA
kaynağı siler — sıra bilinçli: yedekleme başarısız olursa kaynak hâlâ
yerinde kalır, veri kaybı riski yok. DELETE'in gerçek bir hedef klasörü
olmadığı için (`targetFolder` şema gereği hâlâ zorunlu ama kullanılmıyor
— bilinen sınırlama, Saga #292'ye bırakıldı) `target_dir.mkdir` DELETE
step'leri için atlanıyor.

Mevcut bir test (`test_apply_plan_rejects_non_move_operation_types...`)
artık geçersiz örnek kullanıyordu (DELETE'i "desteklenmeyen" örneği
olarak kullanıyordu) — RENAME'e güncellendi.

**Red-team: 2 bulgu.** (1) `.windows-ai-files-backup` klasörünün
`discover_pdf_files` tarafından yanlışlıkla yeniden keşfedilmesi
YAPISAL olarak zaten imkansızdı (tarama recursive değil, yedekler 2
seviye derinde) ama bu koruma sadece "kaza eseri" doğruydu, kodda
AÇIKÇA belgelenmiyordu — `pdf_discovery.py`'ye gizli (nokta ile
başlayan) dosya/klasörleri atlayan açık bir guard + regresyon testi
eklendi (ileride tarama recursive hale getirilirse "silinmiş"
dosyaların yanlışlıkla yeniden keşfedilmesini yapısal olarak engelliyor).
(2) `.windows-ai-files-backup` hiçbir zaman temizlenmiyor — disk
kullanımı sınırsız büyüyebilir, "silinmiş" dosyalar aslında sonsuza dek
diskte kalıyor (veri saklama riski). Bu, gerçek bir mimari karar
(retention politikası) gerektiriyor — Saga #300 olarak Undo UI epic'ine
(Saga #28) bağlı bir takip task'ı açıldı, bloklayıcı değil (henüz
gerçek apply endpoint'i yok). 113/113 test yeşil.

## orchestrator-copy-operasyonu (Saga #288, epic #26)

**Epic 26'nın ilk task'ı: COPY desteği eklendi — "tek tip rollback"
mimarisi operation_type-aware hale getirildi.** Önceden `apply_plan`
sadece MOVE'u destekliyordu ve rollback her zaman "hedefi kaynağa geri
taşı" varsayımıyla çalışıyordu. COPY'de kaynak hiç değişmiyor —
rollback'in "hedefteki kopyayı sil" yapması gerekiyordu, bu yüzden
ileri/geri işlemler `_FORWARD_OPERATIONS`/`_ROLLBACK_OPERATIONS`
dispatch dict'lerine çıkarıldı (`OperationType` → fonksiyon eşlemesi).
Bu, ATDD'de bilinçli olarak DELETE (Saga #289) task'ının üçüncü bir
dal eklemesini kolaylaştıracak şekilde tasarlandı.

`backup_path` COPY için de `source_path` ile dolduruluyor (şema
tutarlılığı için) ama rollback anlamı MOVE'dan farklı — dispatch,
`FileOperation.operation_type` alanından (`OperationType(...)` ile
enum'a çevrilerek) doğru rollback fonksiyonunu seçiyor. 108/108 test
yeşil (2 yeni: COPY başarı + COPY-sonrası-rollback, kaynağın
dokunulmadığını doğrulayan assertion dahil).

**Red-team: exception-masking boşluğu hemen düzeltildi.** Rollback
dispatch araması (`OperationType(operation.operation_type)` +
`_ROLLBACK_OPERATIONS[...]`) sadece `except OSError` içindeydi —
bilinmeyen/bozuk bir `operation_type` (ör. gelecekte DELETE eklenip
rollback tablosuna eklenmesi unutulursa) `ValueError`/`KeyError`
fırlatıp orijinal exception'ı (`exc`) maskeler, transaction'ı sonsuza
dek `"pending"` bırakırdı — Saga #276'nın kendi yorumunun uyardığı TAM
O sınıf hata, sadece farklı bir exception tipiyle. `except (OSError,
ValueError, KeyError)` olarak genişletildi. 109/109 test yeşil (3.
yeni test: rollback tablosu boşken bile orijinal hatanın maskelenmeden
fırlatıldığını ve transaction'ın "pending" kalmadığını doğruluyor).

## asistan-mesaji-markdown-degerlendirmesi (Saga #282, epic #24)

**Yeniden değerlendirildi, kod değişikliği YAPILMADI — öncül hâlâ
geçerli değil.** Bu task'ın önkoşulu ("gerçek bir backend/LLM
entegrasyon task'ı tamamlandığında ele alınmalı") Saga #287 ile
teknik olarak sağlandı (App.tsx artık gerçekten `/api/plan`'a
bağlı). Ama gerçek entegrasyonu inceleyince görülen: asistan
mesaj metni HÂLÂ LLM'in serbest metni DEĞİL — `App.tsx: requestPlan`
sadece iki sabit, tek satırlık string üretiyor ("Önerilen plan:" /
"Seçili klasörde işlenecek PDF bulunamadı."). Backend'in LLM'i sadece
YAPISAL `PlanSkeleton` JSON'u (steps) üretiyor, hiçbir zaman sohbet
balonuna akan serbest metin üretmiyor — `PlanCard`/`ResultCard` da
yapısal veriyi render ediyor, uzun paragraf yok. Red-team'in
öngördüğü risk ("uzun yapısal olmayan paragraflar") mimari olarak
HÂLÂ ORTAYA ÇIKMIYOR. Bir markdown parser bağımlılığı eklemek şu an
sıfır gerçek karşılığı olan spekülatif bir iş olurdu (YAGNI). Bu
değerlendirme belgelendi — eğer ileride backend'in LLM'i doğrudan
serbest metin üretip sohbete akıtan bir özellik eklenirse (bugün
planlı değil), bu task o zaman gerçek bir kod değişikliğiyle yeniden
açılmalı.

## plan-validation-wiring (Saga #281, epic #24)

**Yazılmış ama hiç bağlanmamış bir güvenlik kontrolü nihayet
bağlandı.** `validatePlanResponse` (Saga #262/#280) uzun süredir
`planValidation.ts`'te duruyordu ama `App.tsx`'in gerçek backend'e
bağlanması (Saga #287) olmadan bağlanacak bir yer yoktu. Artık
`App.tsx: requestPlan`, backend'den gelen ham JSON'u `PlanCard`'a
vermeden önce `validatePlanResponse`'tan geçiriyor — geçersizse
(`ok: false`) `PlanCard` HİÇ render edilmiyor, mevcut `planError`/retry
mekanizmasına (Saga #267) düşülüyor.

**`PlanStep.operationType` tipi sıkılaştırıldı.** `string`'den
`(typeof KNOWN_OPERATION_TYPES)[number]`'a — `KNOWN_OPERATION_TYPES`
sabiti `PlanCard.tsx`'e taşındı (tipin sahibi orası, dairesel import'a
girmemek için `planValidation.ts` oradan import edip re-export ediyor).
`PlanCard.test.tsx`'teki serbest-string test verisi ('İkinci'/'Birinci'
operationType olarak kullanılmıştı, sırlama testiydi asıl amacı)
gerçek operationType değerlerine çevrildi, sıralama ayrımı
`targetFolder` üzerinden yapıldı.

**Red-team: gerçek bir bug bulundu, hemen düzeltildi.** İlk
implementasyonda `App.tsx` `{ ...validation.plan, securityStatus:
'approved' }` yazıyordu — spread SONRASINDA literal `'approved'`
atandığı için backend gerçekten `securityStatus: 'rejected'` dönse
BİLE bu koşulsuzca eziliyordu. Düzeltme: `validation.plan.
securityStatus ?? 'approved'` — backend açıkça bir değer gönderirse
o kullanılır, sadece hiç gönderilmemişse `approved`a düşülür. 125/125
test yeşil, `tsc --noEmit` temiz.

## security-gate-reusable-dependency (Saga #283, epic #25)

**Epic 25'in son task'ı — Security Gate yeniden kullanılabilir hale
getirildi.** `backend/main.py`'ye `get_session_or_404(payload:
PlanRequest) -> SessionContext` FastAPI `Depends`'i çıkarıldı — `/api/plan`
artık `session = _sessions.get(...)` + 404 kontrolünü elle tekrarlamıyor,
`Depends(get_session_or_404)` kullanıyor. Saga #285'ten sonra
`PlanRequest`'in sadece `sessionId` taşıması sayesinde endpoint artık
`payload`'a hiç ihtiyaç duymuyor — bu, dependency'nin body'yi kendi
başına parse edip sadece çözümlenmiş `SessionContext`'i vermesini
mümkün kıldı.

`PathWhitelistError` artık `offending_path`/`allowed_root`/`reason`/
`description` alanlarını taşıyor (`str(exc)` eski okunabilir formatı
aynen üretmeye devam ediyor — geriye dönük uyumlu).

**Red-team: "yapı var ama hiç kullanılmıyor" bulgusu hemen düzeltildi.**
İlk implementasyonda `main.py` hâlâ `str(exc)`'i (tam mutlak path dahil)
403 detail'e koyuyordu — yeni structured field'lar YAPI olarak vardı
ama gerçek bir davranış değişikliği getirmiyordu (YAGNI riski,
kullanılmayan soyutlama). Düzeltme: 403 yanıtı artık SADECE kısa
`exc.reason`'ı (`f"{description} {reason}"`, ör. "Kaynak dosya izin
verilen kök dışında") içeriyor — tam mutlak path'ler (`offending_path`/
`allowed_root`, sunucunun dosya sistemi yapısı hakkında keşif bilgisi
verebilir) artık istemciye SIZDIRILMIYOR, sadece sunucu logunda
(`logger.warning`) kalıyor. 106/106 test yeşil (2 yeni: structured
field'lar + 403 yanıtının tam path içermediğini doğrulayan regresyon
testi).

**Epic 25 (MVP: PDF'leri tarihe göre sıralama) TAMAMLANDI** — 271-277 +
283-287 (17 task, 14'ü orijinal backlog + 3'ü red-team'in bulduğu
mimari boşluklardan doğan takip task'ı) hepsi `done`.

**Epic 25 (MVP: PDF'leri tarihe göre sıralama) TAMAMLANDI** — 271-277 +
283-287 (17 task, 14'ü orijinal backlog + 3'ü red-team'in bulduğu
mimari boşluklardan doğan takip task'ı) hepsi `done`.

## chatscreen-controlled-app-wiring (Saga #287, epic #25)

**Epic 25'in uçtan uca hedefi ilk kez gerçekten çalışır hale geldi.**
`ChatScreen` dual-mode'a çevrildi: `messages`/`onMessagesChange`
prop'ları VERİLİRSE controlled çalışır (App.tsx dışarıdan asenkron bir
plan yanıtı ekleyebilir), verilmezse (mevcut 30+ test) davranış
eskisiyle birebir aynı kalır — hiçbir mevcut test kırılmadı. `App.tsx`
artık gerçekten `POST /api/plan(sessionId)` çağırıyor, başarılı yanıtı
yeni bir assistant `ChatMessage.plan`'ına (`securityStatus: 'approved'`
— backend zaten whitelist'ten geçirdiği için) yazıyor, hata durumunda
mevcut `planError`/retry mekanizmasına (Saga #267) yönlendiriyor.
`onApprovePlan` bilinçli olarak sadece loglar — gerçek bir apply/
Orchestrator çağrısı yapmıyor (Saga #274 kasıtlı endpoint'siz).

Bu task'ın tamamlanmasıyla Saga #273'ün onay UI'ı (PlanCard) ve Saga
#277'nin ResultCard'ı (henüz sonuç göstermiyor — apply endpoint'i yok,
ama mapping fonksiyonu hazır) ilk kez gerçek backend veriyle
tetiklenebilir hale geldi.

**Red-team: race-condition bulgusu hemen düzeltildi.** `requestPlan`in
iki çakışan çağrısı (ör. bir istek sürerken "Tekrar dene"ye basılırsa)
arasında hiçbir sıralama koruması yoktu — hangi yanıt önce gelirse o
kazanıyordu, eski bir yanıt yeni/başarılı bir planı sessizce ezebilirdi.
`latestRequestIdRef` ile her `requestPlan` çağrısı kendi isteğinin hâlâ
"en son" olup olmadığını kontrol ediyor, değilse state güncellemesini
atlıyor. (Bu senaryoyu gerçek UI üzerinden tetikleyen bir test
YAZILAMADI — `Gönder` butonu zaten `isGeneratingPlan` sırasında disabled
olduğu için normal kullanımda çakışma oluşmuyor; guard tamamen
defansif/gelecekteki değişikliklere karşı.) 123/123 frontend test
yeşil (7 yeni), `tsc --noEmit` temiz.

## appdb-sema-goc-shimi (Saga #284, epic #25)

**alembic yerine minimal "eksik kolon varsa ALTER TABLE" shim'i.** Saga
#275 red-team bulgusu: `create_db_engine`'in `Base.metadata.create_all`'ı
yeni tablo eklemede idempotent ama VAR OLAN bir tabloya yeni kolon
eklendiğinde sessizce hiçbir şey yapmıyordu — gerçek kullanıcı
makinelerinde `app.db` oluştuktan sonra bu, sessiz veri kaybına/
`sqlite3.OperationalError: no such column` hatalarına yol açardı.
`backend/db.py: _add_missing_columns(engine)` eklendi — `create_all`den
hemen sonra her tabloyu `inspect()` ile gerçek DB şemasıyla karşılaştırıp
eksik kolonları `ALTER TABLE ADD COLUMN` ile ekliyor. alembic KASITLI
OLARAK seçilmedi — proje henüz hiç Python bağımlılık dosyasına sahip
değil (task_0ab06e5e olarak flaglenmişti), yeni ağır bir bağımlılık
eklemek dar kapsam ilkesiyle çelişirdi; kolon silme/tip değiştirme
(SQLite'ta tablo yeniden oluşturmayı gerektirir) MVP'de ihtiyaç
olmadığı için desteklenmiyor.

**Red-team: sessiz şema sürüklenmesi bulundu, hemen düzeltildi.**
`_add_missing_columns` kolon eklerken SADECE tipi üretiyordu, `NOT NULL`
kısıtını hiç emin etmiyordu — bu, taze kurulumlarda (`create_all`: NOT
NULL doğru uygulanır) ile yükseltilmiş kurulumlarda (bu ALTER yolu: NOT
NULL sessizce kaybolurdu) arasında SESSİZ bir şema sürüklenmesine yol
açardı (bugün hiçbir NOT NULL kolon yok, ama gelecekte biri eklerse
fark edilmeden gerçekleşirdi). Düzeltme: varsayılan değeri olmayan NOT
NULL bir kolon eklenmeye çalışılırsa shim artık GÜRÜLTÜLÜ bir
`RuntimeError` ile başarısız oluyor (sessizce nullable'a düşmek yerine)
— "gerçek bir migration aracı gerekiyor" mesajıyla. 105/105 test yeşil
(4 yeni: sıfırdan oluşturma, eksik kolon ekleme + veri korunumu,
idempotentlik, NOT NULL guard).

## orchestrator-planstep-dosya-listesi-ve-kurtarma (Saga #286, epic #25)

**Kırılgan pozisyonel dağıtım kaldırıldı — `PlanStep.fileNames`
eklendi.** Saga #274 red-team bulgusu: `PlanStep` hangi dosyanın
kendisine ait olduğunu taşımıyordu, Orchestrator `pdf_files`'ı sırayla
dağıtıyordu (LLM sırası uyuşmazsa dosyalar YANLIŞ tarih klasörüne
taşınabilirdi, hiçbir runtime kontrol bunu yakalayamazdı).
`PlanStep.fileNames: list[str]` eklendi, `affectedFileCount ==
len(fileNames)` şema seviyesinde zorunlu (`model_validator`). LLM
prompt'u (`plan_generation.py`) buna göre güncellendi.
`orchestrator.py: _distribute_files_to_steps` artık isimle eşleşme
yapıyor — bilinmeyen bir dosyaya atıf yapan, bir dosyayı iki kez atayan
veya bir dosyayı hiç atamayan plan TAMAMEN reddediliyor (hiçbir dosyaya
dokunulmadan).

**Crash-recovery fonksiyonu eklendi (henüz bağlanmadı).**
`recover_incomplete_transactions(session)` — `status="pending"` kalmış
transaction'ları tarar, her `FileOperation`'ı `destination_path`'in
fiziksel varlığına göre uzlaştırır (varsa `"completed"`, yoksa
`"rolled_back"`). Bilinçli kapsam kararı: gerçek bir FastAPI startup
event'ine BAĞLANMADI — bağlanacak gerçek bir apply-endpoint akışı henüz
yok (Saga #287'nin devamı). Saf, test edilebilir bir fonksiyon olarak
bırakıldı.

**Red-team: gerçek bir bug bulundu ve hemen düzeltildi (ready_to_commit:
false).** İlk implementasyon `recover_incomplete_transactions`'da sadece
kendi durumu `"pending"` olan `FileOperation`'ları yeniden doğruluyordu.
Ama `apply_plan`'ın rollback except bloğu bir operasyonu bellek-içi
`"completed"`→`"rolled_back"`e çevirdikten SONRA ama nihai
`session.commit()`'ten ÖNCE süreç çökerse, DB'de o operasyon hâlâ
`"completed"` görünür — dosya fiziksel olarak zaten geri taşınmış
olsa bile. Düzeltme: transaction hâlâ `"pending"` olduğu sürece
İÇİNDEKİ HER operasyon (kendi durumu ne olursa olsun) dosya sistemine
karşı yeniden doğrulanıyor. İkinci düşük-önem bulgu da düzeltildi:
`PlanStep.fileNames` artık `PdfFileMetadata.filename` ile aynı
path-separator validator'ına tabi (Saga #272 defense-in-depth deseniyle
tutarlılık — önceden traversal koruması sadece orchestrator'ın isim
eşleşmesine "kaza eseri" dayanıyordu, şema seviyesinde değildi).
101/101 backend test yeşil (11 yeni test).

## gercek-pdf-kesfi-backend-tarama (Saga #285, epic #25)

**`pdfFiles` istemciden kaldırıldı — backend `selectedFolder`'ı kendisi
tarıyor.** Saga #273/#277 keşiflerinde bulunan boşluk: `PlanRequest.
pdfFiles: list[PdfFileMetadata]` istemciden bekleniyordu ama bunu
dolduracak hiçbir gerçek mekanizma yoktu (ne backend'de tarama, ne
frontend'de native fs erişimi). Karar (a): backend kendi tarasın —
yeni native bağımlılık gerektirmiyor, whitelist'in güvendiği "kaynak
dosya" listesini istemcinin kontrolünden çıkarıyor. Yeni
`backend/pdf_discovery.py: discover_pdf_files(folder)` — SADECE
`folder`ın doğrudan altındaki `.pdf` dosyalarını (case-insensitive,
recursive DEĞİL) listeler, `createdAt`'i `Path.stat().st_ctime`'dan
türetir. `PlanRequest` artık sadece `sessionId` taşıyor.

**Mimari boşluk bulundu, ayrı task'a bağlandı: `ChatScreen` controlled
değil.** Backend tarafı tamamlandı ve test edildi ama gerçek uçtan uca
wiring (`App.tsx`→`/api/plan`→sohbete yansıma) hâlâ MÜMKÜN DEĞİL —
`ChatScreen.tsx` mesaj listesini tamamen kendi iç state'inde tutuyor,
`initialMessages` sadece mount anında okunuyor. App.tsx'in sonradan
asenkron bir plan yanıtı eklemesinin hiçbir yolu yok. Bu, backend
taramasından bağımsız, ayrı bir frontend refactor'ü gerektiriyor — Saga
#287'ye bağlandı (bu task'a `depends_on`). 94/94 backend test yeşil (7
yeni: `test_pdf_discovery.py`; plan endpoint testleri gerçek `tmp_path`
dosyalarıyla yeniden yazıldı — client-taraflı traversal testleri
ARTIK GEÇERSİZ, çünkü filename artık gerçek dosya sisteminden geliyor,
istemci kontrol edemiyor; yerine sistem-kök koruması + non-pdf/alt-klasör
filtreleme testleri eklendi).

**Red-team: 1 bulgu hemen düzeltildi (410 Gone), 1 bulgu docstring'de
belgelendi.** (1) `selectedFolder` session oluşturulduktan sonra
silinirse/taşınırsa, eskiden bu "0 PDF bulundu" ile aynı şekilde 200
dönüyordu — kullanıcının görmesi gereken gerçek durum farklı
("klasör bulunamadı" vs "klasör boş"). `main.py`'ye
`allowed_root.is_dir()` kontrolü eklendi, 410 Gone dönüyor artık. (2)
`st_ctime` sadece Windows'ta gerçek "oluşturulma zamanı"dır (POSIX'te
"meta veri değişikliği zamanı") — proje Windows-only MVP kapsamında
kabul edilebilir, ama sessizce yanlış davranma riski docstring'de
açıkça belgelendi. 95/95 backend test yeşil.

## sonuc-karti-plan-tamamlanma-gosterimi (Saga #277, epic #25)

**Yeni `ResultCard` component'i — `PlanCard`'ın onay sorumluluğuyla
karıştırılmadı.** `ChatMessage`'a ayrı bir `result?: TransactionResult`
alanı eklendi (`{ fileCount, destinationFolders, status }`) — `Plan`
tipini genişletmek yerine ayrı tutuldu, çünkü `PlanCard` zaten
fail-closed onay mantığıyla (Saga #265/#266/#273) yüklü; sonuç göstermek
anlamsal olarak farklı bir sorumluluk. Boş `destinationFolders` durumu
çökmeden net bir metinle gösteriliyor (AC-6).

**Bu görevden itibaren skill'in artifact disiplinine (atdd.md/plan.md/
verify_report.md) dönüldü** — önceki 5 task'ta (271-276) bu dosyalar
yazılmamıştı, kullanıcı fark edip sordu; kararlaştırılan: geçmiş
task'lar için geriye dönük yazılmayacak, bundan sonrakiler için
`artifacts/<task-slug>/` altına gerçekten yazılacak.

**Bilinçli kapsam kararı: HTTP wiring yok, sadece izole component
testleri.** Saga #273/#274/#276'daki aynı önkoşul burada da geçerli —
`App.tsx` gerçek bir backend çağrısı yapmıyor (Saga #285), bu yüzden
`ResultCard` mock/örnek `TransactionResult` props'uyla test edildi,
uçtan uca doğrulanamadı.

**Red-team: backend↔frontend eşleşme boşluğu hemen kapatıldı.**
`TransactionResult.destinationFolders`'ın backend'in TAM dosya yolu
taşıyan `destination_path` alanından nasıl türetileceği (klasör
çıkarma + tekilleştirme) ve `status` alanının backend'in
`"pending"|"committed"|"rolled_back"` değerleriyle nasıl eşleşeceği hiç
belirtilmemişti — bu, #285 wiring'i sırasında zaman baskısı altında
test edilmeden yazılma riski taşıyordu. `ui/src/lib/transactionResult.ts:
toTransactionResult()` ile bu eşleme saf bir fonksiyon olarak yazıldı ve
test edildi (`"rolled_back"→"failed"`, fileCount=0 — Saga #274/#276'nın
hep-ya-da-hiç atomik geri alma garantisi nedeniyle "partial" DEĞİL).
116/116 frontend test yeşil (10 yeni test).

## kismi-hatada-ters-sirali-geri-alma (Saga #276, epic #25)

**Rollback artık kaydedilen alanlardan okuyor, paralel bir bellek-içi
yapıdan değil.** Saga #274'ün ilk implementasyonu geri almayı ayrı bir
`applied: list[tuple[...]]` yardımcı listesiyle yapıyordu — işlevsel
olarak doğruydu ama görev tanımının ("backup_path ve işlem kayıtlarını
kullanarak") istediği şey değildi. Refactor: `applied` artık sadece
`FileOperation` nesnelerinin bir listesi, rollback sırasında
`destination_path`/`backup_path` DOĞRUDAN bu DB kayıtlarından okunuyor
(görev tanımının istediği "backup_path ve işlem kayıtlarını kullanarak"
ifadesiyle artık birebir örtüşüyor).

**Netleştirme (red-team bulgusu): bu, süreç-çökmesi senaryosuna karşı
kurtarma SAĞLAMIYOR.** `applied` hâlâ TAMAMEN bellek-içi bir liste —
`apply_plan` çalışırken process çökerse bu liste kaybolur, hiçbir şey
rollback'i tetiklemez, transaction DB'de "pending" asılı kalır. Bu
refactor SADECE aynı process/çağrı içindeki rollback'in DOĞRU
KAYNAKTAN (DB alanları) okumasını sağlıyor — gerçek bir başlangıçta
(startup) "yarım kalmış transaction'ları tara ve geri al" mekanizması
YOK, bu Saga #286'nın konusu ve henüz yazılmadı.

**Ters sıra davranışı artık açıkça test ediliyor.** 3 dosyalı bir plan,
3. dosyanın taşınması sırasında başarısız olacak şekilde kuruldu;
`move_order` listesi doğrulandı — geri alma hareketleri gerçekten TERS
sırayla (önce en son tamamlanan) gerçekleşiyor.

**"Sohbete... net hata durumu dönmelidir" kısmı henüz kablolanmadı.**
`PlanApplicationError` net, açıklayıcı bir mesajla fırlatılıyor (backend
tarafı tamam) ama bunu sohbet arayüzüne göstermek `App.tsx`'in gerçek bir
apply-çağrısına bağlanmasını gerektiriyor — bu, Saga #273/#285'te
belgelenen aynı önkoşula (gerçek `pdfFiles` kaynağı yok) takılıyor, ayrı
bir task açılmadı çünkü zaten #285'in kapsamına giriyor. 86/86 test yeşil.

## orchestrator-transactionli-plan-uygulama (Saga #274, epic #25)

**İlk gerçek dosya I/O: `backend/orchestrator.py: apply_plan()`.** Onaylı
bir planı `validate_plan_paths` (Saga #271/#272) ile yeniden doğrulayıp
(defense-in-depth — çağıran ne kadar önce doğrulamış olursa olsun),
hedef tarih klasörlerini oluşturup PDF'leri `shutil.move` ile taşıyor, her
dosya için `record_file_operation` çağırıp (Saga #275) transaction'a
bağlıyor. Bir adım başarısız olursa o ana kadar taşınmış dosyalar ters
sırayla eski konumlarına geri taşınıyor, `PlanApplicationError` fırlatılıyor
— kısmi başarı asla dönmüyor.

**Bilinçli kapsam kararı: endpoint YOK, sadece saf fonksiyon.** Saga
#273/#285 bulgusuyla tutarlı: frontend zaten gerçek `pdfFiles`
gönderemiyor (PDF keşif mekanizması yok), bu yüzden bir HTTP endpoint'i
eklense de çağrılamaz, test edilemeyen ölü kod olurdu. `apply_plan`
tamamen endpoint'siz, HTTP'ye bağlanması ayrı bir task'a (Saga #285'in
devamı) bırakıldı. Sadece `OperationType.MOVE` destekleniyor (bu epic'in
kapsamı taşımadır); başka bir operationType görürse hiçbir dosyaya
dokunmadan reddediyor.

**Tasarım boşluğu belgelendi: `PlanStep` hangi dosyanın kendisine ait
olduğunu taşımıyor.** Sadece `affectedFileCount` var — `_distribute_files_to_steps`
`pdf_files`'ı `order`a göre sıralanmış step'lere SIRAYLA dağıtıyor. Bu
KIRILGAN bir varsayım (LLM'in `pdf_files` sırasını koruduğunu varsayar),
docstring'de açıkça işaretlendi; toplam sayı eşleşmezse tüm plan
reddediliyor. Asıl düzeltme (`PlanStep`e açık dosya listesi eklemek, LLM
plan üretimini de değiştirmek) ayrı bir task.

**Kendi testim gerçek bir bug yakaladı: rollback'te "pending" kalan
kayıt.** İlk rollback implementasyonu sadece `status == "completed"`
olan `FileOperation`'ları `"rolled_back"`'e çeviriyordu — ama `shutil.move`
başarısız olan SON adımın kaydı hiç `"completed"` olamadan (kayıt
oluşturulmuş, `session.commit()` henüz çağrılmamış) exception'a
düşüyordu, bu yüzden o kayıt sonsuza dek `"pending"` asılı kalıyordu.
`test_apply_plan_marks_transaction_and_operations_rolled_back_on_failure`
bunu hemen yakaladı; düzeltme: hem `"completed"` hem `"pending"` durumları
`"rolled_back"`'e çevriliyor.

**Red-team: 1 bulgu hemen düzeltildi (ters taşımanın kendisi başarısız
olabilir), 2 bulgu Saga #286'ya bağlandı.** Rollback sırasında
`shutil.move(destination, original_source)`'un KENDİSİ başarısız olursa
(ör. `original_source` bu sırada başka bir işlem tarafından dolduruldu)
eski kod bunu yakalamıyordu — orijinal exception maskeleniyor VE
`transaction.status="rolled_back"` hiç yazılmıyordu. Düzeltme: ters
taşıma artık kendi `try/except`'i içinde, başarısızsa operasyon
`"rollback_failed"` (yanlışlıkla `"rolled_back"` DEĞİL — dosya fiziksel
olarak hâlâ hedefte) olarak işaretleniyor, orijinal exception hep
fırlatılıyor. Diğer iki bulgu (shutil.move↔DB commit arasında crash
tutarsızlığı; `PlanStep`'in hangi dosyanın kendisine ait olduğunu
taşımaması) mimari — Saga #276 (rollback/undo) implementasyonuna
başlamadan önce netleştirilmesi gereken Saga #286'ya bağlandı. 84/84 test
yeşil.

## planı-onaysız-calistirma-koruması (Saga #273, epic #25)

**Gerçek bug: `ChatScreen` `PlanCard`'a `onApprove` hiç geçirmiyordu.**
Epic 24'ün önceki task'ları (Saga #265/#266) `PlanCard` içinde fail-closed
onay mantığını (`canApprove = isApproved && !hasApproved && !stale &&
!isGeneratingPlan`) zaten eksiksiz kurmuştu, ama `ChatScreen.tsx`'teki
`&lt;PlanCard /&gt;` render'ı `onApprove` prop'unu hiç bağlamıyordu — yani
buton görsel olarak vardı ama tıklanınca hiçbir şey dışarı bildirilmiyordu.
`ChatScreen`'e `onApprovePlan?: (messageId: string) => void` prop'u eklendi,
`PlanCard`'a `onApprove={() => onApprovePlan?.(message.id)}` olarak
bağlandı. "Reddetme/plan değişikliği kuyruğu temizler" gereksinimi zaten
mevcut mekanizmalarla (rejected → `isApproved` hep false, plan değişince
→ `stale` → `canApprove` false) karşılanıyordu, yeni bir kuyruk icat
edilmedi.

**Bilinçli kapsam kararı: `App.tsx`'i gerçek `/api/plan`'a bağlamadım.**
Bunun için gereken `pdfFiles` (gerçek PDF listesi + oluşturulma tarihleri)
kaynağı projede hiçbir yerde yok — ne backend'de bir klasör-tarama
endpoint'i, ne frontend'de bir native dosya-listeleme mekanizması
(`@tauri-apps/plugin-fs` kurulu değil). Bunu bu task'a sıkıştırmak ya
sahte/boş bir `pdfFiles: []` göndermek (anlamsız, yanıltıcı) ya da yeni
bir native bağımlılık eklemek (mimari karar, "dar kapsamı seç" ilkesiyle
çelişir) anlamına gelirdi. Bunun yerine Saga #285 açıldı (backend'in
`selectedFolder`'ı kendi taraması mı, yoksa frontend'in native fs
kullanması mı — karar gerektiriyor).

**Red-team bulgusu: "onaydan önce Orchestrator çağrılmaz" garantisi bugün
İTİBARİYLE HENÜZ PRODUCTION'DA GERÇEK DEĞİL, netleştirildi.** Düzeltilen
şey `ChatScreen`→`PlanCard` sınırındaki kopuk callback zinciri — bu
gerçek ve test edilmiş bir düzeltme. AMA `App.tsx` hâlâ `ChatScreen`'i
hiçbir prop olmadan render ediyor — `onApprovePlan` şu an hiçbir yerden
bağlanmıyor, çünkü zaten çağıracağı bir Orchestrator/network entegrasyonu
da yok (Saga #274 hâlâ todo, Saga #285 önkoşulu bekliyor). Yani bu task
GEREKLİ ama TEK BAŞINA YETERLİ değil — "onaysız çalıştırma engellendi"
iddiası ancak #285 (PDF keşfi) + App.tsx wiring + #274 (Orchestrator)
tamamlanınca gerçek bir güvenlik garantisi haline gelir. 103/103 frontend
test yeşil (3 yeni test: onaylanmış planda callback çağrılıyor, reddedilmiş planda asla
çağrılmıyor, `onApprovePlan` verilmediğinde çökme yok).

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

## pdf-ocr (Saga #306, epic #29)

**Kapsam kararı — sadece çekirdek OCR fonksiyonu, orchestrator entegrasyonu
yok.** Saga #299 kararıyla ayrı bir epic olmaktan çıkarılıp Format Agent
Sistemi'nin PDF alt-özelliği olarak buraya taşınan görev, bilinçli olarak
dar tutuldu: `backend/pdf_ocr.py` `pdf_discovery.py` paternini takip eden
bağımsız bir modül — `OperationType.OCR` olarak `models.py`/`orchestrator.py`/
`plan_generation.py`'ye TAM entegrasyon bu görevde YAPILMADI.

**Tesseract/Poppler sistem bağımlılığı riski.** `pytesseract` ve `pdf2image`
sadece Python wrapper'ları; gerçek çalışma zamanında sistemde Tesseract
binary'si (+ `tur.traineddata`) ve Poppler (`pdftoppm`) kurulu olmalı, bu
ortamda kurulu olduğu doğrulanmadı. Mitigasyon: OCR motor çağrısı
(`_run_ocr_engine`) ve PDF→görüntü dönüşümü (`_pdf_to_images`) ayrı,
izole fonksiyonlara çıkarıldı; TÜM testler bunları mock'ladı — test suite'i
YEŞİL olmak için gerçek Tesseract/Poppler kurulumu GEREKMİYOR. Prod
dağıtımı için kurulum ayrı bir packaging adımı (proje zaten .exe
paketleme gündeminde).

**Red-team bulgusu — path validation eksik, kapsam dışı bırakıldı.**
`ocr_pdf_file`, diğer operasyonların (MERGE/SPLIT/COPY/DELETE) kullandığı
`allowed_root`/`is_path_allowed` whitelist kontrolünden geçmiyor. Şu an
hiçbir HTTP endpoint'ine bağlı olmadığı için istismar edilemez; ileride
orchestrator'a entegre edilirken zorunlu kılınmalı — takip görevi
Saga #307 olarak açıldı (`depends_on: [306]`).

Codex/Copilot kotası dolu olduğu için test (red) ve implementasyon (green)
adımları ayrı genel-amaçlı subagent'lara delegasyon disipliniyle yazdırıldı,
ana akış sonucu bağımsız olarak kendi pytest çalıştırmasıyla doğruladı.

6 yeni test, 6/6 yeşil (`backend/tests/test_pdf_ocr.py`).
