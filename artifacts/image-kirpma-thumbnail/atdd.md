---
task_slug: image-kirpma-thumbnail
jira_id: null
saga_task_id: 329
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
---

# ATDD — image-kirpma-thumbnail

## Jira Kaynağı
Jira'ya bağlı değil — yerel görev. Kaynak: Saga #329 (epic #29 "Format Agent
Sistemi").

## Persona
windows-ai-files kullanıcısı (muhasebeci tipi) — bir görseli belirli bir
alana kırpmak veya küçük bir önizleme (thumbnail) üretmek isteyen kişi.
Görsel işleme epic için düşük öncelikli bir ihtiyaç.

## Hedef (Neden)
Eski projede (`core/agents/image_agent.py _crop/_thumbnail`) KRİTİK bir
veri kaybı sınıfı vardı: koordinat/boyut alanları GELMEDİĞİNDE sessizce
`(0,0,100,100)` gibi bir varsayılana düşülüyordu, ve çıktı dosya adı
varsayılanı KAYNAKLA AYNIYSA orijinal görsel yedeksiz ve geri dönüşsüz
şekilde küçük bir kareye düşürülüp `success:True` ile üzerine yazılıyordu.
Bu görüşmede kapsam netleştirildi: koordinatsız/boyutsuz bir istek AÇIK
HATA döndürmeli, VE çıktı HER ZAMAN yeni bir dosyaya yazılmalı (kaynak
asla değiştirilmez) — bu, "üzerine yazma" riskini mimari olarak imkânsız
kılar (varsayılana düşme sorununun yanı sıra).

## User Story
As a windows-ai-files kullanıcısı
I want bir görseli AÇIKÇA belirttiğim koordinatlarla kırpabilmek veya AÇIKÇA belirttiğim boyutta bir thumbnail üretebilmek
So that koordinat/boyut vermeyi unutursam sessiz bir varsayılana düşülüp orijinal görselim yedeksiz ezilmesin

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. [Critical] Given bir görsel ve `cropBox={x0:10,y0:10,x1:100,y1:100}`, When IMAGE_CROP çalıştırılır, Then `croppedFileName`'e TAM O ALANDA kırpılmış yeni bir görsel yazılır, kaynak değişmez.
2. [Critical] Given `cropBox` VERİLMEMİŞ (None/eksik), When IMAGE_CROP çalıştırılır, Then Pydantic validator reddi (plan hiç kabul edilmez) — sessiz varsayılana DÜŞÜLMEZ.
3. [High] Given `cropBox` geçersiz (`x1<=x0` veya `y1<=y0` veya negatif değer veya kaynak sınırlarını aşan alan), When IMAGE_CROP çalıştırılır, Then `PlanApplicationError`, hiçbir dosya yazılmaz.
4. [Critical] Given bir görsel ve `maxWidth=200, maxHeight=200`, When IMAGE_THUMBNAIL çalıştırılır, Then `thumbnailFileName`'e en-boy oranı KORUNARAK küçültülmüş yeni bir görsel yazılır (Pillow'un `thumbnail()` davranışı — verilen boyut üst sınır, esnetme YOK), kaynak değişmez.
5. [Critical] Given `maxWidth`/`maxHeight` VERİLMEMİŞ, When IMAGE_THUMBNAIL çalıştırılır, Then Pydantic validator reddi — sessiz varsayılana DÜŞÜLMEZ.
6. [High] Given `maxWidth`/`maxHeight` geçersiz (sıfır veya negatif), When IMAGE_THUMBNAIL çalıştırılır, Then `PlanApplicationError`, hiçbir dosya yazılmaz.
7. [High] Given kaynak görsel yok/bozuk (Pillow açamıyor), When IMAGE_CROP/IMAGE_THUMBNAIL çalıştırılır, Then `PlanApplicationError`, hiçbir dosya yazılmaz.

## Davranış Sözleşmesi (hangi durumda ne döner)
| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | IMAGE_CROP happy path | `operation.status="completed"` | `croppedFileName`'e yeni görsel yazılır, kaynak değişmez | Sonuç kartı | AC-1 |
| 2 | cropBox eksik (şema seviyesi) | Pydantic `ValueError` — plan hiç kabul edilmez | Yok | Plan onay ekranında doğrulama hatası | AC-2 |
| 3 | cropBox geçersiz geometri (çalışma zamanı) | `PlanApplicationError("IMAGE_CROP alanı geçersiz: ...")` | Hiçbir dosya yazılmaz | Hata mesajı | AC-3 |
| 4 | IMAGE_THUMBNAIL happy path | `operation.status="completed"` | `thumbnailFileName`'e yeni görsel yazılır, kaynak değişmez | Sonuç kartı | AC-4 |
| 5 | maxWidth/maxHeight eksik (şema seviyesi) | Pydantic `ValueError` | Yok | Plan onay ekranında doğrulama hatası | AC-5 |
| 6 | maxWidth/maxHeight geçersiz (çalışma zamanı) | `PlanApplicationError("IMAGE_THUMBNAIL boyutu geçersiz: ...")` | Hiçbir dosya yazılmaz | Hata mesajı | AC-6 |
| 7 | Kaynak yok/bozuk | `PlanApplicationError("... kaynağı okunamıyor: ...")` | Hiçbir dosya yazılmaz | Hata mesajı | AC-7 |
| 8 | **Kısmi başarı** (bir kısmı oldu, kalanı olmadı) | Uygulanmaz — tek dosya/tek atomik yazma (tempfile+atomik-replace deseni), ara durum fiziksel olarak oluşamaz | — | — | — |
| 9 | **Hiçbir şey yapılamadı ama hata da yok** | Uygulanmaz — bu, EPİK'İN önlemeye çalıştığı TAM OLARAK bu sınıf (eski projenin "sessiz varsayılana düş, success:True dön" bug'ı) — AC-2/AC-5 (şema seviyesi) ve AC-3/AC-6 (çalışma zamanı) BİRLİKTE bu durumun asla oluşamayacağını garanti ediyor: koordinat/boyut YOKSA plan hiç kabul edilmez, VARSA ama geçersizse çalışma zamanında reddedilir — üçüncü bir "sessizce bir şey yapmadan başarı dönme" yolu YOK | AC-2, AC-3, AC-5, AC-6 |

