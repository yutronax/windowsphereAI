---
task_slug: dosya-icerik-arama-encoding-timeout
jira_id: null
saga_task_id: 314
priority: medium
coverage_target: 85
performance_target: "1000 dosyalık klasörde arama 10sn içinde tamamlanır"
memory_target: null
test_strategy:
  unit: 70
  integration: 25
  e2e: 5
affected_modules:
  - backend/file_search.py
  - backend/models.py (SearchRequest/SearchResponse)
  - backend/main.py (search_endpoint)
threat_model: done
---

# ATDD — dosya-icerik-arama-encoding-timeout

## Jira Kaynağı
Jira'ya bağlı değil — yerel görev (Saga #314, epic #27 "Dosya Arama")

## Persona
Muhasebeci — klasördeki dosyaların içeriğinde belirli bir metni (örn. "fatura no 12345") arayan, dosyaların çoğu eski Türkçe encoding'lerle (cp1254/latin-1) kaydedilmiş kullanıcı.

## Hedef (Neden)
Saga #313 MVP'si sadece ad/uzantı/tarih filtreleriyle arıyor; içerik-bazlı arama olmadan kullanıcı "içinde X geçen dosya" ihtiyacını karşılayamıyor. Bu task içerik aramasını ekliyor, ama Türkçe encoding'lerin (utf-8 dışı) taramayı düşürmesini veya sonuç kaçırmasını önlemek ve büyük klasörlerde taramanın sonsuza sürmesini engellemek zorunlu.

