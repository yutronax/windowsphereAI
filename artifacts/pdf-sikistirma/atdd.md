---
task_slug: pdf-sikistirma
jira_id: null
saga_task_id: 322
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
---

# ATDD — pdf-sikistirma

## Jira Kaynağı
Jira'ya bağlı değil — yerel görev. Kaynak: Saga #322 (epic #29 "Format Agent
Sistemi").

## Persona
windows-ai-files kullanıcısı (muhasebeci tipi) — büyük PDF belgelerini
(taranmış faturalar, ekli görsel içeren raporlar) e-posta ile göndermeden
önce dosya boyutunu küçültmek isteyen kişi.

## Hedef (Neden)
Eski projede (`core/agents/pdf_agent.py _compress`) üç kontrol eksikti:
1. Sonuç orijinalden büyükse orijinal korunmalıydı ama bu kontrol edilmiyordu
   — kullanıcıya daha büyük bir dosya "sıkıştırılmış" diye verilebiliyordu.
2. Hedef boyuta ulaşılamazsa bu sessizce geçiliyordu.
3. Ghostscript/QPDF yoksa raster yedeği kullanılabiliyordu ama bunun
   maliyeti (metin aranamaz hale gelir) açıkça söylenmiyordu.

Ortam incelemesi bu görüşmede yapıldı: `gs`/`qpdf` kurulu DEĞİL,
requirements.txt'te de yok. Kullanıcı kararıyla kapsam **pypdf-native**
sıkıştırmayla sınırlandı (yeni binary bağımlılık yok, raster yedeği YOK) —
bu, eski projenin 3 kontrolünden sadece 1 ve 2'yi bu ATDD'nin kapsamına
alır; 3 (raster yedek + maliyet uyarısı) kapsam dışı bırakıldı çünkü
pypdf-native yaklaşımda hiç devreye girmiyor.

