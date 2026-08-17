---
task_slug: pdf-siralama-istek-normalizasyonu
priority: high
coverage_target: "AC'lerin tamamı unit/integration test ile kapsanır"
performance_target: "yok (basit string normalizasyonu, ölçülebilir performans hedefi yok)"
test_strategy: "80/20/0 (unit/integration) — mevcut pytest + FastAPI TestClient altyapısı"
affected_modules: ["backend/models.py", "backend/request_normalization.py"]
---

# PDF sıralama isteğini Entry katmanında normalize et ve oturum klasörüyle bağla (Saga #268)

## Persona
"Bu klasördeki PDF'leri tarihe göre sırala" gibi bir istek yazan kullanıcı.

## Goal
İstek metni trimlenmeli, oturumun seçtiği klasör bağlama eklenmeli ve
boş/geçersiz girdi reddedilmelidir. Kullanıcı metni doğrudan dosya sistemi
aracına aktarılmamalıdır (normalize edilmeden herhangi bir dosya
operasyonu bileşenine geçmemeli).

## User Story
Bir kullanıcı olarak, isteğimi yazarken baştaki/sondaki boşlukların veya
yanlışlıkla boş bir istek göndermenin sisteme zarar vermeyeceğinden emin
olmak istiyorum; sistem de benim isteğimi hangi klasörde çalıştığımla
birlikte tutmalı.

## Acceptance Criteria (öncelik sırasına göre)
1. `/api/session` endpoint'ine gönderilen `requestText`, saklanmadan/
   döndürülmeden ÖNCE trim edilir (baştaki/sondaki boşluklar temizlenir)
   — mevcut kodda sadece "boş mu" kontrolü vardı, gerçek trim YOKTU (bug).
2. Trim SONRASI boş kalan (`"   "` gibi) istek 422 ile reddedilir (mevcut
   davranış korunur).
3. `selectedFolder` boş/whitespace-only ise 422 ile reddedilir (mevcut
   davranış korunur).
4. Oluşturulan `SessionContext`, normalize edilmiş `requestText`'i
   `selectedFolder` ile birlikte taşır (bağlama zaten `SessionContext`
   yapısında var — bu task sadece trim eksikliğini kapatıyor).
5. Yeniden kullanılabilir bir `normalize_request_text(text: str) -> str`
   saf fonksiyonu eklenir — gelecekteki plan-üretim katmanı (Saga #269)
   ham kullanıcı metnini DEĞİL, bu fonksiyonun çıktısını kullanmalı
   (kullanıcı metninin doğrudan bir dosya sistemi aracına aktarılmaması
   ilkesi, bu fonksiyonun varlığıyla somutlaştırılıyor).

## Behaviour-contract tablosu
| Girdi | Beklenen sonuç |
|---|---|
| `requestText = "  PDF'leri sırala  "` | 201, `requestText == "PDF'leri sırala"` (trim edilmiş) |
| `requestText = "   "` | 422 |
| `requestText = ""` | 422 |
| `selectedFolder = ""` veya `"   "` | 422 |
| Geçerli, trim gerektirmeyen istek | 201, davranış değişmez (regresyon yok) |

## Risks/Assumptions/Unknowns
- Assumption: `normalize_request_text` bu task'ta backend/request_normalization.py
  adlı YENİ bir modülde tanımlanıyor — `models.py`'nin pydantic validator'ı
  bu fonksiyonu çağırır, böylece mantık tek bir yerde test edilebilir ve
  Saga #269 (plan üretimi) doğrudan import edip kullanabilir. (saga-oto
  tarafından otomatik seçildi)
- Assumption: Bu task, gerçek bir dosya sistemi taraması/PDF metadata
  okuma İÇERMİYOR — sadece Entry (istek) katmanı. Dosya sistemi erişimi
  Saga #269/#270 kapsamında. (saga-oto tarafından otomatik seçildi — dar
  kapsam ilkesi)
- Risk: Mevcut `not_blank` validator zaten boş girdiyi reddediyordu ama
  DEĞERİ TRIM ETMİYORDU (`return value` — orijinal, trim edilmemiş).
  Bu, gerçek bir bug'dı (task açıklamasının "trimlenmeli" AC'siyle
  doğrudan çelişiyordu) — bu task kapsamında düzeltiliyor.

## Test Strategy
80/20/0 unit/integration. `backend/tests/test_request_normalization.py`
(yeni, saf fonksiyon) + `backend/tests/test_main_integration.py`'e trim
davranışını doğrulayan yeni entegrasyon testleri.

## Benchmark
Kabul kriteri: `python -m pytest backend/ -q` içinde tüm testler yeşil.

## Sorular ve Cevaplar (saga-oto otomatik)
- S: Normalizasyon mantığı nerede yaşamalı — doğrudan pydantic validator
  içinde mi, ayrı bir modülde mi? C: Ayrı bir modülde (`request_normalization.py`)
  — Saga #269'un plan üretim katmanı bu fonksiyonu doğrudan import edip
  kullanabilsin diye, tek bir kaynak doğruluk noktası. (saga-oto
  tarafından otomatik seçildi)
- S: Bu task dosya sistemi/PDF metadata işine giriyor mu? C: Hayır — dar
  kapsam, sadece istek metni normalizasyonu + oturum bağlama. (saga-oto
  tarafından otomatik seçildi)
