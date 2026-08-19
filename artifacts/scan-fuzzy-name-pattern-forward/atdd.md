---
task_slug: scan-fuzzy-name-pattern-forward
jira_id: null
saga_task_id: null
priority: low
coverage_target: 85
performance_target: null
memory_target: null
test_strategy:
  unit: 20
  integration: 80
  e2e: 0
affected_modules:
  - backend/main.py
---

# ATDD — scan-fuzzy-name-pattern-forward

## Jira Kaynağı
Jira'ya bağlı değil — yerel görev, Saga #316'nın red-team incelemesinde bulunan bir kapsam boşluğundan doğdu (task_c5e4c577)

## Persona
Muhasebeci — asenkron tarama akışını (`POST /api/search/scan`, Saga #337) kullanırken fuzzy/regex filtrelerini de kullanmak isteyen kullanıcı.

## Hedef (Neden)
Saga #316 (fuzzy/regex arama) sadece senkron `/api/search` endpoint'ine `fuzzyName`/`namePattern` desteği ekledi. Asenkron `/api/search/scan` (Saga #337) bu iki parametreyi `search_files()`'a hiç forward etmiyor — sessiz bir yetenek farkı: aynı `SearchRequest` şemasını kullanan iki endpoint'ten biri fuzzy/regex'i uyguluyor, diğeri sessizce yok sayıyor (hata vermeden). Bu task, asenkron akışı senkron akışla TUTARLI hale getiriyor.

## User Story
As a muhasebeci
I want /api/search/scan'i fuzzyName/namePattern ile çağırdığımda bunların gerçekten uygulanmasını
So that hangi endpoint'i (senkron/asenkron) kullandığıma bakılmaksızın aynı arama yeteneklerine erişebileyim

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. [Critical] Given `fuzzyName` ile `POST /api/search/scan` çağrılır, When tarama tamamlanır, Then `GET /api/search/scan/{scanId}` sonuçları `/api/search`'ün AYNI `fuzzyName` ile döndüreceği sonuçlarla BİREBİR aynıdır.
2. [Critical] Given `namePattern` ile `POST /api/search/scan` çağrılır, When tarama tamamlanır, Then sonuçlar `/api/search`'ün aynı `namePattern` ile döndüreceğiyle birebir aynıdır.
3. [High] Given geçersiz bir `namePattern` (bozuk regex) ile `POST /api/search/scan` çağrılır, When istek işlenir, Then `/api/search`'teki AYNI 422 davranışı uygulanır (tarama hiç başlatılmaz) — mevcut `/api/search`'ün `_parse_search_date` gibi erken-validasyon deseniyle tutarlı.
4. [High] Given `fuzzyName` VE `namePattern` AYNI istekte birlikte `/api/search/scan`'e verilir, When istek işlenir, Then `/api/search`'teki AYNI 422 davranışı uygulanır (tarama hiç başlatılmaz).

## Davranış Sözleşmesi (hangi durumda ne döner)
| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path (fuzzyName/namePattern ile scan tamamlanır) | `status: "done"` + doğru filtrelenmiş `results` | Yok | Sonuç listesi, senkron `/api/search` ile aynı | AC-1, AC-2 |
| 2 | Girdi geçersiz (bozuk regex) | `/api/search` ile BİREBİR aynı 422 (tarama başlatılmadan) | Yok, `_scans` kaydı hiç oluşmaz | Alan altı hata mesajı | AC-3 |
| 3 | Girdi geçersiz (iki mod birlikte) | `/api/search` ile BİREBİR aynı 422 | Yok, `_scans` kaydı hiç oluşmaz | Alan altı hata mesajı | AC-4 |

Bu task'ın davranış sözleşmesi tablosu kısa çünkü SIFIR yeni davranış icat etmiyor — `/api/search`'te zaten var olan davranışı `/api/search/scan`'e AYNEN yansıtıyor. Kısmi başarı/timeout/kaynak-yok gibi satırlar Saga #337'nin kendi ATDD'sinde zaten tanımlı ve bu task'ta değişmiyor, tekrar edilmiyor.

## Test Strategy
Integration: 80% — `/api/search/scan` + `/api/search`'ün AYNI filtrelerle AYNI sonucu döndürdüğünü doğrulayan karşılaştırmalı testler (bu bir "parity" testidir, yeni bir hesaplama mantığı test edilmiyor)
Unit: 20% — 422 erken-validasyonunun `start_search_scan`'de de tetiklendiğini doğrulayan testler
E2E: 0% — kapsam dışı

## Benchmark / Başarı Ölçütü
Coverage Target: 85%
Performance Target: Yok
Diğer ölçülebilir kriterler: `/api/search` ve `/api/search/scan` aynı filtrelerle çağrıldığında AYNI sonuç kümesini döndürür (parity garantisi).

## Kapsam Dışı
- Yeni bir arama yeteneği eklenmiyor — sadece mevcut senkron davranışın asenkron akışa taşınması.
- Frontend değişikliği yok.

## Etkilenen Dosyalar/Modüller (bilinen)
- `backend/main.py` — `start_search_scan()` ve `_run_scan()` fonksiyonlarına `fuzzyName`/`namePattern` parametrelerinin eklenmesi.

## Rollback Beklentisi
Salt-okunur bir özellik — rollback kavramı uygulanmıyor.

## Risks
Yok — kapsam çok dar, mevcut ve zaten test edilmiş bir davranışın kopyalanması.

## Assumptions
- `start_search_scan`'deki 422 validasyonu (regex/çelişki kontrolü), `search_endpoint`'teki AYNI kod yolunu (`_parse_search_date`'e benzer bir ortak yardımcı VEYA aynı satır içi mantığın tekrarı) kullanmalı — plan aşamasında hangisinin daha uygun olduğu netleştirilecek.

## Unknowns
Yok.

## Sorular ve Cevaplar (ham kayıt)
Bu task, Saga #316'nın red-team incelemesinde bulunan bir kapsam boşluğundan doğdu (spawn_task ile flag'lendi) — kapsamı zaten tam olarak tanımlıydı, kullanıcıya ayrıca soru sorulmadı (mevcut senkron endpoint'in davranışını birebir yansıtmak dışında bir karar noktası yoktu).
</content>