## User Story
As a windows-ai-files kullanıcısı
I want bir PDF'i pypdf-native yöntemlerle (içerik akışı sıkıştırma, yinelenen nesne kaldırma) sıkıştırıp yeni bir dosyaya kaydedebilmek
So that sonuç dosyası orijinalden asla büyük olmasın ve sıkıştırma sağlanamadığında bu durum açıkça bilinsin, sessizce geçilmesin

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. [Critical] Given sıkıştırılabilir içerik akışları olan bir PDF, When PDF_COMPRESS çalıştırılır, Then çıktı dosyası (compressedFileName) orijinalden KÜÇÜK boyutta yazılır, kaynak değişmez.
2. [Critical] Given sıkıştırma sonucu orijinal boyuta eşit veya ondan BÜYÜK çıkar (büyüme koruması), When PDF_COMPRESS çalıştırılır, Then compressedFileName YAZILMAZ, işlem yine de başarılı sayılır ama kullanıcıya "sıkıştırma sağlanamadı, dosya zaten optimal" bilgisi açıkça iletilir (sessizce geçilmez).
3. [High] Given kaynak PDF bozuk/pypdf açamıyor, When PDF_COMPRESS çalıştırılır, Then `PlanApplicationError`, hiçbir dosya yazılmaz.
4. [High] Given compressedFileName kaynak dosyalardan biriyle (fileNames) çakışıyor, When plan doğrulanır, Then Pydantic validator reddi (EXCEL_FILTER'daki filteredFileName collision check ile aynı desen).
5. [Medium] Given tek sayfalık/çok küçük bir PDF (zaten sıkıştırılmış boyutta), When PDF_COMPRESS çalıştırılır, Then AC-2 ile aynı yola düşer (büyüme koruması), hata DEĞİL.

## Davranış Sözleşmesi (hangi durumda ne döner)
| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path (gerçek sıkışma sağlandı) | `compress_pdf(...)` `True` döner (sıkıştırıldı), `operation.status="completed"` | compressedFileName'e KÜÇÜLTÜLMÜŞ dosya yazılır, kaynak değişmez | Sonuç kartında yeni dosya + boyut azalması | AC-1 |
| 2 | Girdi geçersiz/eksik (compressedFileName boş/çakışıyor) | Pydantic validator `ValueError` — plan aşamasında engellenir | Yok, plan hiç kabul edilmez | Plan onay ekranında doğrulama hatası | AC-4 |
| 3 | Kaynak yok / bozuk / yetkisiz erişim | Mevcut orchestrator dosya-yok/`is_path_allowed` kontrolü + pypdf açma hatası → `PlanApplicationError("PDF sıkıştırılamadı, dosya okunamıyor: ...")` | Hiçbir dosya yazılmaz | Hata mesajı | AC-3 |
| 4 | **Büyüme koruması** (sonuç >= orijinal boyut) | `compress_pdf(...)` `False` döner (sıkıştırılmadı) — hata DEĞİL | compressedFileName YAZILMAZ, kaynak değişmez | "Sıkıştırma sağlanamadı, dosya zaten optimal boyutta" bilgisi (kesin mekanizma plan adımında belirlenecek — bkz. Unknowns) | AC-2, AC-5 |
| 5 | **Kısmi başarı** (bir kısmı oldu, kalanı olmadı) | Uygulanmaz — tek dosya, tek operasyon; `_write_pages`/`filter_excel_sheet` ile AYNI atomik tempfile+replace deseni, ara durum fiziksel olarak oluşamaz | — | — | — |
| 6 | **Hiçbir şey yapılamadı ama hata da yok** | Satır 4 ile ÖRTÜŞÜYOR — büyüme koruması TAM OLARAK bu durumun kendisi: hiçbir dosya değişmedi, hata da yok. Kritik fark: EXCEL_FILTER'ın "0 satır eşleşti"nden farklı olarak burada dosya HİÇ YAZILMIYOR (header-only dosya gibi bir "boş ama geçerli" çıktı kavramı PDF sıkıştırmada yok) — kullanıcıya bunun AÇIKÇA raporlanması ZORUNLU (görev açıklamasının ana motivasyonu) | AC-2 |

Kısmi başarı satırı silindi: tek dosya/tek atomik yazma operasyonu olduğu
için ara durum oluşamaz (gerekçe yukarıda).

Boş sonuç ↔ hata ayrımı: "büyüme koruması" (satır 4/6) ile "kaynak bozuk"
(satır 3) FARKLI kod yollarıdır — biri `compress_pdf` `False` döndürür
(başarı, dosya yok), diğeri `PlanApplicationError` fırlatır (hata, dosya
yok). İkisi de "dosya yok" ile sonuçlanır ama SEBEPLERİ ve kullanıcıya
gösterilen mesaj AÇIKÇA farklı olmalı — aynı genel "işlem başarısız" mesajına
indirgenmemeli.

## Test Strategy
Unit: 75% — `compress_pdf` (gerçek sıkışma sağlanan senaryo, büyüme
koruması tetiklenen senaryo, bozuk kaynak → exception).
Integration: 20% — orchestrator PDF_COMPRESS step uygulaması, büyüme
koruması durumunda dosya oluşmadığının doğrulanması, rollback.
E2E: 5% — plan oluştur → uygula → sonuç dosyasını oku uçtan uca.

## Benchmark / Başarı Ölçütü
Coverage Target: 85%
Performance Target: yok
Memory: yok
Diğer ölçülebilir kriterler: pytest tüm testler yeşil.

## Kapsam Dışı
- Ghostscript/QPDF entegrasyonu (dış binary bağımlılık) — kullanıcı kararıyla
  kapsam dışı, sadece pypdf-native yöntemler kullanılacak.
- Raster (görüntüye çevirme) yedeği — pypdf-native yaklaşımda hiç
  gerekmiyor, eski projenin bu maddesi bu ATDD'de YOK.
- Hedef boyut/oran parametresi (`targetSizeBytes` gibi) — kullanıcı
  kararıyla kapsam dışı, sadece "mümkün olduğunca sıkıştır".
- `plan_generation.py`/LLM prompt güncellemesi (doğal dilden sıkıştırma
  isteği çıkarma) — ayrı bir Saga task'a bırakıldı (önceki görevlerle
  tutarlı karar).

## Etkilenen Dosyalar/Modüller (bilinen)
- `backend/models.py` — `OperationType.PDF_COMPRESS`; `PlanStep`e
  `compressedFileName` alanı + validator (EXCEL_FILTER'daki
  `filteredFileName` deseniyle aynı).
- Yeni bir modül gerekebilir (`backend/pdf_compress.py`) — `compress_pdf(
  source_path, destination_path) -> bool` (plan adımında kesinleştirilecek,
  `pdf_pages.py`/`pdf_redact.py` ile aynı ayrım deseni).