Boş sonuç ↔ hata ayrımı: bu operasyonlarda "boş ama geçerli sonuç" kavramı
YOK (EXCEL_FILTER'ın "0 satır eşleşti" durumunun burada bir karşılığı
yok) — her çağrı ya gerçek bir kırpılmış/küçültülmüş görsel üretir ya
hata fırlatır.

## Test Strategy
Unit: 75% — kırpma/thumbnail çekirdek fonksiyonları (happy path, geçersiz
geometri/boyut, bozuk kaynak).
Integration: 20% — orchestrator IMAGE_CROP/IMAGE_THUMBNAIL step
uygulamaları, Pydantic validator'ların GERÇEKTEN eksik alanı reddettiğinin
doğrulanması, rollback.
E2E: 5% — plan oluştur → uygula → sonuç dosyasını oku uçtan uca.

## Benchmark / Başarı Ölçütü
Coverage Target: 85%
Performance Target: yok
Memory: yok
Diğer ölçülebilir kriterler: pytest tüm testler yeşil.

## Kapsam Dışı
- `plan_generation.py`/LLM prompt güncellemesi — ayrı bir Saga task'a
  bırakıldı.
- Görsel formatı dönüştürme (ör. PNG→JPEG) — sadece kırpma/thumbnail,
  format kaynakla AYNI kalır.
- Döndürme/filigran/renk düzeltme gibi diğer görsel işlemleri — kapsam
  dışı.
- Thumbnail'de TAM boyuta zorlama (esnetme/kırpma) — sadece en-boy oranı
  korunan küçültme.

## Etkilenen Dosyalar/Modüller (bilinen)
- `backend/models.py` — `OperationType.IMAGE_CROP/IMAGE_THUMBNAIL`;
  `PlanStep`e `cropBox: dict | None` (veya ayrı x0/y0/x1/y1 alanları —
  `RedactionRegion`'ın modeli EMSAL alınabilir), `croppedFileName`,
  `maxWidth`, `maxHeight`, `thumbnailFileName`; ilgili validator'lar
  (EXCEL_FILTER'ın "==1 kaynak" deseni).
- Yeni bir modül gerekebilir (`backend/image_ops.py`).
- `backend/orchestrator.py` — `_SUPPORTED_OPERATION_TYPES`,
  `_ROLLBACK_OPERATIONS` (`_rollback_copy`), hedef-klasör-oluşturma
  hariç-tutma listesi, 2 yeni step-uygulama bloğu.
- `requirements.txt` — Pillow ZATEN mevcut (OCR/pdf2image için), yeni
  bağımlılık GEREKMİYOR.

## Rollback Beklentisi
SPLIT/EXCEL_FILTER ile aynı `_rollback_copy` deseni — kaynak asla
değişmediği için rollback sadece çıktı dosyasını siler.

## Risks
- `cropBox`'ın kaynak görselin GERÇEK piksel sınırlarını aşıp aşmadığı
  kontrolü — `RedactionRegion`'ın PDF sayfa sınırı kontrolüyle BENZER
  bir mantık (`pdf_redact.py`'deki epsilon toleranslı sınır kontrolü)
  code-copilot'ta referans alınabilir.
- Pillow'un `thumbnail()` metodunun TAM davranışı (in-place mi, yeni bir
  Image mi döndürür) plan/code-copilot adımında gerçek kurulumla
  doğrulanmalı.

## Assumptions
- `cropBox` şeması `RedactionRegion`'ın (x0,y0,x1,y1, PDF-nokta-uzayı
  DEĞİL, piksel uzayı) BENZER bir yapı taşır — kullanıcı onaylamadı,
  mimari tutarlılık gerekçesiyle önerildi, plan adımında kesinleştirilmeli.

## Unknowns
- `cropBox`'ın tam Pydantic şeması (ayrı x0/y0/x1/y1 alanları mı, iç içe
  bir `dict`/model mi) — plan adımında `RedactionRegion` emsaliyle
  netleştirilmeli.
- Pillow `thumbnail()` API'sinin tam davranışı — plan/code-copilot
  adımında gerçek kurulumla doğrulanmalı.

## Sorular ve Cevaplar (ham kayıt)
1. Slug onayı → "image-kirpma-thumbnail" (onaylandı).
2. Operasyon ayrımı? → İki ayrı operasyon (IMAGE_CROP/IMAGE_THUMBNAIL).
3. Çıktı modeli? → Yeni dosyaya yaz (kaynak asla değişmez).
4. Geçersiz koordinat/boyut davranışı? → Açık hata, PlanApplicationError.
5. Thumbnail oranı? → En-boy oranı korunur (Pillow'un doğal davranışı).
6. Kabul kriteri + coverage + test oranı? → Otomatik test, %85, 75/20/5.
7. Kapsam dışı (plan_generation.py)? → Hayır, sadece backend modül +
   orchestrator + models.
8. Persona/hedef → task açıklamasından türetildi.
9. Bozuk kaynak davranışı → proje konvansiyonuyla tek mantıklı seçenek
   (açık hata), tekrar sorulmadı.
