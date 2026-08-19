---
task_slug: excel-create-read-append
jira_id: null
saga_task_id: 326
priority: medium
coverage_target: 85
performance_target: null
memory_target: null
test_strategy:
  unit: 75
  integration: 20
  e2e: 5
affected_modules:
  - backend/models.py
  - backend/orchestrator.py
  - backend/main.py
---

# ATDD — excel-create-read-append

## Jira Kaynağı
Jira'ya bağlı değil — yerel görev. Kaynak: Saga #326 (epic #29 "Format Agent
Sistemi").

## Persona
windows-ai-files kullanıcısı (muhasebeci tipi) — sıfırdan bir Excel tablosu
oluşturmak, mevcut bir tabloyu (isteğe bağlı bir hücre aralığıyla) okumak,
veya mevcut bir tabloya yeni satırlar eklemek isteyen kişi.

## Hedef (Neden)
Eski projede (`core/agents/excel_agent.py`) üç ayrı sessiz-hata sınıfı vardı:
1. `_read`: şema `"range"` alanı ("A1:C10") ilan ediyordu ama kod bunu hiç
   OKUMUYORDU — kullanıcı bir aralık istese bile TÜM sayfa döndürülüyordu.
2. `_create`: LLM `"rows"` için düz `[1,2,3]` üretebiliyordu (`[[1,2,3]]`
   yerine) — kod bunu doğrudan satır listesi sanıp çökebiliyordu.
3. `_append_rows`: kaynak dosya yoksa/bozuksa sessizce SIFIRDAN yeni
   (yanlış/boş) bir dosya oluşturuluyordu — kullanıcı "ekleme" yaptığını
   sanırken aslında önceki içerik kayboluyordu.

Bu görüşmede kapsam netleştirildi: üç operasyon TEK bir ATDD'de ele
alınıyor ama MİMARİ OLARAK üçe ayrılıyor — CREATE ve APPEND birer Plan
operasyonu (`OperationType`), READ ise dosya sistemini hiç değiştirmeyen
senkron bir sorgu endpoint'i (plan/transaction/rollback kavramı yok,
`backend/file_search.py`'nin senkron sorgu deseniyle aynı kategori).

