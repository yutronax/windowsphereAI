---
task_slug: word-tablo-basligi
jira_id: null
saga_task_id: 327
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
  - requirements.txt
---

# ATDD — word-tablo-basligi

## Jira Kaynağı
Jira'ya bağlı değil — yerel görev. Kaynak: Saga #327 (epic #29 "Format Agent
Sistemi") — İKİ alt özellikten (Word→PDF dönüştürme + tablo başlıkları)
sadece İKİNCİSİ bu ATDD'nin kapsamında.

## Persona
windows-ai-files kullanıcısı (muhasebeci tipi) — var olan bir Word
belgesine, başlık satırı olan/olmayan bir veri tablosu (ör. bir gider
listesi) eklemek isteyen kişi.

## Hedef (Neden)
Ortam incelemesi bu görüşmede kapsamı belirledi: görev açıklaması iki
bağımsız alt özellik içeriyordu —
1. Word→PDF dönüştürme (LibreOffice/`soffice` binary'sine ihtiyaç duyar).
2. Word tabloya başlık ekleme (sadece `python-docx` kütüphanesi gerekir).

Ortamda `soffice` KURULU DEĞİL (pip ile de kurulamaz, dış binary) — bu
yüzden kullanıcı kararıyla kapsam SADECE tablo başlıkları özelliğine
daraltıldı; dönüştürme ayrı bir Saga task'a (LibreOffice kurulduktan
sonra) bırakıldı.

Eski projede (`core/agents/word_agent.py`) şema `"headers"` alanı ilan
ediyordu ama fonksiyon SADECE `"rows"` okuyordu — kullanıcı başlık
girse bile tablo başlıksız oluşuyordu (sessiz veri kaybı).

## User Story
As a windows-ai-files kullanıcısı
I want var olan bir Word belgesine, isteğe bağlı bir başlık satırıyla, veri satırlarından oluşan bir tablo ekleyebilmek
So that verdiğim başlık sessizce düşmesin ve tablo her zaman istediğim yapıda oluşsun

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. [Critical] Given var olan bir `.docx` ve `headers=["Ad","Tutar"]`, `rows=[["Ali","100"],["Veli","200"]]`, When WORD_APPEND_TABLE çalıştırılır, Then belgeye EN ÜSTTE başlık satırı olan 3 satırlık bir tablo eklenir, önceki içerik korunur.
2. [Critical] Given `headers` VERİLMEMİŞ (`None`) ve sadece `rows`, When WORD_APPEND_TABLE çalıştırılır, Then başlıksız (sadece veri satırlarından oluşan) bir tablo eklenir, hata FIRLATILMAZ.
3. [High] Given `headers` 3 sütunlu ama bir `rows` satırı 2 hücreli (uyuşmazlık), When WORD_APPEND_TABLE çalıştırılır, Then `PlanApplicationError`, belgeye HİÇBİR ŞEY eklenmez, kaynak değişmez.
4. [High] Given kaynak `.docx` yok veya bozuk (python-docx açamıyor), When WORD_APPEND_TABLE çalıştırılır, Then `PlanApplicationError`, kaynak değişmez.

