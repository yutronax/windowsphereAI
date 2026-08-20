---
task_slug: pdf-pii-tespiti
jira_id: null
saga_task_id: 333
priority: low
coverage_target: 90
performance_target: null
memory_target: null
test_strategy:
  unit: 85
  integration: 15
  e2e: 0
affected_modules:
  - backend/pdf_pii.py
  - backend/main.py
  - backend/models.py
  - backend/tests/test_pdf_pii.py
threat_model: done
---

# ATDD — pdf-pii-tespiti

## Jira Kaynağı
Jira'ya bağlı değil — yerel görev (Saga #333, epic #29 altında).

## Persona
Format Agent Sistemi kullanıcısı — bir PDF'i redakte etmeden önce hangi
bölgelerin KVKK kapsamındaki hassas veri (TC kimlik no, IBAN/hesap no)
içerdiğini elle bulmak yerine sistemin önermesini isteyen kişi. Ayrıca
LLM/plan üreten taraf — önerilen bölgeleri doğrudan mevcut REDACT
operasyonuna geçirebilir.

## Hedef (Neden)
Saga #320'nin `RedactionRegion`/`redact_pdf_page`/REDACT operationType'ı
zaten çalışıyor ama kullanıcının/LLM'in redaksiyon bölgesini (sayfa +
koordinat) ELLE belirtmesini gerektiriyor. Bu görev PDF metnini tarayıp
TC kimlik no / IBAN gibi KVKK kapsamındaki kalıpları regex+checksum ile
bulup, mevcut `RedactionRegion` modeliyle BİREBİR uyumlu bir bölge listesi
öneren yeni bir katman ekliyor — REDACT'ın kendisini değiştirmiyor.

## User Story
As a Format Agent Sistemi kullanıcısı
I want bir PDF'teki TC kimlik no/IBAN gibi hassas verilerin konumunu
otomatik olarak bulmak
So that redaksiyon bölgesini elle koordinat vererek belirtmek zorunda
kalmayayım

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. [Critical] Given metin katmanlı bir PDF (allowed_root içinde, mevcut
   whitelist'ten geçmiş), When `POST /api/pdf/detect-pii` çağrılır, Then
   PDF'in metin içeriği taranır, resmi TC kimlik no checksum algoritmasını
   geçen 11 haneli dizeler VE `TR` ile başlayan 26 karakterlik IBAN
   kalıpları bulunur, her biri için `RedactionRegion(page, x0, y0, x1, y1)`
   listesi (PDF nokta-uzayı, sol-alt kökenli — `RedactionRegion`'ın kendi
   sözleşmesiyle birebir) döner.
2. [Critical] Given PDF'te hiçbir PII kalıbı bulunamazsa, When endpoint
   çağrılır, Then `200 + boş liste` döner — bu bir hata DEĞİL, geçerli bir
   "temiz PDF" sonucudur.
3. [High] Given 11 haneli bir sayı dizesi checksum'ı GEÇMİYORSA (gerçek
   bir TC kimlik no formatına uymuyor), When taranır, Then bu dize PII
   olarak İŞARETLENMEZ (yanlış-pozitif önleme).
4. [High] Given PDF dosyası bozuk/açılamıyor VEYA `allowed_root` dışında,
   When endpoint çağrılır, Then sırasıyla `PlanApplicationError`/
   `PathWhitelistError` ile TUTARLI bir hata döner (mevcut whitelist
   mekanizması, Saga #338'in genelleştirmesiyle bu endpoint de kapsanır —
   plan aşamasında `_DESTINATION_FIELD_BY_OPERATION`'a değil, ayrı bir
   path-whitelist kontrolüne ihtiyaç olup olmadığı netleştirilecek çünkü
   bu bir Plan/apply_plan operasyonu DEĞİL, salt-okunur bir sorgu).
5. [Medium] Given bulunan bir PII eşleşmesi sayfa sınırının dışına
   taşıyor/geçersiz bir bounding box üretiyorsa, When bölge hesaplanır,
   Then bu eşleşme atlanır (listeye eklenmez) — geçersiz bir
   `RedactionRegion` asla döndürülmez.
6. [Critical] [AC-S1] Given PDF'te 1+ PII eşleşmesi bulunur, When
   `/api/pdf/detect-pii` yanıtı üretilir, Then yanıt SADECE
   `RedactionRegion(page, x0, y0, x1, y1)` alanlarını içerir — eşleşen
   ham TC kimlik no/IBAN DEĞERİ (ör. "12345678901") yanıtın HİÇBİR
   alanında, log satırında veya hata mesajında YER ALMAZ (saldırganın
   somut girdisi: ağ trafiğini/logları izleyen biri; gözlenebilir sonuç:
   response body'de/`backend`'in ürettiği hiçbir log satırında 11 haneli
   TC-kimlik-benzeri veya `TR`+24-hane IBAN-benzeri bir dize BULUNMAZ).