## User Story
As a windows-ai-files kullanıcısı
I want sıfırdan bir Excel dosyası oluşturabilmek, mevcut bir dosyayı (isteğe bağlı bir hücre aralığıyla) okuyabilmek, veya mevcut bir dosyaya yeni satırlar ekleyebilmek
So that "range" parametresi sessizce yoksayılmasın, düz sayı listesi göndermem çökmeye yol açmasın, ve bozuk/eksik bir dosyaya "ekleme" yapmaya çalıştığımda içeriğim sessizce kaybolmasın

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. [Critical] Given `rows=[["Ad","Puan"],["Ali",90]]` ve `createdFileName="yeni.xlsx"` (allowed_root'ta henüz yok), When EXCEL_CREATE çalıştırılır, Then `yeni.xlsx` tam olarak verilen satırlarla oluşturulur.
2. [Critical] Given `createdFileName` allowed_root'ta ZATEN VAR, When EXCEL_CREATE çalıştırılır, Then `PlanApplicationError`, mevcut dosyaya DOKUNULMAZ (üzerine yazılmaz).
3. [High] Given `rows=[1,2,3]` (düz liste, iç içe değil), When EXCEL_CREATE çalıştırılır, Then her eleman tek hücreli bir satır olarak sarılır (`[[1],[2],[3]]`), çökme YOK.
4. [Critical] Given bir `.xlsx` dosyası ve `range="A1:C10"`, When `/api/excel/read` çağrılır, Then SADECE o hücre aralığındaki değerler döner (tüm sayfa değil).
5. [High] Given `range` VERİLMEMİŞ, When `/api/excel/read` çağrılır, Then tüm kullanılan sayfa alanı (`ws.dimensions`) döner.
6. [Critical] Given var olan bir `.xlsx` dosyası ve `rows=[["Veli",80]]`, When EXCEL_APPEND çalıştırılır, Then satırlar dosyanın SONUNA eklenir, önceki içerik korunur (kaynak YERİNDE güncellenir, PDF APPEND ile aynı desen).
7. [Critical] Given kaynak dosya YOK veya BOZUK (openpyxl açamıyor), When EXCEL_APPEND çalıştırılır, Then `PlanApplicationError`, HİÇBİR yeni/boş dosya oluşturulmaz, kaynak (varsa) değişmez.

## Davranış Sözleşmesi (hangi durumda ne döner)
| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | EXCEL_CREATE happy path | `operation.status="completed"` | `createdFileName`'e yeni dosya yazılır | Sonuç kartında yeni dosya | AC-1 |
| 2 | EXCEL_CREATE hedef zaten var | `PlanApplicationError("EXCEL_CREATE çıktı dosyası zaten var: '...'")` | Hiçbir dosya yazılmaz/değişmez | Hata mesajı | AC-2 |
| 3 | EXCEL_CREATE düz satır listesi | Normal başarı (sarılmış haliyle) | `createdFileName`'e yazılır | Sonuç kartı, satırlar tek-hücreli görünür | AC-3 |
| 4 | EXCEL_READ happy path (range ile/sız) | `200 + {values: [[...]], range: "A1:C10" veya null}` | Yok (salt okunur) | Tablo verisi | AC-4, AC-5 |
| 5 | EXCEL_READ kaynak yok/bozuk/geçersiz range | `404`/`422` (uygun HTTP kodu, `SearchResponse`-benzeri hata deseni) | Yok | Hata mesajı | — (girdi doğrulama, ayrı AC gerekmiyor) |
| 6 | EXCEL_APPEND happy path | `operation.status="completed"` | Kaynak dosya YERİNDE güncellenir (PDF APPEND'in `_append_backup_path` deseniyle AYNI gizli yedek) | Sonuç kartı, dosya güncellendi | AC-6 |
| 7 | EXCEL_APPEND kaynak yok/bozuk | `PlanApplicationError("EXCEL_APPEND kaynağı okunamıyor: '...'")` | HİÇBİR dosya oluşturulmaz/değişmez | Hata mesajı | AC-7 |
| 8 | **Kısmi başarı** (bir kısmı oldu, kalanı olmadı) | Uygulanmaz — CREATE/APPEND'in ikisi de tek dosya/tek atomik yazma operasyonu (tempfile+atomik-replace deseni), ara durum fiziksel olarak oluşamaz | — | — | — |
| 9 | **Hiçbir şey yapılamadı ama hata da yok** | Uygulanmaz — CREATE/APPEND'in her ikisi de ya dosyayı değiştirir (satır sayısı>=1 zorunlu, boş `rows` reddedilir) ya da hata fırlatır; "sessiz no-op" durumu şema seviyesinde (rows boş olamaz validator'ı) engellenir | — | — | — |

Kısmi başarı ve "hiçbir şey yapılamadı ama hata yok" satırları silindi: CREATE
tek atomik yazma, APPEND PDF APPEND'in AYNI atomik-yerinde-güncelleme
deseni (`_forward_append`/`_rollback_append` ile paralel), READ tamamen
salt-okunur — üçünde de ara/sessiz durum mimari olarak oluşamaz.

Boş sonuç ↔ hata ayrımı: EXCEL_READ'de boş bir sayfa (`values: []`) ile
dosya bulunamaması/bozuk olması FARKLI durumlardır — biri `200 + boş dizi`,
diğeri `404`/`422` + hata mesajı. Aynı yanıt şekline indirgenmez.

## Test Strategy
Unit: 75% — satır normalizasyonu (`rows` sarma), range parse, CREATE/APPEND
çekirdek fonksiyonları (happy path + hata yolları).
Integration: 20% — orchestrator CREATE/APPEND step uygulaması, `/api/excel/read`
endpoint entegrasyon testleri, rollback.
E2E: 5% — plan oluştur → uygula → sonuç dosyasını oku uçtan uca (CREATE/APPEND
için); READ için doğrudan endpoint çağrısı.

## Benchmark / Başarı Ölçütü
Coverage Target: 85%
Performance Target: yok
Memory: yok
Diğer ölçülebilir kriterler: pytest tüm testler yeşil.

## Kapsam Dışı
- `plan_generation.py`/LLM prompt güncellemesi (doğal dilden CREATE/APPEND
  isteği çıkarma, EXCEL_READ için doğal dil sorgusu) — ayrı bir Saga
  task'a bırakıldı (önceki görevlerle tutarlı karar).
- EXCEL_READ için sayfa (sheet) seçimi — sadece aktif sayfa (`workbook.active`)
  okunur, çok sayfalı dosyalarda sayfa adı parametresi bu ATDD'de YOK.
- EXCEL_CREATE'te formül/biçimlendirme desteği — sadece ham değerler
  (`ws.append(row)`), hücre biçimlendirmesi/formül YOK.
- EXCEL_APPEND'de `rows`'un mevcut sütun başlıklarıyla eşleştirilmesi —
  satırlar KÖR olarak sona eklenir, başlık-sütun hizalaması kontrol
  EDİLMEZ (kullanıcı sorumluluğunda).

## Etkilenen Dosyalar/Modüller (bilinen)
- `backend/models.py` — `OperationType.EXCEL_CREATE`/`EXCEL_APPEND` (READ
  OperationType DEĞİL); `PlanStep`e `rows: list | None`,
  `createdFileName: str | None` (CREATE), `appendRows: list | None`
  (APPEND, `rows` ile aynı normalizasyon ama ayrı alan — CREATE/APPEND
  aynı anda kullanılamayacağı için isim çakışması netleştirilmeli, plan
  adımında kesinleşecek); CREATE için `fileNames` boş olma zorunluluğu
  (kaynaksız operasyon — mevcut MERGE'in ">=2" / SPLIT'in "==1"
  desenlerinin YENİ bir "==0" varyantı).
- Yeni bir modül gerekebilir (`backend/excel_create.py`/`excel_append.py`
  veya `excel_sort.py`'ye eklenen fonksiyonlar) — plan adımında
  kesinleştirilecek.
- `backend/orchestrator.py` — `_SUPPORTED_OPERATION_TYPES`,
  `_ROLLBACK_OPERATIONS` (APPEND için `_rollback_append`'in AYNI deseni,
  muhtemelen paylaşılan/paralel bir `_excel_append_backup_path`), hedef-
  klasör-oluşturma hariç-tutma listesi, iki yeni step-uygulama bloğu.
- `backend/main.py` — YENİ bir endpoint (`POST /api/excel/read` veya
  benzeri) — `SearchRequest`/`SearchResponse` deseniyle tutarlı bir
  istek/yanıt şeması.

## Rollback Beklentisi
EXCEL_CREATE: SPLIT/EXCEL_FILTER ile aynı `_rollback_copy` deseni (kaynak
yok, rollback sadece çıktıyı siler).
EXCEL_APPEND: PDF APPEND'in `_rollback_append`/`_append_backup_path`
deseniyle AYNI (yerinde güncelleme, ayrı gizli yedek klasöründen geri
kopyalama).
EXCEL_READ: rollback kavramı YOK (dosya sistemi hiç değişmiyor).

## Risks
- `PlanStep.fileNames`'in her operationType için "kaç kaynak dosya"
  anlamına geldiği şeması (MERGE>=2, SPLIT/OCR/APPEND/EXCEL_SORT/
  EXCEL_FILTER/PDF_*==1) EXCEL_CREATE'in "==0" (kaynaksız) durumuyla İLK
  KEZ genişliyor — plan adımında bu validator'ın mevcut `affected_file_count_matches_file_names`
  ile çakışmadığından emin olunmalı (0==0 zaten matematiksel olarak
  tutarlı, ama açıkça test edilmeli).
- `rows`/`appendRows` alan isimlendirmesi (CREATE ve APPEND için aynı mı
  ayrı mı) plan adımında netleşecek — bu görüşmede kesinleşmedi.

## Assumptions
- EXCEL_READ, `SessionContext`/`selectedFolder` bağlamı üzerinden çalışır
  (diğer tüm endpoint'lerle aynı allowed_root/whitelist doğrulaması) —
  kullanıcı onaylamadı ama proje genelinde TEK bir erişim-kontrol modeli
  olduğu için varsayım riski düşük.
- `range` formatı openpyxl'in kendi `ws[range_string]` sözdizimiyle
  ("A1:C10") birebir aynı — ayrı bir parser YAZILMAYACAK, openpyxl'in
  kendi hata mesajı (geçersiz range) yakalanıp 422'ye çevrilecek.

## Unknowns
- `rows` (CREATE) / `appendRows` (APPEND) alan isimlendirmesi — plan
  adımında modele bakılarak kesinleştirilmeli.
- EXCEL_CREATE'in `fileNames=[]` deseninin mevcut Pydantic validator'larla
  (özellikle `affected_file_count_matches_file_names`) gerçekten çakışmadan
  çalıştığı plan/code-copilot adımında test edilerek doğrulanmalı.

## Sorular ve Cevaplar (ham kayıt)
1. Kapsam (üçü birden mi)? → Evet, üçü birden bu ATDD'de.
2. Slug onayı → "excel-create-read-append" (onaylandı).
3. EXCEL_READ mimarisi? → Senkron sorgu endpoint'i (Plan operasyonu DEĞİL).
4. EXCEL_CREATE çakışma davranışı? → Reddet, açık hata.
5. EXCEL_APPEND çıktı modeli? → Yerinde güncelle (PDF APPEND deseni).
6. Range kapsamı sadece READ'de mi? → Evet (tek mantıklı seçenek, tekrar
   sorulmadı).
7. Kabul kriteri + coverage + test oranı? → Otomatik test, %85, 75/20/5.
8. Kapsam dışı (plan_generation.py)? → Hayır, sadece backend modül +
   orchestrator + models + READ endpoint'i.
9. Satır sarma normalizasyonu CREATE+APPEND'in ikisinde de mi? → Evet.
10. Persona/hedef → task açıklamasından türetildi.
