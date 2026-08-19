---
task_slug: excel-satir-filtreleme
jira_id: null
saga_task_id: 325
priority: high
coverage_target: 85
performance_target: null
memory_target: null
test_strategy:
  unit: 75
  integration: 20
  e2e: 5
affected_modules:
  - backend/excel_sort.py
  - backend/orchestrator.py
  - backend/models.py
---

# ATDD — excel-satir-filtreleme

## Jira Kaynağı
Jira'ya bağlı değil — yerel görev. Kaynak: Saga #325 (epic #29 "Format Agent Sistemi").

## Persona
windows-ai-files uygulamasını kullanan, doğal dille komut veren kullanıcı
("Ad sütununa göre filtrele", "Puan sütunu 90'a eşit olanları filtrele").
Sütun adını HER ZAMAN başlık metniyle ifade eder, harfle değil.

## Hedef (Neden)
İki parça:
1. Mevcut `resolve_sort_column` (Saga #324'te eklendi) zaten "Ad", "ID",
   "Yaş" gibi kısa/alfabetik başlıkların sütun harfiyle karıştırılmasını
   önlüyor — ama bu çözüm sadece EXCEL_SORT operasyonunda var.
2. Projede satır filtreleme (belirli bir sütun değerine göre satır alt
   kümesi çıkarma) operasyonu HİÇ yok. #325 kapsamı bu görüşmede
   filtrelemeyi de içerecek şekilde genişletildi (kullanıcı onayı) —
   aynı başlık-önce/harf-sonra çözümlemesini kullanan yeni bir
   EXCEL_FILTER operasyonu eklenecek.

## User Story
As a windows-ai-files kullanıcısı
I want Excel dosyasında bir sütun BAŞLIK ADI ve değerine göre satırları filtreleyip yeni bir dosyaya yazabilmek
So that "Ad"/"ID" gibi kısa başlıklar sütun harfiyle karıştırılıp sessiz no-op üretmesin ve filtreleme doğal dil komutuyla çalışsın

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. [Critical] Given başlık satırında "Puan" adlı bir sütun var, When filterColumn="Puan", filterValue=90 ile filtrelenir, Then sadece Puan değeri "90" olan satırlar (+ header) filteredFileName'e yazılır, kaynak değişmez.
2. [Critical] Given başlık satırında "Ad" adlı bir sütun var (kısa/alfabetik, sütun harfi "AD" ile karışabilir), When filterColumn="Ad" ile filtrelenir, Then başlık eşleşmesi ÖNCE denenir ve doğru sütun (Ad) kullanılır — asla harf yorumuna (ör. AD sütunu) düşülmez.
3. [High] Given filterColumn ne başlıkta ne geçerli bir sütun harfi olarak çözülebiliyor, When filtreleme çalıştırılır, Then `ValueError` → orchestrator'da `PlanApplicationError`'a çevrilir, hiçbir dosya yazılmaz.
4. [High] Given hiçbir satır filterValue'ya eşit değil, When filtreleme çalıştırılır, Then işlem başarılı sayılır, sadece header içeren bir dosya filteredFileName'e yazılır (hata fırlatılmaz).
5. [High] Given veri satırlarında (header hariç) en az bir GERÇEK formül hücresi (`cell.data_type == "f"`) var, When filtreleme çalıştırılır, Then `ExcelFilterFormulaGuardError` fırlatılır, sıfır satır işlenir, çıktı dosyası hiç oluşmaz.
6. [Medium] Given kaynak dosya boş sayfa veya sadece header içeriyor (0 veri satırı), When filtreleme çalıştırılır, Then no-op sayılır, dosya olduğu gibi filteredFileName'e kopyalanır, hata fırlatılmaz.

## Davranış Sözleşmesi (hangi durumda ne döner)
| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path (başlık eşleşmesi ile filtre) | `filter_excel_sheet()` None döner (exception yoksa başarı), orchestrator `operation.status="completed"` | filteredFileName'e yeni dosya yazılır, kaynak değişmez | Sonuç kartında yeni dosya adı, filtrelenmiş satır sayısı | AC-1, AC-2 |
| 2 | Girdi geçersiz/eksik (filterColumn boş) | Pydantic validator `ValueError` ("filterColumn is required when operationType is EXCEL_FILTER") — plan aşamasında engellenir | Yok, plan hiç kabul edilmez | Plan onay ekranında doğrulama hatası | AC-3 (girdi seviyesi) |
| 3 | Kaynak yok (dosya bulunamadı) | Mevcut orchestrator dosya-yok kontrolü (diğer operasyonlarla aynı, bu ATDD'de yeni davranış eklenmiyor) — `PlanApplicationError` | Yok | Hata mesajı | — (mevcut altyapı, değişmiyor) |
| 4 | Yetkisiz erişim (allowed_root dışı yol) | Mevcut `is_path_allowed` kontrolü — diğer operasyonlarla birebir aynı, bu task kapsamında değişmiyor | Yok | Hata mesajı | — (mevcut altyapı) |
| 5 | Sütun çözülemiyor (ne başlık ne harf) | `ValueError` → orchestrator'da yakalanıp `PlanApplicationError("Excel filtre sütunu çözülemedi: '...'")`'a çevrilir | Hiçbir dosya yazılmaz (temp dosya silinir) | Hata mesajı, işlem reddedildi | AC-3 |
| 6 | Formül guard tetiklenir | `ExcelFilterFormulaGuardError` → orchestrator'da `PlanApplicationError("Excel filtresi reddedildi, veri aralığında formül bulundu: ...")` | Sıfır satır işlenir, çıktı dosyası oluşmaz | Hata mesajı, işlem reddedildi | AC-5 |
| 7 | **Kısmi başarı** (bir kısmı oldu, kalanı olmadı) | Uygulanmaz — satırlık uygulanır: `filter_excel_sheet` tek bir atomik `tempfile + Path.replace` işlemidir (sort ile aynı desen), ara adım yok, ya tüm satırlar filtrelenip yazılır ya da hiçbiri | Kısmi yazma imkânsız (temp dosya + atomik replace) | — | — |
| 8 | **Hiçbir şey yapılamadı ama hata da yok** (0 satır eşleşti) | Başarı + header-only dosya (satır 4 ile aynı) — SESSİZ BAŞARI değil, mesajda "0 satır eşleşti" bilgisi olmalı | filteredFileName oluşur, sadece header | "0 satır eşleşti" mesajı görünür kılınmalı (sessiz "başarılı" değil) | AC-4 |

Kısmi başarı satırı: `sort_excel_sheet`/`filter_excel_sheet` deseni zaten
tempfile+atomik-replace kullandığı için ara/yarım durum fiziksel olarak
oluşamaz — silindi, gerekçe yukarıda.

Boş sonuç ↔ hata ayrımı: 0 satır eşleşmesi (AC-4/satır 8) ile sütun
çözülememesi (satır 5) FARKLI kod yollarıdır — biri `success` + boş veri,
diğeri `PlanApplicationError`. Aynı "boş" görünüme sahip olmamaları için
mesaj metninde "0 satır eşleşti" ile "sütun çözülemedi" ayrı ayrı ifade
edilir; ikisi de asla aynı dönüş değerine indirgenmez.

## Test Strategy
Unit: 75% — `resolve_sort_column`'ın filtre için de kullanılabilirliği
(gerekirse `resolve_column` adıyla ortaklaştırılır), `filter_excel_sheet`
formül-guard/0-satır/normal-eşleşme senaryoları (test_excel_sort.py
deseniyle aynı dosyada veya `test_excel_filter.py`).
Integration: 20% — orchestrator EXCEL_FILTER step uygulaması, rollback
(_rollback_copy), PlanApplicationError dönüşümleri.
E2E: 5% — plan oluştur → uygula → sonuç dosyasını oku uçtan uca (mevcut
test_main_integration.py deseniyle).

## Benchmark / Başarı Ölçütü
Coverage Target: 85%
Performance Target: yok (küçük/deterministik modül, mevcut EXCEL_SORT
task'ında da performans hedefi tanımlanmamıştı)
Memory: yok
Diğer ölçülebilir kriterler: pytest tüm testler yeşil (verify pipeline
gate'i geçmesi kabul kriteri sahibi — bkz. Sorular ve Cevaplar #10).

## Kapsam Dışı
- Birden fazla filtre koşulu (AND/OR kombinasyonu) — sadece tek sütun/tek değer.
- Eşitlik dışı operatörler (içerir, büyük/küçük, aralık) — sadece tam eşitlik (`str(hücre) == str(değer)`).
- `plan_generation.py`/LLM prompt güncellemesi (doğal dilden filterColumn/filterValue çıkarma) — ayrı bir Saga task'a bırakıldı, bu ATDD sadece backend modül + orchestrator + models kapsıyor.
- Kaynağı yerinde değiştirme — sadece yeni dosyaya yazma modeli (EXCEL_SORT ile aynı).

## Etkilenen Dosyalar/Modüller (bilinen)
- `backend/excel_sort.py` — `filter_excel_sheet()` fonksiyonu eklenecek (muhtemelen `resolve_sort_column` paylaşılan hâle getirilip `resolve_column` adıyla yeniden adlandırılır), `ExcelFilterFormulaGuardError` sınıfı.
- `backend/models.py` — `OperationType.EXCEL_FILTER`, `PlanStep`e `filterColumn`/`filterValue`/`filteredFileName` alanları + aynı validator deseni (Parametre Ekleme Tuzağı — bkz. proje hafızası: 3 yerde eklenmezse Pydantic sessizce siler).
- `backend/orchestrator.py` — `EXCEL_FILTER` step uygulaması (EXCEL_SORT bloğuyla birebir aynı desen, satır 681-707 civarı), rollback haritasına `_rollback_copy` eklenmesi (satır 339-341 civarı, EXCEL_SORT ile aynı).
- (varsa) `capabilities.json` veya benzeri araç şeması dosyası — proje hafızasındaki "Parametre Ekleme Tuzağı" üçüncü konum; plan/code-copilot adımında doğrulanmalı.

## Rollback Beklentisi
EXCEL_SORT ile birebir aynı `_rollback_copy` deseni: kaynak dosyaya hiç
dokunulmadığı için rollback sadece çıktı (filteredFileName) dosyasını siler.

## Risks
- `resolve_sort_column`'ı `filter_excel_sheet` ile paylaşmak için isim
  değişikliği (`resolve_column`) gerekebilir — mevcut `test_excel_sort.py`
  bu fonksiyonu adıyla import ediyorsa refactor sırasında kırılabilir,
  plan adımında kontrol edilmeli.
- `capabilities.json` (veya eşdeğeri) üçüncü parametre-ekleme noktası
  gözden kaçarsa LLM plan üretiminde EXCEL_FILTER hiç tetiklenmez (proje
  hafızası: Parametre Ekleme Tuzağı).

## Assumptions
- Filtre değeri (`filterValue`) string olarak karşılaştırılıyor
  (`str(hücre) == str(değer)`), tip normalizasyonu `_sort_key`'deki gibi
  ayrıca ele alınmıyor çünkü eşitlik karşılaştırması tip duyarlılığına
  `_resolve_col`'daki kadar bağımlı değil — kullanıcı onaylamadı, varsayım
  olarak işaretli, plan adımında netleştirilmeli.

## Unknowns
- `capabilities.json` dosyasının tam yolu ve EXCEL_SORT için nasıl
  tanımlandığı bu görüşmede doğrulanmadı — `plan` adımında Glob/Grep ile
  bulunmalı.

## Sorular ve Cevaplar (ham kayıt)
1. Sütun çözümleme davranışı zaten var mı? → Evet, `resolve_sort_column`
   (backend/excel_sort.py) başlık-önce/harf-sonra çözümlemesini Saga
   #324'te zaten uyguluyor (kod incelemesiyle tespit edildi).
2. #325 ile ne yapılsın (kod zaten var, filtreleme hiç yok)? → Filtreleme
   özelliğini de şimdi ekle (kapsam genişletildi).
3. Çıktı modeli? → Yeni dosyaya yaz (EXCEL_SORT ile aynı desen).
4. Eşleşme operatörü? → Sadece tam eşitlik.
5. 0 satır eşleşirse? → Başarı + sadece header'lı boş dosya.
6. Test stratejisi oranı? → 75/20/5 (Recommended, onaylandı).
7. Formül guard filtrede de uygulansın mı? → Evet, aynı guard.
8. Coverage/performans hedefi? → Coverage %85, performans hedefi yok.
9. Kapsam dışı (plan_generation.py dahil mi)? → Hayır, sadece backend
   modül + orchestrator + models; plan_generation.py ayrı task.
10. Kabul kriteri sahibi? → Otomatik test (pytest yeşil).
11. Rollback beklentisi? → COPY deseniyle aynı (kullanıcıya tekrar
    sorulmadı, EXCEL_SORT ile mimari tutarlılık gerekçesiyle tek seçenek
    olarak sunuldu ve zımnen kabul edildi).
12. Persona/hedef → task açıklamasından ve kapsam genişletme kararından
    türetildi, ayrıca sorulmadı.
