---
task_slug: dosya-arama-ilerleme-gostergesi
jira_id: null
saga_task_id: 337
priority: low
coverage_target: 85
performance_target: "POST /api/search/scan <10ms içinde scan_id döner"
memory_target: null
test_strategy:
  unit: 75
  integration: 20
  e2e: 5
affected_modules:
  - backend/main.py (yeni endpoint'ler)
  - backend/models.py (yeni şemalar)
  - backend/file_search.py (dokunulmaz, olduğu gibi kullanılır)
threat_model: done
---

# ATDD — dosya-arama-ilerleme-gostergesi

## Jira Kaynağı
Jira'ya bağlı değil — yerel görev (Saga #337, epic #27 "Dosya Arama", Saga #315'ten bölündü, #336'ya bağımlı)

## Persona
Muhasebeci — recursive arama (#336) ile artık çok seviyeli bir arşivde arama yapabilen, ama binlerce dosyalı büyük klasörlerde arayüzün "donduğunu" düşünüp tekrar tekrar tıklama riski taşıyan kullanıcı.

## Hedef (Neden)
Mevcut `/api/search` senkron — istemci cevap gelene kadar bekler (10sn'ye kadar sürebilir, #314/#336'nın timeout'u zaten var). Kullanıcı bu süre boyunca hiçbir ilerleme bilgisi görmüyor. Bu task, mevcut senkron `/api/search`'e DOKUNMADAN (geriye dönük uyumluluk, #334 SearchPanel bozulmaz), paralel bir asenkron akış (`/api/search/scan`) ekliyor — istemci isterse bunu kullanarak anlık `scan_id` alıp durumu polling'le takip edebilir.

## User Story
As a muhasebeci
I want büyük bir aramayı başlattığımda hemen bir onay alıp, tarama arka planda devam ederken durumunu sorgulayabilmek
So that arayüzün donduğunu düşünüp gereksiz yere tekrar denemeyeyim

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. [Critical] Given geçerli bir `sessionId` ve filtreler, When `POST /api/search/scan` çağrılır, Then 10ms içinde (gerçek tarama henüz bitmeden) bir `scan_id` ile 202/200 döner, tarama arka planda başlar.
2. [Critical] Given yeni başlatılmış bir `scan_id`, When `GET /api/search/scan/{scan_id}` hemen çağrılır, Then `status: "running"` + o ana kadar taranan dosya sayısı döner (henüz `results` yok).
3. [Critical] Given tarama tamamlanmış bir `scan_id`, When `GET /api/search/scan/{scan_id}` çağrılır, Then `status: "done"` + tam `results` listesi (+ varsa `partial: true`, #336'nın kendi 10sn timeout'undan miras) döner.
4. [High] Given var olmayan/hiç oluşturulmamış bir `scan_id`, When `GET /api/search/scan/{scan_id}` çağrılır, Then `status: "not_found"` ile 404 döner.
5. [High] Given aynı session'da art arda iki `POST /api/search/scan` çağrısı, When ikinci çağrı ilki hâlâ çalışırken yapılır, Then iki BAĞIMSIZ `scan_id` üretilir, ikisi de kendi taramasını tamamlar (biri diğerini iptal etmez/ezmez).
6. [High] Given `sessionId` geçersiz/eksik veya `allowed_root` artık mevcut değil, When `POST /api/search/scan` çağrılır, Then mevcut `/api/search`'teki 404/410 davranışı BİREBİR korunur (tarama hiç başlatılmaz).
7. [Medium] Given tamamlanmış bir `scan_id`, When tamamlanmasından 5 dakika sonra `GET /api/search/scan/{scan_id}` çağrılır, Then `status: "not_found"` döner (bellek temizlendi).

## Davranış Sözleşmesi (hangi durumda ne döner)
| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path (scan başlatılır) | 202 + {scanId: "..."} | Bellek-içi durum kaydı oluşur (`status: running`) | Anlık onay, tarama arka planda | AC-1 |
| 2 | Girdi geçersiz (sessionId eksik/geçersiz) | Mevcut `/api/search` ile BİREBİR aynı (404, session bulunamadı) | Yok, tarama başlamaz | Mevcut hata davranışı | AC-6 |
| 3 | Kaynak yok (allowed_root artık mevcut değil) | Mevcut `/api/search` ile BİREBİR aynı (410 Gone) | Yok, tarama başlamaz | "Seçili klasör artık mevcut değil" | AC-6 |
| 4 | Yetkisiz erişim | Uygulanmıyor — session-tabanlı erişim zaten #313/#314'te ele alınıyor, bu task yeni bir yetkilendirme katmanı eklemiyor. Silindi. | | | |
| 5 | Dış bağımlılık hatası | Uygulanmıyor — dış bağımlılık yok, saf dosya sistemi + bellek-içi state. Silindi. | | | |
| 6 | Zaman aşımı (scan_id bulunamıyor) | 404 + {status: "not_found"} | Yok | "Tarama bulunamadı" (süresi dolmuş VEYA hiç var olmamış — ikisi de aynı yanıt, çağıran ayırt edemez) | AC-4, AC-7 |
| 7 | Kısmi başarı (tarama #336'nın kendi 10sn timeout'una takıldı) | `status: "done"` + `results: [o ana kadar bulunanlar]` + `partial: true` | Yok | Kısmi sonuç listesi, partial bayrağı görünür | AC-3 (partial miras) |
| 8 | Hiçbir şey yapılamadı ama hata da yok (tarama bitti, 0 eşleşme) | `status: "done"` + `results: []` | Yok | Boş liste — "hata" değil "sonuç yok" | AC-3 (negatif durum) |

Kısmi başarı: Satır 7 — `search_files()`'ın kendi 10sn timeout'u (#336) tetiklenirse, arka plan taraması yine de `status: "done"` olarak işaretlenir (tarama SÜRECİ bitmiştir, sadece SONUÇ kısmi) — `running` durumunda asla takılı kalmaz, `done` + `partial:true` net bir son durumdur.
Hiçbir şey yapılamadı ama hata da yok: Filtrelere uyan dosya yoksa `status: "done"` + `results: []` döner — bu "hata" değil "sonuç yok" durumudur, `running`'de asla takılı kalmaz.
Boş sonuç ↔ hata ayrımı: `status: "done" + results: []` (eşleşme yok) ile `status: "not_found"` (scan_id hiç yok veya süresi dolmuş) NET ayrı durumlardır — ikisi de "boş" gibi görünebilir ama farklı HTTP status kodlarıyla (200 vs 404) ayrılır, çağıran asla karıştıramaz.

## Threat-Model Notu
STRIDE-lite geçişi: Bu task yeni bir background-task/bellek-içi-state yüzeyi
ekliyor — DoS ve Info Disclosure kategorileri değerlendirildi.
- **DoS**: Sınırsız sayıda `scan_id` oluşturulup bellek şişirilebilir mi?
  AC-7 (5 dakika sonra temizlik) bunu kısmen hafifletiyor ama scan
  BAŞLATMA hız sınırı bu task'ta YOK — kullanıcı kararı: tek kullanıcılı
  yerel masaüstü aracı (aynı `dosya-icerik-arama-encoding-timeout`
  ATDD'sindeki kabul edilen risk gerekçesiyle), rate-limiting bilinçli
  olarak kapsam dışı bırakılıyor, Risks'e yazıldı.
- **Info Disclosure**: `scan_id`'ler tahmin edilebilirse başka bir
  session'ın tarama sonucu sızabilir mi? `scan_id` `uuid4()` ile
  üretilecek (plan aşamasında netleştirilecek) — tahmin edilemez olmalı,
  bu bir AC-S olarak aşağıya eklendi.

**AC-S1 [High]**: Given `scan_id` üretimi, When bir scan başlatılır, Then `scan_id` kriptografik olarak tahmin edilemez olmalı (`uuid.uuid4()` veya eşdeğeri) — sıralı/artan bir sayaç KULLANILMAZ (aksi halde bir kullanıcı başka bir session'ın `scan_id`'sini tahmin edip sonuçlarını görebilir).

## Test Strategy
Unit: 75% — background task tetikleme mantığı, bellek-içi state geçişleri (running→done, not_found), 5dk temizlik mantığı, scan_id üretiminin tahmin edilemezliği
Integration: 20% — `POST /api/search/scan` + `GET /api/search/scan/{scan_id}`'nin birlikte çalışması (başlat→poll→sonuç al), mevcut `/api/search`'ün DEĞİŞMEDİĞİNİ doğrulayan regresyon testleri
E2E: 5% — mevcut e2e altyapısı yok, component/entegrasyon testine kayar

## Benchmark / Başarı Ölçütü
Coverage Target: 85%
Performance Target: `POST /api/search/scan` <10ms içinde `scan_id` döner (gerçek tarama beklenmeden)
Memory: Tamamlanan scan_id'ler 5 dakika sonra bellekten temizlenir (sınırsız büyüme önlenir)
Görsel/UI kriteri: Yok — bu task backend-only, frontend polling entegrasyonu (SearchPanel'in bunu kullanması) KAPSAM DIŞI, ayrı bir takip görevi.
Diğer ölçülebilir kriterler: Eşzamanlı iki scan_id birbirini etkilemeden tamamlanır (AC-5).

## Kapsam Dışı
- Mevcut `/api/search` (senkron) DEĞİŞMİYOR — SearchPanel (#334) bu task'ta güncellenmiyor, hâlâ senkron endpoint'i kullanmaya devam ediyor.
- Frontend'in yeni asenkron endpoint'i kullanacak şekilde güncellenmesi — ayrı bir takip görevi olarak açılmalı (bu ATDD'de yok).
- Rate-limiting / scan başlatma sıklığı sınırı — kabul edilen risk (tek kullanıcılı yerel araç).
- Kalıcı (DB) durum saklama — bellek-içi, backend restart'ta tüm scan_id'ler kaybolur (kullanıcı kararı).

## Etkilenen Dosyalar/Modüller (bilinen)
- `backend/main.py` — `POST /api/search/scan`, `GET /api/search/scan/{scan_id}` yeni endpoint'ler.
- `backend/models.py` — `ScanStartResponse` (scanId), `ScanStatusResponse` (status, taranan sayısı, results, partial) yeni şemalar.
- `backend/file_search.py` — DOKUNULMAZ, `search_files()` olduğu gibi arka plan task'ından çağrılır.

## Rollback Beklentisi
Salt-okunur bir özellik (dosya sistemi üzerinde yazma yapmıyor, bellek-içi geçici state dışında kalıcı durum değişikliği yok) — rollback kavramı uygulanmıyor.

## Risks
- Rate-limiting yok — kabul edilen risk (Threat-Model Notu'nda gerekçeli).
- Bellek-içi state, mevcut `_sessions` sözlüğü deseniyle (backend/main.py) tutarlı ama thread-safety netleştirilmeli — arka plan taraması ile ana event loop'un aynı dict'e eriştiği durumda kilitleme/eşzamanlılık stratejisi plan aşamasında belirlenmeli.
- FastAPI'de blocking bir fonksiyonu (`search_files()`, CPU+IO ağırlıklı) arka planda çalıştırmanın doğru mekanizması (`BackgroundTasks` vs `asyncio.to_thread` vs `run_in_executor`) plan aşamasında netleştirilmeli — yanlış seçilirse event loop bloke olup TÜM backend'i (diğer session'ların istekleri dahil) donmasına yol açabilir.

## Assumptions
- `scan_id` `uuid.uuid4()` ile üretilir (AC-S1'in gereği, kullanıcıya ayrıca sorulmadı ama threat-model'in doğal sonucu).

## Unknowns
- Arka plan çalıştırma mekanizmasının kesin seçimi (threading/asyncio) — plan aşamasında kod tabanına bakılarak netleştirilecek.

## Sorular ve Cevaplar (ham kayıt)
1. Arama nasıl çalışmalı? → Asenkron: scan_id + polling
2. İlerleme durumu nerede tutulsun? → Bellek-içi (in-memory dict)
3. Eşzamanlı taramalar birbirini nasıl ezmesin? → Her scan_id bağımsız, iptal yok
4. Polling durum şekli ne olsun? → status: running/done/not_found + sayı + sonuç
5. Mevcut /api/search ne olsun? → Aynen kalsın, yeni /api/search/scan eklensin
6. Yeni endpoint adı ne olsun? → POST /api/search/scan + GET /api/search/scan/{scan_id}
7. Eski scan_id'ler temizlensin mi? → Evet, 5 dakika sonra
8. Benchmark ne olsun? → <10ms'de scan_id, polling doğru sonucu verir
9. Test stratejisi oranı? → 75/20/5
</content>
