---
task_slug: zip-temel-operasyonlar
jira_id: null
saga_task_id: 328
priority: low
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

# ATDD — zip-temel-operasyonlar

## Jira Kaynağı
Jira'ya bağlı değil — yerel görev. Kaynak: Saga #328 (epic #29 "Format Agent
Sistemi").

## Persona
windows-ai-files kullanıcısı (muhasebeci tipi) — bir grup dosyayı (ör. bu
ayın faturaları) zip'leyip göndermek, bir zip'in içeriğine bakmak, bir
zip'e dosya eklemek, bir zip'i açmak, veya birden fazla zip'i birleştirmek
isteyen kişi.

## Hedef (Neden)
Eski projede (`core/agents/zip_agent.py`) EXTRACT operasyonunda somut bir
bug vardı: şema `"destination"` derken kod `"output_dir"` okuyordu —
kullanıcının istediği klasör YOK SAYILIP zip adından türetilen bir klasöre
çıkarılıyordu (sessiz yanlış-yer hatası). Bu görüşmede kapsam beşe
genişletildi: CREATE/ADD/EXTRACT/MERGE (Plan operasyonları) + OPEN (senkron
sorgu, EXCEL_READ'in deseni) — Python'ın `zipfile` stdlib'i kullanılacağı
için (LibreOffice/Ghostscript'in aksine) yeni bir dış bağımlılık YOK.

## User Story
As a windows-ai-files kullanıcısı
I want seçili dosyaları zip'leyebilmek, bir zip'in içeriğini görebilmek, bir zip'e dosya ekleyebilmek, bir zip'i (kullanıcının BELİRTTİĞİ klasöre) çıkarabilmek, ve birden fazla zip'i birleştirebilmek
So that "destination" parametrem sessizce yoksayılıp yanlış bir klasöre çıkarma yapılmasın, ve zip içindeki kötü niyetli bir dosya yolu (zip-slip) allowed_root dışına yazma yapamasın

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. [Critical] Given `fileNames=["a.pdf","b.xlsx"]` ve `zippedFileName="arsiv.zip"`, When ZIP_CREATE çalıştırılır, Then `arsiv.zip` tam olarak bu iki dosyayı içerir, kaynaklar değişmez.
2. [Critical] Given var olan bir `.zip` ve `destinationFolder="cikti"` (kullanıcının AÇIKÇA belirttiği klasör adı), When ZIP_EXTRACT çalıştırılır, Then içerik `allowed_root/cikti/` altına çıkarılır — zip ADINDAN türetilen bir klasöre DEĞİL (eski projenin bug'ı bu ATDD'de imkânsız kılınıyor).
3. [Critical] Given zip içinde bir giriş adı `"../../evil.txt"` (zip-slip girişimi), When ZIP_EXTRACT çalıştırılır, Then `PlanApplicationError`, HİÇBİR dosya çıkarılmaz (tüm-ya-da-hiç, kısmi çıkarma YOK).
4. [High] Given var olan bir `.zip` ve `filesToAdd=["c.docx"]`, When ZIP_ADD çalıştırılır, Then YENİ bir dosyaya (`addedFileName`) kaynak zip'in TÜM eski içeriği + yeni dosya yazılır, kaynak zip değişmez.
5. [High] Given `fileNames=["a.zip","b.zip"]` (en az 2 zip) ve `mergedZipFileName="birlesik.zip"`, When ZIP_MERGE çalıştırılır, Then YENİ zip TÜM kaynak zip'lerin TÜM girişlerini içerir, kaynaklar değişmez.
5b. [Medium] Given var olan bir `.zip`, When `/api/zip/list` çağrılır, Then zip içindeki girişlerin (ad, boyut, sıkıştırılmış boyut) listesi döner, dosya sistemi HİÇ değişmez.
6. [High] Given kaynak zip yok/bozuk (ZIP_EXTRACT/ZIP_ADD/ZIP_MERGE için), When operasyon çalıştırılır, Then `PlanApplicationError`, hiçbir dosya oluşturulmaz/değişmez.

## Davranış Sözleşmesi (hangi durumda ne döner)
| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | ZIP_CREATE happy path | `operation.status="completed"` | `zippedFileName`'e yeni zip yazılır | Sonuç kartı | AC-1 |
| 2 | ZIP_EXTRACT happy path | `operation.status="completed"` | `destinationFolder`'a (kullanıcının BELİRTTİĞİ) içerik çıkarılır | Sonuç kartı, doğru klasör | AC-2 |
| 3 | ZIP_EXTRACT zip-slip girişimi | `PlanApplicationError("ZIP_EXTRACT reddedildi, güvenli olmayan giriş yolu: '...'")` (AC-S1) | HİÇBİR dosya çıkarılmaz | Hata mesajı | AC-3 |
| 4 | ZIP_ADD happy path | `operation.status="completed"` | `addedFileName`'e yeni zip (eski içerik + yeni dosya) yazılır, kaynak zip değişmez | Sonuç kartı | AC-4 |
| 5 | ZIP_MERGE happy path | `operation.status="completed"` | `mergedZipFileName`'e birleşik zip yazılır, kaynaklar değişmez | Sonuç kartı | AC-5 |
| 6 | ZIP_OPEN (list) happy path | `200 + {entries: [{name, size, compressedSize}]}` | Yok (salt okunur) | Dosya listesi | AC-5b |
| 7 | Kaynak zip yok/bozuk | `PlanApplicationError("... kaynağı okunamıyor: '...'")` (Plan operasyonları için) / `404`/`422` (ZIP_OPEN için) | Hiçbir dosya değişmez | Hata mesajı | AC-6 |
| 8 | ZIP_EXTRACT hedef klasörde aynı isimli dosya varsa | Üzerine yazılır (zipfile.extractall'ın doğal davranışı), hata YOK | Var olan dosya değişir | Sonuç kartı, sessiz üzerine yazma bilinçli kabul edilen davranış | — (AC gerekmiyor, kullanıcı kararıyla netleşti) |
| 9 | **Kısmi başarı** (ZIP_EXTRACT bir kısmı çıkarıp kalanı çıkaramazsa) | Uygulanmaz — zip-slip kontrolü TÜM girişler ÖNCEDEN taranır, gerçek çıkarma İLK geçerli olmayan giriş bulunursa hiç BAŞLAMAZ (AC-3'ün "tüm-ya-da-hiç" garantisi) | — | — | AC-3 |
| 10 | **Hiçbir şey yapılamadı ama hata da yok** | Uygulanmaz — `fileNames`/`filesToAdd` boş olamaz (validator), her çağrı ya işlemi yapar ya hata fırlatır | — | — | — |

Kısmi başarı ve "hiçbir şey yapılamadı ama hata yok" satırları büyük ölçüde
silindi: CREATE/ADD/MERGE tek atomik yazma (tempfile+atomik-replace),
EXTRACT'in kısmi-çıkarma riski AC-3'ün ön-tarama garantisiyle kapatıldı.

Boş sonuç ↔ hata ayrımı: ZIP_OPEN'da boş bir zip (`entries: []`) ile
dosya bulunamaması/bozuk olması FARKLI durumlardır — biri `200 + boş
liste`, diğeri `404`/`422` + hata mesajı.

## Test Strategy
Unit: 75% — her operasyonun çekirdek fonksiyonu (happy path + hata
yolları), ÖZELLİKLE zip-slip tarama mantığı (AC-3, farklı kaçış
teknikleri: `../`, mutlak path, sembolik link taklidi).
Integration: 20% — orchestrator step uygulamaları, `/api/zip/list`
entegrasyon testleri, rollback.
E2E: 5% — plan oluştur → uygula → sonuç dosyasını oku uçtan uca.

## Benchmark / Başarı Ölçütü
Coverage Target: 85%
Performance Target: yok
Memory: yok
Diğer ölçülebilir kriterler: pytest tüm testler yeşil.

## Kapsam Dışı
- `plan_generation.py`/LLM prompt güncellemesi — ayrı bir Saga task'a
  bırakıldı.
- Klasör-rekursif zip'leme (ZIP_CREATE sadece VERİLEN dosya listesini
  zip'ler, allowed_root'un TAMAMINI rekursif taramaz).
- Şifreli/parola korumalı zip desteği.
- Zip içinde alt-klasör yapısı OLUŞTURMA (ZIP_CREATE tüm dosyaları zip'in
  KÖKÜNE, düz yapıda ekler — iç içe klasör hiyerarşisi yok).
- ZIP_ADD'de birden fazla dosya EKLEME desteği net değil — bu ATDD'de
  TEK bir dosya listesi (`filesToAdd`) kabul edilir, ama tekil/çoğul
  ayrımı code-copilot'ta netleştirilecek (bkz. Unknowns).

## Etkilenen Dosyalar/Modüller (bilinen)
- `backend/models.py` — `OperationType.ZIP_CREATE/ZIP_ADD/ZIP_EXTRACT/ZIP_MERGE`;
  `PlanStep`e `zippedFileName`, `destinationFolder` (EXTRACT — targetFolder'dan
  AYRI, çünkü targetFolder zaten YYYY-MM formatına kilitli, ZIP_EXTRACT'in
  hedefi rastgele bir isim olabilir — bkz. Risks), `filesToAdd`,
  `addedFileName`, `mergedZipFileName`; ilgili validator'lar.
- Yeni bir modül gerekebilir (`backend/zip_ops.py`).
- `backend/orchestrator.py` — `_SUPPORTED_OPERATION_TYPES`,
  `_ROLLBACK_OPERATIONS`, hedef-klasör-oluşturma hariç-tutma listesi, 4
  yeni step-uygulama bloğu.
- `backend/main.py` — yeni `POST /api/zip/list` endpoint'i (`search_endpoint`
  deseni).

## Rollback Beklentisi
ZIP_CREATE/ZIP_ADD/ZIP_MERGE: SPLIT/EXCEL_FILTER ile aynı `_rollback_copy`
deseni (kaynak asla değişmez, rollback sadece çıktıyı siler).
ZIP_EXTRACT: DELETE'in çoklu-dosya "geri alma" deseninden FARKLI — çıkarılan
DOSYALARIN TAMAMI bilinmiyor olabilir (hedef klasörde önceden dosya varsa
üzerine yazma AC-8), bu yüzden ZIP_EXTRACT'in rollback'i plan/code-copilot
adımında AYRICA netleştirilmeli (bkz. Unknowns — muhtemelen sadece YENİ
oluşturulan dosyalar/klasör silinir, üzerine yazılanlar GERİ ALINAMAZ,
DELETE'in "hiçbir zaman gerçek anlamda geri alınamaz" sınıfına benzer).

## Risks
- ZIP_EXTRACT'in `destinationFolder`'ı `PlanStep.targetFolder` (YYYY-MM
  formatına kilitli) ile ÇAKIŞMAMALI — ayrı bir alan olmalı, plan adımında
  şema tasarımı netleştirilmeli.
- Zip-slip koruması: sadece `../` DEĞİL, mutlak Windows path'leri (`C:\...`)
  ve sürücü harfi değişimi de kontrol edilmeli — code-copilot'a bu üç
  senaryo da AÇIKÇA talimat verilmeli.
- ZIP_EXTRACT'in rollback modelinin (üzerine yazılan dosyalar geri
  alınamaz) DELETE ile aynı "kalıcı yan etki" sınıfına girdiği kullanıcıya
  açıkça anlatılmalı (bkz. Rollback Beklentisi).

## Assumptions
- `filesToAdd` (ZIP_ADD) TEK bir dosya listesi kabul eder (birden fazla
  dosya EKLENEBİLİR, ama hepsi tek bir `PlanStep.fileNames`'in dışında,
  allowed_root'taki dosyalardan seçilir) — kullanıcı onaylamadı, plan
  adımında netleştirilmeli.

## Unknowns
- `destinationFolder` (ZIP_EXTRACT) ile `targetFolder` (mevcut, YYYY-MM
  formatına kilitli) arasındaki ilişki — plan adımında şema kararı
  gerekiyor.
- ZIP_EXTRACT'in rollback modeli (üzerine yazılan dosyalar için gerçek
  bir "geri alma" mümkün mü) — plan adımında netleştirilmeli.
- `filesToAdd`'in tekil/çoğul kapsamı — plan adımında netleştirilmeli.

## Sorular ve Cevaplar (ham kayıt)
1. Kapsam (beşi birden mi)? → Evet, beşi birden — zipfile stdlib olduğu
   için yeni bağımlılık yok.
2. Slug onayı → "zip-temel-operasyonlar" (onaylandı).
3. ZIP_CREATE kaynağı? → Seçili dosya listesi (MERGE deseni), klasör
   rekursif DEĞİL.
4. ZIP_EXTRACT hedefi? → Kullanıcının verdiği klasör adı (bug'ın asıl
   nedeni buydu, açıkça düzeltiliyor).
5. ZIP_ADD/ZIP_MERGE çıktı modeli? → İkisi de yeni dosyaya yaz.
6. ZIP_EXTRACT çakışma davranışı? → Üzerine yazılır, hata yok.
7. Zip-slip koruması dahil mi? → Evet, AC-S1 olarak eklendi.
8. Kabul kriteri + coverage + test oranı? → Otomatik test, %85, 75/20/5.
9. Kapsam dışı (plan_generation.py)? → Hayır, sadece backend modül +
   orchestrator + models + ZIP_OPEN endpoint'i.
10. Persona/hedef → task açıklamasından ve kapsam genişletme kararından
    türetildi.
