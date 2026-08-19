---
task_slug: dosya-arama-fuzzy-regex
jira_id: null
saga_task_id: 316
priority: low
coverage_target: 85
performance_target: null
memory_target: null
test_strategy:
  unit: 80
  integration: 15
  e2e: 5
affected_modules:
  - backend/file_search.py
  - backend/models.py
  - backend/main.py
threat_model: done
---

# ATDD — dosya-arama-fuzzy-regex

## Jira Kaynağı
Jira'ya bağlı değil — yerel görev (Saga #316, epic #27 "Dosya Arama")

## Persona
Muhasebeci — dosya adını tam hatırlamayan (örn. "fatura" mı "fatuura" mı yazmıştı) veya belirli bir desene uyan dosyaları (örn. "2024-*-fatura") arayan kullanıcı.

## Hedef (Neden)
Mevcut `name_contains` filtresi (Saga #313) sadece düz substring eşleşmesi yapıyor — kullanıcı dosya adını yanlış hatırlarsa veya desenli bir arama yapmak isterse hiç sonuç bulamıyor. Bu task iki bağımsız yetenek ekliyor: bulanık (fuzzy) isim eşleşmesi ve regex desen araması.

## User Story
As a muhasebeci
I want dosya adını tam hatırlamadığımda bulanık eşleşmeyle veya desenli bir regex ile arayabilmek
So that küçük yazım farkları veya karmaşık adlandırma kalıpları arama sonucunu kaçırmasın

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. [Critical] Given `allowed_root`'ta "fatura_2024.pdf" adlı bir dosya, When `fuzzy_name="fatuura_2024"` (Levenshtein mesafesi ≤2) ile arama yapılır, Then dosya sonuç listesinde görünür.
2. [Critical] Given `allowed_root`'ta "2024-01-fatura.pdf" ve "rapor.pdf" dosyaları, When `name_pattern="2024-.*-fatura"` (regex) ile arama yapılır, Then sadece "2024-01-fatura.pdf" sonuçta görünür.
3. [Critical] Given geçersiz bir regex deseni (örn. `"("` eşlenmemiş parantez), When `name_pattern` ile arama yapılır, Then 422 Unprocessable Entity döner, hata fırlatılmaz (500 değil).
4. [High] Given `fuzzy_name` VE `name_pattern` AYNI istekte birlikte verilir, When arama yapılır, Then 422 döner (birbirini dışlayan iki mod, çelişkili girdi erken reddedilir).
5. [High] Given Levenshtein mesafesi 3+ olan bir dosya adı (örn. "fatura" ile "invoice"), When `fuzzy_name="fatura"` ile arama yapılır, Then o dosya sonuçta GÖRÜNMEZ (eşik dışı).
6. [Medium] Given `fuzzy_name`/`name_pattern` ile birlikte `extension`/`modifiedAfter`/`modifiedBefore` filtreleri, When arama yapılır, Then tümü AND mantığıyla birleşir (mevcut #313/#314 davranışıyla tutarlı).
7. [Medium] Given `allowed_root`'un alt klasöründeki bir dosya (2. seviye), When `fuzzy_name`/`name_pattern` ile arama yapılır, Then o dosya sonuçta GÖRÜNMEZ (bilinçli kapsam kararı: sadece kök dizin, non-recursive — #336'nın recursive değişikliğinden BAĞIMSIZ).

## Davranış Sözleşmesi (hangi durumda ne döner)
| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path (fuzzy veya regex eşleşme bulunur) | 200 + SearchResponse{results: [...]} | Yok (salt-okunur) | Eşleşen dosya listesi | AC-1, AC-2 |
| 2 | Girdi geçersiz (bozuk regex) | 422 + {detail: "name_pattern geçersiz regex: '...'"} | Yok | Alan altı hata mesajı | AC-3 |
| 3 | Girdi geçersiz (fuzzy_name + name_pattern birlikte) | 422 + {detail: "fuzzy_name ve name_pattern aynı anda kullanılamaz"} | Yok | Alan altı hata mesajı | AC-4 |
| 4 | Kaynak yok (allowed_root artık mevcut değil) | 410 Gone (mevcut davranış, değişmiyor) | Yok | "Seçili klasör artık mevcut değil" | — (313'ten miras) |
| 5 | Yetkisiz erişim | Uygulanmıyor — session-tabanlı erişim zaten #313'te ele alınıyor, bu task yeni bir yetkilendirme katmanı eklemiyor. Silindi. | | | |
| 6 | Dış bağımlılık hatası | Uygulanmıyor — dış bağımlılık yok, saf string/regex hesaplaması. Silindi. | | | |
| 7 | Zaman aşımı | Uygulanmıyor — bu task non-recursive (kök dizin sığ tarama), #314/#336'nın 10sn timeout'u zaten VAR olan davranış, fuzzy/regex bunu değiştirmiyor, ayrı bir timeout senaryosu eklenmiyor. Silindi. | | | |
| 8 | Hiçbir şey yapılamadı ama hata da yok (eşik dışı, 0 sonuç) | 200 + SearchResponse{results: []} | Yok | Boş liste — "hata" değil "sonuç yok" | AC-5 (negatif durum) |

Kısmi başarı: Uygulanmıyor — fuzzy_name/name_pattern tek bir filtre katmanı, AND zincirine (satır 6) eklenir, "yarım" bir eşleşme durumu yok (bir dosya ya eşleşir ya eşleşmez). Silindi.
Hiçbir şey yapılamadı ama hata da yok: Eşik dışı/desene uymayan durumda `results: []` ile 200 döner — normal "sonuç yok" durumu.
Boş sonuç ↔ hata ayrımı: Boş sonuç (`200 + []`) = eşleşme yok. Regex hatası (`422`) = desen sözdizimi bozuk. Çelişkili girdi (`422`) = iki mod birlikte verildi. Klasör yok (`410`) = allowed_root artık mevcut değil. Dördü farklı durumlarla ayrılır, karışmaz.

## Threat-Model Notu
STRIDE-lite geçişi: Bu task kullanıcı girdisini (regex deseni) doğrudan
`re.compile()`'a geçiriyor — DoS kategorisi (ReDoS: kötü niyetli/karmaşık
bir regex deseni catastrophic backtracking ile CPU'yu kilitleyebilir)
değerlendirildi.

**AC-S1 [High]**: Given kötü niyetli bir ReDoS deseni (örn. `"(a+)+$"` gibi
catastrophic backtracking'e yol açan bir regex), When `name_pattern` ile
arama yapılır, Then arama makul bir sürede (mevcut dosya-adı uzunlukları
için, örn. birkaç yüz karakter) tamamlanmalı veya bir üst sınır (regex
çalıştırma zaman aşımı) olmalı — sınırsız CPU tüketimi kabul edilemez.

Kabul edilen risk: `re` modülünün Python'daki standart implementasyonu
zaten regex çalıştırma süresini SINIRLAYAN bir mekanizma sunmuyor (üçüncü
parti `regex` kütüphanesi timeout destekler ama bu task'ta yeni bağımlılık
EKLENMİYOR — kullanıcı fuzzy için de "bağımlılık gerektirmeyen" tercih
etti). Bu nedenle AC-S1 TAM bir timeout garantisi DEĞİL, dosya adlarının
(genelde <260 karakter, işletim sistemi sınırı) doğal olarak kısa olması
nedeniyle pratik risk düşük kabul ediliyor — bilinçli risk, Risks'e yazıldı.

## Test Strategy
Unit: 80% — Levenshtein mesafesi hesaplama, regex derleme+eşleştirme, geçersiz regex reddi, iki-mod-çelişkisi reddi
Integration: 15% — `/api/search` endpoint'inin fuzzy_name/name_pattern ile diğer filtrelerle AND kombinasyonu
E2E: 5% — mevcut e2e altyapısı yok, component/entegrasyon testine kayar

## Benchmark / Başarı Ölçütü
Coverage Target: 85%
Performance Target: Yok (non-recursive, kök dizin sığ tarama — performans riski düşük)
Memory: Belirtilmedi
Görsel/UI kriteri: Yok — backend-only, frontend değişikliği yok
Diğer ölçülebilir kriterler: Levenshtein ≤2 eşleşen dosyalar bulunur, geçersiz regex 422 döner, iki mod birlikte 422 döner.

## Kapsam Dışı
- `content_contains` (#314) ile fuzzy/regex birleşimi — sadece dosya ADI filtreleri, içerik araması bu task'ta etkilenmiyor.
- Frontend (SearchPanel, #334) güncellemesi — backend-only, ayrı bir takip görevi gerekir.
- Recursive fuzzy/regex arama — bilinçli olarak sadece kök dizin (görev tanımının kendi kararı, #336'nın recursive değişikliğinden bağımsız).
- Regex çalıştırma süresi için gerçek bir timeout mekanizması (üçüncü parti kütüphane) — kabul edilen risk, Threat-Model Notu'nda gerekçeli.

## Etkilenen Dosyalar/Modüller (bilinen)
- `backend/file_search.py` — `search_files()`'a `fuzzy_name`/`name_pattern` parametreleri, Levenshtein hesaplama yardımcı fonksiyonu eklenir.
- `backend/models.py` — `SearchRequest`'e `fuzzyName`/`namePattern` alanları eklenir.
- `backend/main.py` — `search_endpoint()`'te iki-mod-çelişkisi + regex validasyonu (422) eklenir.

## Rollback Beklentisi
Salt-okunur bir özellik (dosya sistemi üzerinde yazma yapmıyor) — rollback kavramı uygulanmıyor.

## Risks
- ReDoS: kabul edilen risk (Threat-Model Notu'nda gerekçeli) — dosya adı uzunlukları doğal olarak kısa olduğu için pratik risk düşük, ama teorik olarak sıfır değil.
- Levenshtein hesaplama, dosya sayısı arttıkça O(n·m) maliyetlidir (n=dosya sayısı, m=ortalama isim uzunluğu×fuzzy_name uzunluğu) — non-recursive/kök-dizin sınırlaması bunu MVP için kabul edilebilir tutuyor.

## Assumptions
- `fuzzyName`/`namePattern` alan adları (camelCase), mevcut `nameContains`/`modifiedAfter` konvansiyonuyla tutarlı olacak şekilde varsayıldı.

## Unknowns
- Yok.

## Sorular ve Cevaplar (ham kayıt)
1. Fuzzy algoritma/eşik ne olsun? → Levenshtein mesafesi ≤2, stdlib (ek bağımlılık yok)
2. Regex ile fuzzy aynı çağrıda mı? → Hayır, iki ayrı parametre, birbirini dışlar
3. Geçersiz regex ne olsun? → 422
4. Recursive mi? → Hayır, sadece kök dizin (bilinçli karar)
5. İki mod birlikte verilirse? → 422
6. Benchmark ne olsun? → Levenshtein≤2 bulunur, geçersiz regex 422, ikisi birlikte 422
7. Test stratejisi oranı? → 80/15/5
8. Kapsam dışı ne var? → content_contains birleşimi yok, frontend yok, recursive yok
</content>