- `backend/orchestrator.py` — `_SUPPORTED_OPERATION_TYPES`,
  `_ROLLBACK_OPERATIONS` (`_rollback_copy` — ama sadece dosya YAZILDIYSA
  anlamlı, büyüme-koruması durumunda rollback edilecek bir şey yok, bu
  plan adımında netleştirilmeli), hedef-klasör-oluşturma hariç-tutma
  listesi, yeni step-uygulama bloğu.

## Rollback Beklentisi
Dosya YAZILDIYSA (AC-1): SPLIT/EXCEL_FILTER ile aynı `_rollback_copy`
deseni — kaynak hiç değişmediği için rollback sadece çıktıyı siler.
Dosya YAZILMADIYSA (AC-2, büyüme koruması): rollback edilecek bir şey
yok — bu durumda `record_file_operation`'ın hiç çağrılıp çağrılmayacağı
(ve dolayısıyla rollback haritasının bu durumda hiç devreye girmeyeceği)
plan adımında kod incelemesiyle netleştirilmeli (bkz. Unknowns).

## Risks
- pypdf-native sıkıştırmanın GERÇEK sıkışma oranı düşük olabilir (görsel
  ağırlıklı PDF'lerde içerik-akışı sıkıştırma çok az fark eder) — bu,
  AC-2/AC-5'in (büyüme koruması) BEKLENENDEN SIK tetiklenebileceği
  anlamına gelir; bu bir bug değil, kullanıcının bilinçli seçtiği kapsam
  sınırlamasının doğal sonucu.
- "Büyüme koruması" durumunun kullanıcıya nasıl iletileceği (hangi API
  alanı/mekanizma üzerinden) henüz kod seviyesinde netleşmedi — mevcut
  `TransactionApplyResponse.warnings` mekanizması (REDACT'ta kullanılıyor)
  STATİK olarak plan.steps üzerinden üretiliyor (main.py:462-465), bizim
  ihtiyacımız DİNAMİK (sadece GERÇEKTEN büyüme korumasına düşülürse
  uyarı) — mevcut mekanizma DOĞRUDAN uymuyor, plan adımında somut bir
  çözüm (ör. `AppliedFileOperation`'a bir `note`/`status` alanı eklemek)
  önerilmeli.

## Assumptions
- `compress_pdf` fonksiyonu bir `bool` döndürür (sıkıştı/sıkışmadı) —
  exception fırlatmaz (exception SADECE gerçek hatalar için, ör. bozuk
  dosya) — kullanıcı onaylamadı, mimari tutarlılık gerekçesiyle önerildi,
  plan adımında kesinleştirilmeli.

## Unknowns
- Büyüme koruması durumunun kullanıcıya iletilme mekanizması (bkz. Risks)
  — plan adımında `backend/models.py`/`backend/main.py` incelenerek somut
  bir tasarım kararına bağlanmalı.
- Yeni bir `backend/pdf_compress.py` modülü mü gerekir yoksa mevcut bir
  dosyaya mı eklenir — plan adımında netleştirilmeli.

## Sorular ve Cevaplar (ham kayıt)
1. Sıkıştırma stratejisi (Ghostscript/QPDF/raster/pypdf-native)? →
   pypdf-native (ortam incelemesiyle: gs/qpdf kurulu değil).
2. Slug onayı → "pdf-sikistirma" (onaylandı).
3. Çıktı modeli? → Yeni dosyaya yaz (SPLIT/EXCEL_FILTER ile aynı desen).
4. Büyüme koruması davranışı? → Çıktı dosyası yazılmaz, açık "zaten
   küçük/sıkıştırılamadı" mesajı (sessiz başarı DEĞİL, ama hata da DEĞİL).
5. Hedef boyut parametresi var mı? → Yok, sadece "mümkün olduğunca
   sıkıştır".
6. Bozuk kaynak davranışı? → Açık hata, `PlanApplicationError` (proje
   konvansiyonuyla tek mantıklı seçenek, tekrar sorulmadı).
7. Kabul kriteri sahibi + coverage + test oranı? → Otomatik test (pytest
   yeşil), %85 coverage, 75/20/5.
8. Kapsam dışı (plan_generation.py dahil mi)? → Hayır, sadece backend
   modül + orchestrator + models.
9. Persona/hedef → task açıklamasından ve ortam incelemesinden türetildi.
10. Rollback beklentisi → mimari tutarlılık gerekçesiyle önerildi, ama
    "dosya yazılmadıysa" durumu netleşmediği için Unknowns'a taşındı.