## Davranış Sözleşmesi (hangi durumda ne döner)
| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path (başlıklı) | `operation.status="completed"` | Kaynak YERİNDE güncellenir (EXCEL_APPEND/PDF APPEND deseni), tablo eklenir | Sonuç kartı, belge güncellendi | AC-1 |
| 2 | Happy path (başlıksız) | `operation.status="completed"` | Kaynak YERİNDE güncellenir, başlıksız tablo eklenir | Sonuç kartı | AC-2 |
| 3 | Sütun sayısı uyuşmazlığı | `PlanApplicationError("WORD_APPEND_TABLE sütun sayısı uyuşmuyor: ...")` | HİÇBİR dosya değişmez | Hata mesajı | AC-3 |
| 4 | Kaynak yok/bozuk | `PlanApplicationError("WORD_APPEND_TABLE kaynağı okunamıyor: ...")` | HİÇBİR dosya değişmez | Hata mesajı | AC-4 |
| 5 | **Kısmi başarı** (bir kısmı oldu, kalanı olmadı) | Uygulanmaz — tek tablo/tek atomik yazma (backup+tempfile+atomik-replace deseni, EXCEL_APPEND'in AYNI garantisi), ara durum fiziksel olarak oluşamaz | — | — | — |
| 6 | **Hiçbir şey yapılamadı ama hata da yok** | Uygulanmaz — `rows` boş olamaz (validator), her çağrı ya tabloyu ekler ya hata fırlatır, sessiz no-op mimari olarak imkânsız | — | — | — |

Kısmi başarı ve "hiçbir şey yapılamadı ama hata yok" satırları silindi:
tek atomik yazma operasyonu (EXCEL_APPEND'in backup+tempfile+atomik-replace
deseni izlenecek), ara/sessiz durum oluşamaz.

Boş sonuç ↔ hata ayrımı: `headers=None` (AC-2, geçerli/beklenen bir durum,
başarı) ile sütun sayısı uyuşmazlığı (AC-3, hata) FARKLI kod yollarıdır —
ikisi de "başlık eksik/tuhaf" gibi görünebilir ama biri başarı biri hata,
aynı mesaja indirgenmez.

## Test Strategy
Unit: 75% — tablo ekleme çekirdek fonksiyonu (başlıklı/başlıksız happy
path, sütun uyuşmazlığı, bozuk kaynak).
Integration: 20% — orchestrator WORD_APPEND_TABLE step uygulaması,
rollback.
E2E: 5% — plan oluştur → uygula → sonuç dosyasını oku uçtan uca.

## Benchmark / Başarı Ölçütü
Coverage Target: 85%
Performance Target: yok
Memory: yok
Diğer ölçülebilir kriterler: pytest tüm testler yeşil.

## Kapsam Dışı
- **Word→PDF dönüştürme (LibreOffice tazelik doğrulama, timeout,
  kullanıcı-istediği-çıktı-adı) — TAMAMEN kapsam dışı, ayrı bir Saga
  task'a bırakıldı** (ortamda `soffice` kurulu değil).
- `plan_generation.py`/LLM prompt güncellemesi (doğal dilden tablo isteği
  çıkarma) — ayrı bir Saga task'a bırakıldı.
- Sıfırdan yeni `.docx` oluşturma — sadece VAR OLAN bir belgeye ekleme
  (EXCEL_CREATE'in kaynaksız deseni burada YOK).
- Tablo biçimlendirmesi (stil, renk, font) — sadece ham metin hücreleri.
- Birden fazla tablo aynı anda ekleme — tek çağrı, tek tablo.

## Etkilenen Dosyalar/Modüller (bilinen)
- `requirements.txt` — YENİ bağımlılık: `python-docx` (henüz projede yok,
  pip ile kurulabilir, LibreOffice'ten FARKLI olarak dış binary GEREKTİRMİYOR).
- `backend/models.py` — `OperationType.WORD_APPEND_TABLE`; `PlanStep`e
  `tableHeaders: list | None`, `tableRows: list`; `fileNames==1` zorunluluğu
  (EXCEL_APPEND/PDF APPEND deseni).
- Yeni bir modül gerekebilir (`backend/word_table.py`) — plan adımında
  kesinleştirilecek.
- `backend/orchestrator.py` — `_SUPPORTED_OPERATION_TYPES`,
  `_ROLLBACK_OPERATIONS` (`_rollback_append` — dosya-tipinden bağımsız,
  EXCEL_APPEND'de olduğu gibi DOĞRUDAN yeniden kullanılabilir), hedef-
  klasör-oluşturma hariç-tutma listesi, yeni step-uygulama bloğu.

## Rollback Beklentisi
EXCEL_APPEND/PDF APPEND ile AYNI `_rollback_append`/`_append_backup_path`
deseni (yerinde güncelleme, ayrı gizli yedek klasöründen geri kopyalama).

## Risks
- `python-docx` requirements.txt'e YENİ bir bağımlılık olarak eklenecek —
  proje genelinde başka hiçbir yerde kullanılmıyor, ilk kullanım. Kurulum
  adımı gerektirebilir (`pip install python-docx`), SETUP.md güncellemesi
  gerekebilir.
- `python-docx`'in tablo API'sinin (`document.add_table`, hücre erişimi)
  tam şekli plan/code-copilot adımında gerçek kurulumla doğrulanmalı
  (EXCEL_APPEND'de openpyxl API'si için yapılan doğrulamayla aynı
  disiplin).

## Assumptions
- `.docx` dosyasında zaten en az bir paragraf/tablo olsun olmasın, yeni
  tablo belgenin SONUNA eklenir (python-docx'in `document.add_table`
  varsayılan davranışı) — kullanıcı onaylamadı, en basit/beklenen
  davranış olarak varsayıldı.

## Unknowns
- `backend/word_table.py` gibi yeni bir modül mü gerekir yoksa mevcut
  bir dosyaya mı eklenir — plan adımında kesinleştirilmeli.
- `python-docx`'in gerçek API şekli (tablo oluşturma, hücre yazma) plan
  adımında gerçek kurulumla doğrulanmalı.

## Sorular ve Cevaplar (ham kayıt)
1. Kapsam (dönüştürme + tablo mu, sadece biri mi)? → Sadece tablo
   başlıkları — LibreOffice kurulu değil, dönüştürme ayrı task'a bırakıldı.
2. Slug onayı → "word-tablo-basligi" (onaylandı).
3. Operasyon tipi (append mi create mi)? → Var olan dosyaya EKLEME
   (EXCEL_APPEND deseni).
4. Headers verilmezse davranış? → Başlıksız tablo oluştur, hata YOK.
5. Bozuk kaynak davranışı? → Açık hata (proje konvansiyonuyla tek
   mantıklı seçenek, tekrar sorulmadı).
6. Sütun sayısı uyuşmazlığı? → Açık hata, tablo eklenmez.
7. Kabul kriteri + coverage + test oranı? → Otomatik test, %85, 75/20/5.
8. Kapsam dışı (plan_generation.py)? → Hayır, sadece backend modül +
   orchestrator + models.
9. Persona/hedef → task açıklamasından ve kapsam daraltma kararından
   türetildi.