7. [High] [AC-S2] Given PDF metni çok uzun/binlerce sayfa (kötü niyetli
   veya kazara), When regex taraması çalışır, Then TC kimlik no ve IBAN
   kalıpları SABİT uzunluklu quantifier'lar (`\d{11}`, `TR\d{24}` — iç içe
   açık-uçlu `+`/`*` YOK) kullanır, böylece regex çalışma süresi metin
   uzunluğuyla DOĞRUSAL kalır (ReDoS/katastrofik geri-izleme riski yok).

## Davranış Sözleşmesi (hangi durumda ne döner)
| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path: PDF'te 1+ geçerli TC kimlik no/IBAN var | `200 + [RedactionRegion, ...]` | Yok — salt okunur, dosyaya dokunulmaz | Önerilen bölge listesi | AC-1 |
| 2 | Girdi geçersiz: dosya adı whitelist dışı | `PathWhitelistError` (mevcut mekanizma) | Yok | Yapılandırılmış whitelist hatası | AC-4 |
| 3 | Kaynak yok: PDF bulunamıyor/bozuk | Hata (pypdf'in exception'ı, endpoint'te 4xx'e çevrilir) | Yok | "PDF okunamadı" mesajı | AC-4 |
| 4 | Yetkisiz erişim | Uygulanmıyor — tek kullanıcılı masaüstü uygulaması, whitelist zaten AC-4'te kapsanıyor. | — | — | — |
| 5 | Dış bağımlılık hatası (ağ/DB/API) | Uygulanmıyor — salt yerel pypdf metin çıkarma, dış bağımlılık yok. | — | — | — |
| 6 | Zaman aşımı | Uygulanmıyor — bu görevde OCR kapsam dışı (kullanıcı onayı), pypdf metin çıkarma senkron ve hızlı, ayrı bir timeout mekanizması gerekmiyor. | — | — | — |
| 7 | **Kısmi başarı**: bazı eşleşmeler geçerli bölge üretiyor, bazıları (sayfa sınırı dışı) geçersiz | Geçerli olanlar listede, geçersiz olanlar SESSİZCE ATLANIR (hata değil) | Yok | Kısmi bir liste (sadece geçerli bölgeler) | AC-5 |
| 8 | **Hiçbir şey yapılamadı ama hata da yok** | PII bulunamazsa `200 + []` zaten AC-2'nin kendisi — bu "sessiz başarı" DEĞİL, çünkü boş liste dürüst bir sonuç (gerçekten PII yok), sessizce BAŞARISIZ olup da başarı iddia eden bir dal YOK (PDF okunamazsa AC-4/satır-3'e düşer, hata döner). | — | — | AC-2 |

Kısmi başarı: 7. satırda tanımlı — geçersiz bounding box üreten eşleşmeler
sessizce atlanır, bu davranışsal bir tasarım kararı (kullanıcı onayı),
hata değil.
Hiçbir şey yapılamadı ama hata da yok: Olanaksız/ayrımlı — "PDF okundu ama
PII yok" (AC-2, dürüst boş sonuç) ile "PDF okunamadı" (satır 3, hata) AÇIKÇA
farklı yollardır, aynı değeri dönmezler.
Boş sonuç ↔ hata ayrımı: `200 + []` (temiz PDF) ile PDF okunamadığında
dönen hata (4xx) KESİN olarak ayrılır — asla aynı koda/değere düşmezler.

