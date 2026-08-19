---
task_slug: pdf-sayfa-araligi-secimi
jira_id: null
saga_task_id: 321
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

# ATDD — pdf-sayfa-araligi-secimi

## Jira Kaynağı
Jira'ya bağlı değil — yerel görev. Kaynak: Saga #321 (epic #29 "Format Agent
Sistemi").

## Persona
windows-ai-files kullanıcısı (muhasebeci tipi), doğal dille komut veren
("1, 3 ve 5-9 sayfalarını çıkar/böl", "3. sayfayı sil"). Sayfa numaralarını
her zaman 1-indexed düşünür ("1. sayfa" = belgenin ilk sayfası).

## Hedef (Neden)
Eski projede (`core/agents/pdf_agent.py`) iki bağımsız veri kaybı sınıfı
vardı:
1. `parse_page_spec`: karışık ayrık+aralık istekler ("1,3,5-9") min/max
   alıp aralığa genişletiliyordu — "1,3,5" yanlışlıkla 1..5 olarak
   yorumlanıp sessiz veri hatası üretiyordu.
2. `_delete_pages`: baştan sona silme sırasında her silme sonrası kalan
   sayfaların indeksleri kayıyordu — hata vermeden yanlış sayfalar
   siliniyordu (klasik sessiz veri kaybı, çözüm TERSTEN silmek).

Bu görüşmede kapsam netleştirildi: hem SEÇİLİ sayfaları tek bir dosyaya
çıkarma (extract) hem de kaynaktan belirli sayfaları çıkarıp kalanı yeni
bir dosyaya yazma (delete) — ikisi de aynı `parse_page_spec` doğrulamasını
paylaşır.

## User Story
As a windows-ai-files kullanıcısı
I want "1,3,5-9" gibi karışık ayrık+aralık bir sayfa listesi belirterek PDF'ten seçili sayfaları tek dosyaya çıkarabilmek VEYA kaynaktan seçili sayfaları silip kalanını yeni bir dosyaya yazdırabilmek
So that ne yanlış sayfa aralığı yorumlanıp sessiz veri hatası üretilsin ne de silme sırasında indeks kaymasıyla yanlış sayfalar silinsin

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. [Critical] Given 10 sayfalık bir PDF, When `pageSpec="1,3,5-9"` ile PDF_EXTRACT_PAGES çalıştırılır, Then çıktı dosyası TAM OLARAK [1,3,5,6,7,8,9] sayfalarını (orijinal sırayla) içerir, kaynak değişmez.
2. [Critical] Given 10 sayfalık bir PDF, When `pageSpec="1,3,5-9"` ile PDF_DELETE_PAGES çalıştırılır, Then çıktı dosyası TAM OLARAK [2,4,10] sayfalarını (kalanları, orijinal sırayla) içerir, kaynak değişmez.
3. [Critical] Given `pageSpec="9-5"` (ters aralık, başlangıç>bitiş), When herhangi bir operasyon çalıştırılır, Then `ValueError` → `PlanApplicationError`, hiçbir dosya yazılmaz.
4. [High] Given `pageSpec="1,3,8"` ama belge 5 sayfa (8 belge dışı), When operasyon çalıştırılır, Then TÜM istek reddedilir (kısmi işlem YOK), `PlanApplicationError`, hiçbir dosya yazılmaz.
5. [High] Given PDF_DELETE_PAGES ile TÜM sayfalar silinirse (0 sayfa kalır), When operasyon çalıştırılır, Then `PlanApplicationError`, hiçbir dosya yazılmaz (0 sayfalık boş PDF sessizce üretilmez).
6. [Medium] Given `pageSpec=" 1, 3 , 5-9 "` (boşluklu), When parse edilir, Then boşluklar trim edilir, `"1,3,5-9"` ile AYNI sonucu üretir.
7. [Medium] Given `pageSpec="1,1,3"` (tekrarlanan sayfa), When parse edilir, Then tekrar sessizce tekilleştirilir (orijinal belge sırası korunur, sayfa iki kez çıkmaz).

