---
task_slug: security-whitelist-generalization
jira_id: null
saga_task_id: 338
priority: low
coverage_target: 100
performance_target: null
memory_target: null
test_strategy:
  unit: 100
  integration: 0
  e2e: 0
affected_modules:
  - backend/security.py
  - backend/tests/test_security.py
threat_model: done
---

# ATDD — security-whitelist-generalization

## Jira Kaynağı
Jira'ya bağlı değil — yerel görev (Saga #338, epic #29 altında).

## Persona
Bu deponun geliştiricileri ve bağımsız red-team incelemesi yapan kişi/subagent
— yeni bir Plan operasyonu eklerken whitelist kontrolünü unutma riskini
taşıyan kişi.

## Hedef (Neden)
`backend/security.py`'deki `validate_plan_paths`, sadece 4 operasyonun
(MERGE/REDACT/EXCEL_SORT/EXCEL_CREATE) hedef dosya adını `_validate_single_path`
(allowed_root dışına çıkma/sistem-korumalı klasör/azami derinlik) ile
kontrol ediyor. 7 operasyon (EXCEL_FILTER/PDF_EXTRACT_PAGES/PDF_DELETE_PAGES/
PDF_COMPRESS/ZIP_CREATE/ZIP_ADD/ZIP_MERGE) sadece Pydantic'in ayraç-engelleme
validator'ına güveniyor, mimari-seviyesi whitelist kontrolünden geçmiyor
(Saga #326 ve #328 red-team bulguları). Ayrıca aynı 4 operasyonun ayrı bir
"zincirleme hedef çakışması" (planın bilmediği var olan bir dosyayla
çakışma + plan-içi çoklu-step aynı hedefi üretme) koruması var, yeni 7
operasyonda o da yok. Bu görev her iki korumayı da TEK, OperationType→
alan-adı eşlemesi kullanan genelleştirilmiş fonksiyonlara çıkararak, yeni
bir operasyon eklendiğinde bu korumaların unutulmasını yapısal olarak
imkânsız hale getiriyor.

## User Story
As a bu depoda yeni Plan operasyonu ekleyen/inceleyen geliştirici
I want tüm hedef-dosya-adı üreten operasyonların whitelist + çakışma
kontrolünden TEK bir merkezi mekanizmayla geçmesini
So that yeni bir operasyon eklendiğinde bu korumanın unutulması yapısal
olarak imkânsız olsun, red-team her seferinde ayrı ayrı kontrol etmek
zorunda kalmasın

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. [Critical] Given `security.py` içinde `OperationType` → hedef-alan-adı
   eşlemesi yapan tek bir sözlük/liste (11 operasyon: MERGE, REDACT,
   EXCEL_SORT, EXCEL_CREATE, EXCEL_FILTER, PDF_EXTRACT_PAGES,
   PDF_DELETE_PAGES, PDF_COMPRESS, ZIP_CREATE, ZIP_ADD, ZIP_MERGE), When
   `validate_plan_paths` çalışır, Then her step için ilgili operasyonun
   hedef alanı (varsa) `_validate_single_path` ile kontrol edilir — 11
   operasyonun HİÇBİRİ için ayrı bir `if step.operationType == X:` bloğu
   kalmaz.
2. [Critical] Given aynı 11 operasyon için TEK bir genelleştirilmiş
   "zincirleme hedef çakışması" fonksiyonu (mevcut 4 ayrı
   `validate_*_destinations` fonksiyonunun yerini alır), When bir plan
   birden fazla step'te aynı hedef dosya adını üretir VEYA planın bilmediği
   zaten var olan bir dosyayla çakışır, Then plan tamamen reddedilir
   (`PathWhitelistError`), tek bir merkezi fonksiyondan.
3. [Critical] [AC-S1] Given yeni 7 operasyonun her biri için, When hedef
   dosya adı `allowed_root` dışına çıkacak/sistem-korumalı bir klasöre
   değecek/azami derinliği aşacak şekilde ayarlanır (saldırganın somut
   girdisi: ör. targetFolder'ı `../../` seviyesine taşıyan bir değer,
   Pydantic'in ayraç-engelleme validator'ını atlatmayan ama `allowed_root`
   dışına resolve olan bir kombinasyon), Then `PathWhitelistError` fırlatılır
   ve HİÇBİR dosya işlemi başlamaz (önceden sessizce geçiyordu — bu tam
   olarak Saga #326/#328 red-team'in bulduğu açığın kapatılmasıdır).
4. [High] [AC-S2] Given yeni 7 operasyonun her biri için, When hedef dosya
   adı planın bilmediği, `allowed_root`'ta zaten var olan bir dosyayla
   çakışır (saldırganın/kullanıcının somut girdisi: hedef alan adı
   kullanıcının önemli, plana dahil olmayan bir dosyasıyla aynı), Then
   `PathWhitelistError` fırlatılır — kullanıcı verisi sessizce üzerine
   yazılmaz.
5. [Critical] Given mevcut 4 operasyonun (MERGE/REDACT/EXCEL_SORT/
   EXCEL_CREATE) tüm var olan testleri, When genelleştirilmiş fonksiyonlara
   geçildikten sonra çalıştırılır, Then hiçbir regresyon olmadan hepsi
   PASS kalır (davranış birebir korunur).
6. [Medium] Given ZIP_EXTRACT operasyonu, When `validate_plan_paths`/yeni
   genelleştirilmiş fonksiyonlar çalışır, Then ZIP_EXTRACT'e dokunulmaz —
   kendi `extract_zip` fonksiyonu içinde zaten ayrı ve sağlam bir
   `_validate_single_path` çağrısı var, bu görev onu değiştirmez.

## Davranış Sözleşmesi (hangi durumda ne döner)
| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path: 11 operasyonun herhangi biri, hedef alanı allowed_root içinde, çakışma yok | Fonksiyon `None` döner (exception yok) | Yok — sadece doğrulama | Plan `apply_plan`'a geçer, normal akış devam eder | AC-1, AC-2 |
| 2 | Girdi geçersiz: hedef alan `allowed_root` dışına çıkıyor | `PathWhitelistError` fırlatılır (`reason="izin verilen kök dışında"`) | Yok — plan hiç uygulanmaz | Mevcut `PathWhitelistError` işleme zincirine göre (backend/main.py) yapılandırılmış hata | AC-3 |
| 3 | Kaynak yok: hedef alan `None`/boş (operasyon o alanı gerektirmiyor) | Genelleştirilmiş fonksiyon o alanı atlar (kontrol edilmez) | Yok | Etkilenmez — Pydantic zaten bu alanın SADECE ilgili operationType için zorunlu olduğunu garanti ediyor | AC-1 |
| 4 | Yetkisiz erişim | Uygulanmıyor — bu fonksiyon kullanıcı/rol yetkilendirmesi yapmıyor, sadece dosya yolu whitelist'i. Silinme nedeni: proje tek-kullanıcılı masaüstü uygulaması, rol tabanlı yetkilendirme kapsam dışı. | — | — | — |
| 5 | Dış bağımlılık hatası (ağ/DB/API) | Uygulanmıyor — bu fonksiyon salt yerel dosya sistemi path çözümlemesi yapıyor, ağ/DB/API çağrısı yok. Silinme nedeni: fonksiyonun doğası gereği dış bağımlılığı yok. | — | — | — |
| 6 | Zaman aşımı | Uygulanmıyor — senkron, salt CPU/dosya-sistemi işlemi (path.resolve()), ağ beklemesi yok. Silinme nedeni: zaman aşımı kavramı bu fonksiyona uygulanmıyor. | — | — | — |
| 7 | **Kısmi başarı**: plandaki 11 operasyon step'inden biri whitelist ihlali yapıyor, diğerleri geçerli | `PathWhitelistError` fırlatılır — TÜM plan reddedilir, geçerli step'ler de dahil hiçbiri kısmen kabul edilmez | Yok — hiçbir dosya işlemi başlamaz (bu kontrol `apply_plan`'dan ÖNCE çalışır) | Kullanıcı tüm planın reddedildiğini görür, hangi step/alan sorununa yol açtığını `offending_path`/`reason` alanlarından görür | AC-3, AC-4 |
| 8 | **Hiçbir şey yapılamadı ama hata da yok** | Bu durum tanımsız/olanaksız: fonksiyon ya `None` döner (tüm kontroller geçti) ya `PathWhitelistError` fırlatır — sessiz "başarı" görünümü üretecek bir dal yok (mevcut `_validate_single_path` deseni zaten böyle, genelleştirme bunu bozmaz) | — | — | — |

Kısmi başarı: 7. satırda tanımlı — mevcut `validate_plan_paths` davranışıyla
birebir aynı (tek bir ihlal tüm planı reddeder), genelleştirme bu ilkeyi
değiştirmez.
Hiçbir şey yapılamadı ama hata da yok: Olanaksız — fonksiyon senkron ve
exception-şeffaf, `_validate_single_path` zaten ya `None` döner ya
`PathWhitelistError` fırlatır, üçüncü bir sessiz dal yok (AC-1/AC-2 ile
garanti altına alınır, kod incelemesinde kontrol edilir).
Boş sonuç ↔ hata ayrımı: Uygulanmıyor — bu fonksiyon bir sorgu/liste
döndürmüyor, sadece doğrulama yapıp geçer veya reddeder; "boş sonuç"
kavramı yok.

## Test Strategy
Unit: 100% — `backend/tests/test_security.py`'ye (veya `validate_plan_paths`
zaten test ediliyorsa mevcut dosyaya) yeni 7 operasyonun her biri için en
az 2 test eklenir: (1) whitelist-ihlali reddi, (2) çakışma reddi. Mevcut
4 operasyonun testleri regresyon kontrolü için değişmeden çalıştırılır.
Integration/E2E: 0% — bu saf bir güvenlik-katmanı birim testi refactor'ü,
API/e2e senaryosu gerektirmez.

## Benchmark / Başarı Ölçütü
Coverage Target: backend/security.py için %100 branch coverage (güvenlik-
kritik dosya, kullanıcı onayı: her yeni dict-girdisi ve çakışma dalı en
az bir testle kaplı olmalı).
Diğer ölçülebilir kriterler:
- `pytest backend/tests/test_security.py` (ve `test_orchestrator.py` gibi
  `validate_plan_paths`'e bağımlı diğer test dosyaları) tüm testler PASS.
- 11 operasyonun HİÇBİRİ için ayrı bir `if step.operationType == X:` bloğu
  kalmaz — `validate_plan_paths` içinde tek bir döngü/sözlük araması olur.

## Kapsam Dışı
- ZIP_EXTRACT — kendi `extract_zip` fonksiyonu içinde zaten ayrı ve sağlam
  bir `_validate_single_path` çağrısı var, bu görev ona dokunmaz.
- "Yeni çıktı dosya adı" üretmeyen operasyonlar (MOVE, COPY, DELETE,
  RENAME'in kaynak tarafı, EXCEL_APPEND, WORD_APPEND_TABLE, OCR, PDF_SPLIT) —
  bunlar zaten `targetFolder`/kaynak dosya kontrolünden geçiyor, ayrıca bir
  "hedef dosya adı" alanları yok, bu görevin kapsamına girmiyorlar.
  (Saga #338 follow-up: IMAGE_CROP, IMAGE_THUMBNAIL kapsama dahil edildi —
  red-team bulgusu sonrası, bu iki operasyonun da hedef dosya adı ürettiği
  tespit edildi.)
- `_validate_single_path`'in kendi mantığı (allowed-root/sistem-korumalı/
  derinlik kontrolleri) değişmiyor — sadece HANGİ alanların bu fonksiyona
  gönderildiği genelleştiriliyor.
- Yeni bir güvenlik açığı sınıfı taranmıyor — bu görev SADECE bilinen
  (#326/#328 red-team'de bulunan) whitelist/çakışma boşluğunu kapatıyor.

## Etkilenen Dosyalar/Modüller (bilinen)
- backend/security.py (`validate_plan_paths` + `validate_rename_destinations`/
  `validate_merge_destinations`/`validate_redact_destinations`/
  `validate_excel_sort_destinations`'ın TEK bir genelleştirilmiş fonksiyona
  birleştirilmesi)
- backend/tests/test_security.py (yeni testler)

## Rollback Beklentisi
Uygulanmıyor — production davranışı sadece GENİŞLİYOR (önceden sessizce
geçen 7 operasyon artık reddediliyor), mevcut kabul edilen senaryolar
değişmiyor. Runtime rollback mekanizması gerektirmez; suite kırılırsa
standart `git revert` ile geri alınır.

## Threat Model (STRIDE-lite)
Varlık: kullanıcının `allowed_root` altındaki dosyaları (PDF/Word/Excel/
Image/Zip). Güven sınırı: Plan JSON'daki (LLM/kullanıcı tarafından
üretilen) hedef dosya adı alanları → dosya sistemi yazma işlemi.

- **Tampering** (asıl tehdit) — Plan'daki hedef alan değerlerine (client/LLM
  tarafından üretilen) güveniliyor; 7 operasyon için whitelist kontrolü
  yoktu → AC-S1/AC-S2 ile kapatıldı.
- **Elevation** — Bu görevde ayrı bir yetki sınırı yok (tek kullanıcılı
  masaüstü uygulaması); "elevation" burada dosya sistemi sınırının
  (`allowed_root` dışına çıkma) aşılması anlamına geliyor, bu da Tampering
  ile aynı AC'lerce (AC-S1) kapatılıyor.
- **Spoofing** — Uygulanmıyor, kimlik doğrulama/oturum bu görevin
  kapsamında değil (tek kullanıcılı masaüstü aracı, kabul edilen risk).
- **Repudiation** — Uygulanmıyor, çok kullanıcılı/denetim izi gereksinimi
  yok (kabul edilen risk, tek kullanıcılı yerel araç).
- **Information disclosure** — `PathWhitelistError` zaten yapılandırılmış
  alanlar (`offending_path`/`reason`) taşıyor, çağıran (`backend/main.py`)
  ne kadarının istemciye açılacağına ayrıca karar veriyor (mevcut tasarım,
  bu görev değiştirmiyor) — yeni bir AC gerekmiyor.
- **Denial of Service** — Uygulanmıyor, rate limit/sınırsız-yükleme bu
  görevin kapsamında değil (kabul edilen risk, tek kullanıcılı yerel araç,
  ağ maruziyeti yok).

## Risks
- Genelleştirilmiş çakışma fonksiyonu, mevcut 4 fonksiyonun BİRBİRİNDEN
  FARKLI `all_destinations` listelerini (her biri bir öncekinin üstüne
  ekleniyordu: rename → rename+merge → +redact → +excel_sort) TEK bir
  listede birleştirirken küçük bir davranış farkı oluşabilir — plan
  adımı sırasının önemi olmadığını doğrulayan mevcut testler bunu
  yakalamalı, ama dikkatli refactor gerektirir.
- Kapsam plan aşamasında genişletildi (whitelist + çakışma, sadece
  whitelist değil) — bu, ilk red-team bulgusunun (Saga #326/#328)
  önerdiğinden daha büyük bir değişiklik; `code-copilot`/`test-copilot`
  bunu tek seferde doğru kapsamda tutmalı.

## Assumptions
- Genelleştirilmiş whitelist dict'i `backend/security.py` içinde
  tanımlanacak (kullanıcı onayı bu konuda net değildi, `models.py`
  alternatifi de mevcuttu — red-team bulgusunda security.py önerilmişti,
  bu varsayılan olarak kullanılıyor).

## Unknowns
- Genelleştirilmiş fonksiyonların kesin imzaları/isimleri (implementasyon
  sırasında `plan` skill'i tarafından netleştirilecek).

## Sorular ve Cevaplar (ham kayıt)
1. Zincirleme çakışma kontrolü de 7 yeni operasyona genişletilsin mi? →
   Evet, genişletilsin.
2. Çakışma kontrolü tek genel fonksiyona mı çıkarılsın, yoksa 7 ayrı
   fonksiyon mu eklensin? → Tek genel fonksiyon.
3. Dict-driven whitelist döngüsü mevcut 4 operasyonu da mı kapsasın? →
   Evet, mevcut 4'ü de dict'e taşı.
4. Test stratejisi? → Her 7 operasyon için whitelist-ihlali reddi +
   çakışma reddi testi (en az 2 test/operasyon).
5. Coverage hedefi? → backend/security.py için %100 branch.
6. Kapsam dışı (ZIP_EXTRACT + "yeni dosya adı üretmeyen" operasyonlar)? →
   Onaylandı (tek seçenek olarak sunuldu, kullanıcı akışı onayladı).
7. Persona/Hedef/Bağımlılıklar/Öncelik → Saga #338 görev açıklamasından
   ve kod incelemesinden (kullanıcı mesajından, tekrar sorulmadı).