## Test Strategy
Unit: 85% — regex kalıpları (TC kimlik no formatı), TC checksum algoritması
(bilinen geçerli/geçersiz TC kimlik no örnekleriyle), koordinat-hesaplama
mantığı (pypdf `visitor_text` callback'inden bounding box üretimi) mock'lu/
küçük PDF fixture'larla test edilir.
Integration: 15% — gerçek bir PDF (pypdf ile oluşturulmuş, içine bilinen
TC kimlik no/IBAN örnekleri yazılmış) ile endpoint'in uçtan uca doğru
`RedactionRegion` listesi ürettiği doğrulanır.
E2E: 0% — backend-only, yeni bir UI eklenmiyor (kullanıcı onayı).

## Benchmark / Başarı Ölçütü
Coverage Target: 90%.
Diğer ölçülebilir kriterler:
- Bilinen geçerli TC kimlik no örnekleriyle (resmi algoritmaya uyan)
  %100 doğru tespit.
- Bilinen geçersiz (checksum'ı geçmeyen 11 haneli rastgele sayılar)
  örneklerle sıfır yanlış-pozitif.
- Geçerli IBAN formatı (`TR` + 24 rakam) örnekleriyle %100 doğru tespit.

## Kapsam Dışı
- Taranmış/OCR gereken PDF'ler (metin katmanı olmayan) — sadece metin
  katmanlı PDF kapsanıyor, boş liste döner (kullanıcı onayı, epic
  açıklamasındaki "doğal uzantı" bu görevin parçası değil).
- Vergi no, telefon no gibi checksum'suz/daha geniş kalıplar — sadece
  TC kimlik no + IBAN (kullanıcı onayı, yanlış-pozitif riski).
- `plan_generation.py`'nin LLM prompt'una entegrasyon — bu görev sadece
  bağımsız bir endpoint ekliyor, LLM'in bunu otomatik çağırması ayrı bir
  görev (kullanıcı onayı).
- Bulunan bölgelerin OTOMATİK olarak REDACT edilmesi — bu görev sadece
  ÖNERİ üretiyor, kullanıcı/LLM hâlâ REDACT operasyonunu ayrıca
  tetiklemeli (mevcut akış değişmiyor).

## Etkilenen Dosyalar/Modüller (bilinen)
- `backend/pdf_pii.py` (yeni — regex/checksum/koordinat mantığı)
- `backend/main.py` (yeni `/api/pdf/detect-pii` endpoint'i)
- `backend/models.py` (muhtemelen yeni bir response şeması, `RedactionRegion`
  zaten mevcut, değişmeyecek)
- `backend/tests/test_pdf_pii.py` (yeni)

## Rollback Beklentisi
Uygulanmıyor — bu salt-okunur bir sorgu endpoint'i, hiçbir dosya
değişikliği yapmıyor (PDF'i okur, yazmaz). Hata durumunda hiçbir kalıcı
etki olmaz.

## Threat Model (STRIDE-lite)
Varlık: PDF içindeki hassas kişisel veri (TC kimlik no, IBAN) VE bu
verinin sistemin ÜRETTİĞİ yeni bir çıktıda (API yanıtı, log) tekrar
belirmesi. Güven sınırı: frontend (Tauri penceresi/tarayıcı) → yerel
FastAPI backend.

- **Information disclosure** (asıl tehdit) — endpoint "PII bulundu" derken
  ham değeri de response'a koyabilirdi, bu PII'yi YENİ bir yerde (API
  yanıtı, olası log/telemetri) tekrar ifşa eder → **AC-S1** ile kapatıldı
  (sadece koordinat döner, değer asla).
- **Denial of Service** — kötü/kazara çok uzun metinli bir PDF, açık-uçlu
  regex kalıplarıyla ReDoS'a yol açabilir → **AC-S2** ile kapatıldı (sabit
  uzunluklu kalıplar).
- **Tampering** — dosya adı whitelist'ten geçmeli, bu zaten AC-4'te var
  (mevcut `PathWhitelistError` mekanizmasına dayanıyor, tekrar
  üretilmiyor).
- **Spoofing** — Uygulanmıyor, kimlik doğrulama/oturum bu görevin
  kapsamında değil (tek kullanıcılı masaüstü aracı, önceki görevlerle
  tutarlı kabul edilen risk).
- **Repudiation** — Uygulanmıyor, salt-okunur bir sorgu, denetim izi
  gereksinimi yok (tek kullanıcılı yerel araç).
- **Elevation** — Uygulanmıyor, bu görevde ayrı bir yetki sınırı yok.

## Risks
- pypdf'in `visitor_text` callback'i her PDF üreticisinde (Word→PDF,
  tarayıcı, farklı yazı tipleri) tutarlı transform matrisi vermeyebilir —
  bounding box hesaplaması plan aşamasında gerçek bir örnekle
  doğrulanmalı.
- `RedactionRegion`'ın koordinat sözleşmesi (PDF nokta-uzayı, sol-alt
  kökenli) ile pypdf'in `visitor_text`'inin verdiği transform matrisinin
  UYUMLU olduğu varsayılıyor — plan aşamasında `backend/pdf_redact.py`'nin
  mevcut testleriyle çapraz kontrol edilmeli.
- TC kimlik no checksum algoritması yanlış implemente edilirse (resmi
  algoritma: 10. hane ve 11. hane için ayrı formüller) hem yanlış-pozitif
  hem yanlış-negatif riski var — bilinen doğru/yanlış örneklerle test
  edilmesi zorunlu (bu zaten Test Strategy'de var).

## Assumptions
- Endpoint'in dosya adını nasıl alacağı (query param, body) plan
  aşamasında mevcut `/api/` endpoint'lerinin konvansiyonuna göre
  netleştirilecek — `backend/main.py`'deki benzer bir salt-okunur
  endpoint'in (varsa) deseni takip edilecek.

## Unknowns
- Whitelist kontrolünün bu endpoint için TAM olarak nasıl uygulanacağı
  (AC-4'te not edildi) — plan aşamasında netleştirilecek.

## Sorular ve Cevaplar (ham kayıt)
1. Çıktı şekli? → Yeni endpoint, RedactionRegion listesi döner (plan_generation
   entegrasyonu değil).
2. PII kalıpları? → TC kimlik no + IBAN (vergi no/telefon sonraki sürüme).
3. OCR/taranmış PDF? → Kapsam dışı, sadece metin katmanlı.
4. Koordinat yöntemi? → pypdf'in visitor_text callback'i (yeni bağımlılık yok).
5. TC checksum? → Evet, resmi algoritma uygulanmalı.
6. Benchmark? → Bilinen örneklerle %100 doğru + sıfır yanlış-pozitif.
7. Boş sonuç? → 200 + boş liste (hata değil).
8. Test stratejisi? → unit %85 / integration %15 / e2e %0.
9. Persona/Hedef/Happy path/Bağımlılıklar → Saga #333 görev açıklamasından
   (kullanıcı mesajından, tekrar sorulmadı).