## Davranış Sözleşmesi (hangi durumda ne döner)
| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path (extract) | `extract_pdf_pages()` None döner (exception yoksa başarı), `operation.status="completed"` | Yeni dosyaya (extractedFileName) yazılır, kaynak değişmez | Sonuç kartında yeni dosya, seçili sayfa sayısı | AC-1 |
| 1b | Happy path (delete) | `delete_pdf_pages()` None döner, `operation.status="completed"` | Kalan sayfalar yeni dosyaya (remainingFileName) yazılır, kaynak değişmez | Sonuç kartında yeni dosya, kalan sayfa sayısı | AC-2 |
| 2 | Girdi geçersiz/eksik (pageSpec boş) | Pydantic validator `ValueError` ("pageSpec is required when operationType is PDF_EXTRACT_PAGES/PDF_DELETE_PAGES") — plan aşamasında engellenir | Yok, plan hiç kabul edilmez | Plan onay ekranında doğrulama hatası | AC girdi seviyesi |
| 3 | Kaynak yok / yetkisiz erişim | Mevcut orchestrator dosya-yok/`is_path_allowed` kontrolü (diğer operasyonlarla aynı, bu ATDD'de yeni davranış eklenmiyor) | Yok | Hata mesajı | — (mevcut altyapı) |
| 4 | Ters aralık ("9-5") veya belge-dışı sayfa numarası | `ValueError` → `PlanApplicationError("PDF sayfa aralığı çözülemedi: '...'")` | Hiçbir dosya yazılmaz | Hata mesajı, işlem reddedildi | AC-3, AC-4 |
| 5 | TÜM sayfalar silinir (delete, 0 sayfa kalır) | `ValueError` (`parse_page_spec`/`delete_pdf_pages` içinde erken kontrol) → `PlanApplicationError("PDF'in tüm sayfaları silinemez: ...")` | Hiçbir dosya yazılmaz | Hata mesajı | AC-5 |
| 6 | **Kısmi başarı** (bazı sayfalar geçerli, bazıları değil) | Uygulanmaz — AC-4 gereği TÜM istek ATOMIK reddedilir, kısmi sayfa seçimi asla uygulanmaz | Hiçbir dosya yazılmaz | Hata mesajı, hangi sayfa numarasının geçersiz olduğu belirtilir | AC-4 |
| 7 | **Hiçbir şey yapılamadı ama hata da yok** | Uygulanmaz — bu operasyonlarda "boş ama başarılı" durumu YOKTUR: pageSpec her zaman en az 1 geçerli sayfa numarası içermek zorunda (boş string zaten validator'da reddedilir), extract/delete her zaman ya tüm istenen sayfaları işler ya da tamamen reddeder | — | — | — |

Kısmi başarı satırı: `extract_pdf_pages`/`delete_pdf_pages` deseni EXCEL_SORT/
EXCEL_FILTER'daki tempfile+atomik-replace ile AYNI — ama önce TÜM pageSpec
doğrulanır (parse + belge sınırı kontrolü), sonra yazma başlar. Böylece
"bazı sayfalar işlendi bazıları işlenmedi" durumu fiziksel olarak
oluşamaz — ya hiç yazma başlamaz (doğrulama reddi) ya da komple yazılır.

"Hiçbir şey yapılamadı ama hata da yok" satırı UYGULANMIYOR ve silindi:
pageSpec boşsa/geçersizse şema seviyesinde reddedilir (validator), bu
yüzden "sessizce hiçbir şey yapmama" durumu bu iki operasyon için
mimari olarak imkânsız — EXCEL_FILTER'daki "0 satır eşleşti" senaryosunun
(orada geçerli bir sonuçtu) burada karşılığı YOK, çünkü pageSpec zaten en
az 1 geçerli sayfa numarası taşımak ZORUNDA.

Boş sonuç ↔ hata ayrımı: "0 sayfa kaldı" (delete, satır 5) her zaman
hatadır — asla "başarılı ama boş dosya" olarak yorumlanmaz, EXCEL_FILTER'ın
"0 satır eşleşti = başarı" kararından KASITLI OLARAK FARKLI (PDF'te
0 sayfalık bir dosya anlamsızdır, Excel'de 0 satırlı-ama-header'lı bir
dosya anlamlıdır).

## Test Strategy
Unit: 75% — `parse_page_spec` (ayrık+aralık karışık, boşluk normalize,
ters aralık hatası, tekrar tekilleştirme, belge-dışı sayfa kontrolü),
`extract_pdf_pages`/`delete_pdf_pages` (happy path, 0-sayfa-kalır hatası).
Integration: 20% — orchestrator PDF_EXTRACT_PAGES/PDF_DELETE_PAGES step
uygulaması, rollback (COPY deseni), PlanApplicationError dönüşümleri.
E2E: 5% — plan oluştur → uygula → sonuç dosyasını oku uçtan uca.

## Benchmark / Başarı Ölçütü
Coverage Target: 85%
Performance Target: yok
Memory: yok
Diğer ölçülebilir kriterler: pytest tüm testler yeşil (verify pipeline
gate'i geçmesi kabul kriteri sahibi).

## Kapsam Dışı
- `plan_generation.py`/LLM prompt güncellemesi (doğal dilden pageSpec
  çıkarma) — ayrı bir Saga task'a bırakıldı (EXCEL_FILTER'daki kararla
  tutarlı), bu ATDD sonunda PDF_EXTRACT_PAGES/PDF_DELETE_PAGES sadece
  API/orchestrator seviyesinde çalışır, doğal dil komutuyla henüz
  tetiklenemez.
- Saga #322 (PDF sıkıştırma) — ayrı görev, bu ATDD'ye dahil değil.
- Sayfa aralığı dışında başka bir seçim sözdizimi (ör. "son 3 sayfa",
  "tek sayılı sayfalar") — sadece açık numara/aralık listesi.
- Kaynağı yerinde güncelleme — sadece yeni dosyaya yazma modeli (SPLIT/
  EXCEL_FILTER ile aynı).

## Etkilenen Dosyalar/Modüller (bilinen)
- `backend/models.py` — `OperationType.PDF_EXTRACT_PAGES`,
  `OperationType.PDF_DELETE_PAGES`; `PlanStep`e `pageSpec` +
  `extractedFileName`/`remainingFileName` alanları + aynı validator deseni
  (EXCEL_FILTER'daki gibi 3-yerde-kayıt tuzağına dikkat).
- Yeni bir modül gerekebilir (`backend/pdf_pages.py`) — `parse_page_spec`,
  `extract_pdf_pages`, `delete_pdf_pages` — EXCEL_SORT'un `excel_sort.py`
  ile aynı ayrım deseni (plan adımında kesinleştirilecek).
- `backend/orchestrator.py` — `_SUPPORTED_OPERATION_TYPES`,
  `_ROLLBACK_OPERATIONS` (`_rollback_copy`), hedef-klasör-oluşturma
  hariç-tutma listesi, iki yeni step-uygulama bloğu (SPLIT/EXCEL_FILTER
  ile aynı desen).

## Rollback Beklentisi
SPLIT/EXCEL_FILTER ile birebir aynı `_rollback_copy` deseni: kaynak
dosyaya hiç dokunulmadığı için rollback sadece çıktı dosyasını siler.

## Risks
- pypdf'in sayfa indeksleme API'si 0-indexed — `parse_page_spec`'in
  1-indexed girdiyi doğru çevirdiğinden emin olunmalı (off-by-one riski,
  test-copilot'ta özellikle hedeflenmeli).
- İki operasyonun (extract/delete) `parse_page_spec`'i paylaşması,
  EXCEL_SORT/EXCEL_FILTER'ın `resolve_sort_column` paylaşımıyla AYNI
  isimlendirme gerilimini taşıyor — plan adımında netleştirilmeli.

## Assumptions
- `pageSpec` formatı sadece virgülle ayrılmış tekil sayfa numaraları ve
  `başlangıç-bitiş` aralıklarından oluşur (ör. "1,3,5-9"); başka bir
  sözdizimi (regex, wildcard) desteklenmez — kullanıcı onayladı (Format
  Kuralları sorusu).

## Unknowns
- Yeni bir `backend/pdf_pages.py` modülü mü gerekir yoksa mevcut bir
  dosyaya mı (`orchestrator.py` içine yardımcı fonksiyon olarak) eklenir
  — plan adımında kod tabanı incelenerek netleştirilmeli.

## Sorular ve Cevaplar (ham kayıt)
1. Slug onayı → "pdf-sayfa-araligi-secimi" (onaylandı).
2. Kapsam: extract + delete mi, sadece biri mi? → Her ikisi de (kapsam
   genişletildi, iki yeni operasyon).
3. Belge-dışı sayfa numarası davranışı? → Açık hata, TÜM istek reddedilir
   (kısmi işlem yok).
4. Delete çıktı modeli? → Yeni dosyaya yaz (SPLIT/EXCEL_FILTER ile aynı
   desen, kaynak asla değişmez).
5. Tüm sayfalar silinirse? → Açık hata (görev açıklamasından zaten netti,
   tekrar sorulmadı).
6. Format kuralları (boşluk/ters aralık/tekrar)? → Boşluk normalize
   edilir, ters aralık hata, tekrar sessizce tekilleştirilir.
7. Kabul kriteri sahibi + coverage? → Otomatik test (pytest yeşil), %85
   coverage.
8. Test stratejisi oranı? → 75/20/5.
9. Sayfa indeksleme? → 1-indexed (kullanıcı dili her zaman 1'den başlar,
   tek mantıklı seçenek olduğu için tekrar sorulmadı).
10. Kapsam dışı (plan_generation.py dahil mi)? → Hayır, sadece backend
    modül + orchestrator + models; plan_generation.py ayrı task.
11. Persona/hedef → task açıklamasından ve kapsam genişletme kararından
    türetildi.
12. Rollback beklentisi → SPLIT/EXCEL_FILTER ile mimari tutarlılık
    gerekçesiyle tek seçenek olarak sunuldu, ayrıca sorulmadı.