## User Story
As a muhasebeci
I want dosya içeriğinde geçen bir metni arayabilmek (encoding'den bağımsız, zaman aşımı korumalı)
So that "fatura no 12345 geçen dosyaları bul" gibi ihtiyaçlarımı karşılayabileyim

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. [Critical] Given allowed_root altında utf-8/latin-1/cp1254 ile kaydedilmiş metin dosyaları, When contentContains="fatura no 12345" ile /api/search çağrılır, Then üç encoding'in hepsinde doğru eşleşen dosyalar sonuç listesinde döner.
2. [Critical] Given 1000 dosyalık bir klasör, When içerik araması 10 saniyeyi aşarsa, Then o ana kadar bulunan eşleşmeler `partial: true` bayrağıyla 200 döner (arama kesilmez, hata dönmez).
3. [High] Given klasörde binary dosyalar (örn. .exe, .pdf) ve 10MB+ metin dosyaları, When içerik araması çalıştırılır, Then bu dosyalar sessizce atlanır, sonuç listesinde görünmez, hata fırlatılmaz.
4. [High] Given contentContains="" (boş) veya sadece boşluk, When /api/search çağrılır, Then 422 Unprocessable Entity döner (diğer alan validasyonlarıyla tutarlı).
5. [Medium] Given klasörde okuma izni olmayan (permission denied) bir dosya, When içerik araması çalıştırılır, Then o dosya atlanır, arama diğer dosyalarla devam eder, hata dönmez.
6. [Medium] Given contentContains ile birlikte nameContains/extension/modifiedAfter/modifiedBefore filtreleri, When /api/search çağrılır, Then tüm filtreler AND mantığıyla birleşir (313'teki mevcut davranışla tutarlı).
7. [Medium] Given allowed_root'un doğrudan altındaki dosyalar ve alt klasörlerdeki dosyalar, When içerik araması çalıştırılır, Then sadece doğrudan alt dosyalar taranır (recursive değil — 313 ile aynı kapsam).
8. [High] Given allowed_root altında allowed_root DIŞINDA bir hedefe işaret eden bir symlink, When içerik araması çalıştırılır, Then symlink içeriği taranmaz/okunmaz, sonuç listesine girmez (allowed_root sınırının dışına çıkarak veri sızdırmayı önler).
9. [Medium] Given contentContains 500 karakterden uzun bir string, When /api/search çağrılır, Then 422 Unprocessable Entity döner (aşırı büyük payload ile bellek/CPU tüketimi DoS'unu önler).

## Davranış Sözleşmesi (hangi durumda ne döner)
| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path (3 encoding'de eşleşme) | 200 + SearchResponse{results: [...]} | Yok (salt-okunur) | Eşleşen dosya listesi | AC-1 |
| 2 | Girdi geçersiz (contentContains boş/whitespace) | 422 + {detail: "contentContains boş olamaz"} | Yok | Alan altı hata mesajı | AC-4 |
| 3 | Kaynak yok (allowed_root artık mevcut değil) | 410 Gone (mevcut /api/search davranışı, değişmiyor) | Yok | "Seçili klasör artık mevcut değil" | — (313'ten miras) |
| 4 | Yetkisiz erişim (tek dosya permission denied) | 200 + SearchResponse (o dosya hariç) | O dosya atlanır | Sonuç listesinde o dosya yok, hata yok | AC-5 |
| 5 | Dış bağımlılık hatası | Uygulanmıyor — dış bağımlılık (ağ/DB/API) yok, salt dosya sistemi işlemi. Silindi. | | | |
| 6 | Zaman aşımı (10sn aşıldı) | 200 + SearchResponse{results: [...], partial: true} | Tarama o an kesilir | "Kısmi sonuç" göstergesi (partial flag) | AC-2 |
| 7 | Kısmi başarı (bazı dosyalar okunamadı, bazıları okundu) | 200 + SearchResponse (okunabilenler dahil, okunamayanlar sessizce hariç) | Atlanan dosyalar için skippedCount YOK (kullanıcı tercihi: sessiz atlama) | Sadece eşleşen dosyalar, atlananlar görünmez | AC-3, AC-5 |
| 8 | Hiçbir şey yapılamadı ama hata da yok (0 sonuç) | 200 + SearchResponse{results: []} | Yok | Boş liste | AC-1 (negatif durum) |

Kısmi başarı: Satır 7 — dosyaların bir kısmı okunamasa (binary/büyük/izinsiz) bile arama complete sayılır, sadece okunabilen dosyalar taranır; kullanıcıya "eksik tarandı" bilgisi verilmez (kullanıcı kararı: sessiz atlama).
Hiçbir şey yapılamadı ama hata da yok: contentContains eşleşmesi 0 ise boş `results: []` ile 200 döner — bu "hata" değil "sonuç yok" anlamına gelir.
Boş sonuç ↔ hata ayrımı: Boş sonuç (`200 + []`) = eşleşme yok. Girdi hatası (`422`) = contentContains boş/whitespace. Klasör yok (`410`) = allowed_root artık mevcut değil. Üçü farklı status code'larla ayrılır, aynı response şekli asla karışmaz.

## Test Strategy
Unit: 70% — encoding fallback sırası (utf-8→latin-1→cp1254), timeout kesme mantığı, binary/10MB+ dosya atlama, boş contentContains reddi, permission-denied atlama
Integration: 25% — /api/search endpoint'inin contentContains ile diğer filtrelerle (nameContains/extension/tarih) AND kombinasyonu, gerçek dosya sistemine yazılmış fixture dosyalarla uçtan uca çağrı
E2E: 5% — tek bir tam senaryo: kullanıcı klasör seçer, içerik arar, sonuç listesini görür

## Benchmark / Başarı Ölçütü
Coverage Target: 85%
Performance Target: 1000 dosyalık klasörde arama 10 saniye içinde tamamlanır (veya partial:true ile kesilir)
Memory: Belirtilmedi (assumption: mevcut MVP'nin bellek profiline yakın, dosyalar stream/chunk okunur, tamamı belleğe yüklenmez)
Görsel/UI kriteri: Yok — bu task backend-only (frontend UI #334'te ayrı task)
Diğer ölçülebilir kriterler: 3 encoding'in (utf-8, latin-1/cp1252, cp1254) hepsinde doğru okuma test edilir

## Kapsam Dışı
- Fuzzy dosya adı / regex desen arama (Saga #316'da ayrı task)
- Büyük klasör taramalarında ilerleme göstergesi (Saga #315'te ayrı task)
- Frontend UI (Saga #334'te ayrı task, sadece backend contentContains alanı burada)
- Recursive (alt klasörlere inen) arama — kapsam 313 ile aynı, sadece doğrudan alt dosyalar
- Atlanan dosya sayısının response'a eklenmesi (skippedCount) — kullanıcı sessiz atlamayı tercih etti

## Etkilenen Dosyalar/Modüller (bilinen)
- backend/file_search.py — search_files() fonksiyonuna content_contains parametresi, encoding fallback, timeout, binary/boyut atlama mantığı eklenecek
- backend/models.py — SearchRequest'e contentContains, SearchResponse'a partial alanı eklenecek
- backend/main.py — search_endpoint'te contentContains validasyonu (boş/whitespace → 422)

## Rollback Beklentisi
Salt-okunur bir özellik (dosya sistemi üzerinde yazma/silme yapmıyor) — rollback kavramı uygulanmıyor. Hata durumunda sadece HTTP response döner, hiçbir kalıcı durum değişmez.

## Risks
- Encoding fallback sırası (utf-8→latin-1→cp1254) yanlış sırayla denenirse latin-1 geçerli ama yanlış decode edip cp1254 gereken içeriği atlayabilir — bu ATDD'de sıra netleştirilmedi, plan aşamasında kod tabanındaki benzer emsal aranmalı.
- 10 saniyelik global timeout, çok sayıda küçük dosya + az sayıda çok büyük (ama 10MB altı) dosya kombinasyonunda tutarsız kesme noktalarına yol açabilir.
- **Kabul edilen risk (threat-model):** Rate limiting / brute-force koruması bu task kapsamında yok — uygulama tek kullanıcılı, yerel masaüstü aracı (Electron/local backend), çok kiracılı sınır veya kimlik doğrulama katmanı yok. Bilinçli olarak kapsam dışı.

## Assumptions
- Dosyaların tamamı belleğe yüklenmeden, chunk/stream okunarak taranıyor (bellek hedefi kullanıcı tarafından verilmedi, bu bir varsayım).
- contentContains karşılaştırması case-insensitive (313'teki nameContains ile tutarlı) — kullanıcıya sorulmadı, emsal koddan varsayıldı.

## Unknowns
- Encoding fallback sırasının kesin denenme mantığı (ilk başarılı decode mu kullanılıyor, yoksa hepsi denenip en olası mı seçiliyor) — plan aşamasında netleştirilmeli.

## Sorular ve Cevaplar (ham kayıt)
1. İçerik araması hangi endpoint üzerinden çalışsın? → Mevcut /api/search'e contentContains parametresi eklensin
2. Global timeout süresi ne olmalı ve aşılırsa ne dönsün? → 10 saniye, kısmi sonuçlarla 200 dön
3. Binary dosya ve 10MB+ dosyalar atlandığında kullanıcı bunu görsün mü? → Sessizce atla, sadece eşleşenler listelenir
4. Başarı ölçütü / benchmark için hedef ne olsun? → 1000 dosyalık klasörde arama 10sn içinde tamamlanır, encoding testleri 3 kodlamayı da doğru okur
5. contentContains boş string veya sadece boşluk verilirse ne olsun? → 422 hata dön
6. İzin hatası (dosya okunamıyor) olursa tek dosya için ne olur? → O dosya atlanır, arama diğerleriyle devam eder
7. Test stratejisi oranı (unit/integration/e2e) nasıl olsun? → 70/25/5
8. İçerik araması recursive mi? → 313 ile aynı: sadece doğrudan alt dosyalar, recursive değil
</content>
