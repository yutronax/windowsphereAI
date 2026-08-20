---
task_slug: diff-tray-onizleme-ui
jira_id: null
saga_task_id: 317
priority: low
coverage_target: 80
performance_target: "<1000ms"
memory_target: null
test_strategy:
  unit: 60
  integration: 30
  e2e: 10
affected_modules:
  - GET /api/transactions (backend, Saga #294'te oluşturulmuş)
  - ResultCard / geçmiş paneli (frontend)
---

# ATDD — diff-tray-onizleme-ui

## Jira Kaynağı
Jira'ya bağlı değil — kaynak Saga task #317 (Epic #28 "Undo / Geri Alma Kullanıcı Arayüzü").

## Persona
windows-ai-files kullanıcısı; işlem (transaction) geçmişi panelinde geçmiş bir işlemin üzerine gelen (hover) kişi.

## Hedef (Neden)
Kullanıcı, geçmiş bir transaction'ın hangi dosyaları etkilediğini tam içeriği açmadan, git-status benzeri hafif bir önizlemeyle görebilsin. Şu an transaction geçmişi sadece işlem meta verisini gösteriyor, hangi dosyaların değiştiğini görmek için başka bir yol yok.

## User Story
As a windows-ai-files kullanıcısı
I want geçmiş bir transaction üzerine geldiğimde etkilenen dosyaların önce/sonra durumunun kısa bir listesini görmek
So that işlemi geri almadan önce neyin değiştiğini hızlıca anlayabileyim

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. [Critical] Given geçmişte dosya değişikliği içeren bir transaction, When kullanıcı transaction üzerine hover yapar, Then ilk 10 dosya adına kadar önce/sonra durumu (git-status benzeri) gösterilir.
2. [Critical] Given GET /api/transactions endpoint'i, When yanıt dönerse, Then her transaction objesine `preview` alanı (dosya adı listesi, en fazla 10 kayıt) eklenmiş olarak gelir — ayrı bir endpoint çağrısı gerekmez.
3. [High] Given bir transaction'da hiçbir dosya değişmemiş, When kullanıcı hover yapar, Then "Değişiklik yok" mesajı gösterilir (hata değil, boş liste değil çökme).
4. [High] Given transaction'daki bir DELETE operasyonunun fiziksel yedeği (`backup_path`) retention süresi dolup `purge_expired_delete_backups` tarafından silinmiş, When kullanıcı hover yapar, Then o operasyon için "Önizleme mevcut değil" mesajı gösterilir — bu, "değişiklik yok" mesajından farklı ve ayırt edilebilir olmalı. MOVE/RENAME/COPY operasyonlarında bu durum hiç oluşmaz.
5. [Medium] Given transaction 10'dan fazla dosya içeriyor, When önizleme oluşturulur, Then sadece ilk 10 dosya adı gösterilir, kalan sayı ("+N daha") belirtilir.
6. [Medium] Given transaction'daki bazı dosyaların önce/sonra durumu hesaplanamıyor (örn. dosya fiziksel olarak silinmiş/okunamıyor), When önizleme oluşturulur, Then hesaplanabilen dosyalar gösterilir + hesaplanamayanlar "?" işaretli belirsiz satır olarak işaretlenir; tüm önizleme iptal edilmez.

## Davranış Sözleşmesi (hangi durumda ne döner)
| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path (dosya değişiklikleri var) | 200 + transaction objesi içinde `preview: {files: [{name, before, after}], truncated: bool, total_count: int}` | yok (salt okunur) | Hover'da dosya listesi önce/sonra durumuyla | AC-1, AC-2 |
| 2 | Girdi geçersiz/eksik (geçersiz transaction id) | 404 + `{error: "transaction bulunamadı"}` | yok | "Transaction bulunamadı" hata mesajı | AC-4 (benzeri durum) |
| 3 | Kaynak yok (DELETE operasyonunun fiziksel yedeği `purge_expired_delete_backups` ile silinmiş) | 200 + `preview: {available: false, reason: "backup_purged"}` — SADECE bu durumda; MOVE/RENAME/COPY'de hiç tetiklenmez | yok | "Önizleme mevcut değil" mesajı | AC-4 |
| 4 | Yetkisiz erişim | Uygulanmadı — bu özellik tek kullanıcılı yerel uygulamada çalışıyor, auth katmanı yok (mevcut /api/transactions endpoint'iyle aynı güven sınırı) | — | — | — |
| 5 | Dış bağımlılık hatası (dosya sistemi okuma hatası) | 200 + `preview` içinde etkilenen dosya satırı `status: "unknown"` (belirsiz/"?" işaretli) olarak işaretlenir, geri kalan dosyalar normal döner | yok | Belirsiz satırlar "?" ile işaretli, diğerleri normal | AC-6 |
| 6 | Zaman aşımı | Uygulanmadı — işlem yerel dosya sistemi karşılaştırması, ağ çağrısı yok; büyük transaction'larda 1000ms hedefi aşılırsa bu bilinen risk olarak Risks bölümünde not edilmiştir, ayrı bir timeout davranışı tanımlanmamıştır | — | — | — |
| 7 | **Kısmi başarı** (bazı dosyalar hesaplanabildi, bazıları hesaplanamadı) | 200 + `preview.files` içinde karışık: hesaplanabilenler `before`/`after` dolu, hesaplanamayanlar `status: "unknown"` | yok | Hesaplanabilen dosyalar normal, diğerleri "?" işaretli satır | AC-6 |
| 8 | **Hiçbir şey yapılamadı ama hata da yok** (transaction'da hiç dosya değişikliği kaydı yok) | 200 + `preview: {files: [], empty: true}` | yok | "Değişiklik yok" mesajı — boş liste ile "önizleme mevcut değil" (durum 3) açıkça farklı alanlarla (`empty` vs `available: false`) ayrılır | AC-3 |

Kısmi başarı: Durum 7'de detaylandırıldı — hesaplanamayan dosyalar sessizce atlanmaz, "?" ile işaretlenir.
Hiçbir şey yapılamadı ama hata da yok: Durum 8'de detaylandırıldı — boş `files` dizisi + `empty: true` alanıyla açık şekilde işaretlenir, sessiz/belirsiz boş yanıt yasak.
Boş sonuç ↔ hata ayrımı: "Değişiklik yok" (`empty: true`, dosya değişikliği kaydı gerçekten yok) ile "Önizleme mevcut değil" (`available: false`, snapshot verisi temizlenmiş/kayıp) iki ayrı alanla ayırt edilir — aynı boş görünüm arkasında farklı kök nedenler UI'da farklı mesajla gösterilir.

Uygulanmayan satırlar (Yetkisiz erişim, Zaman aşımı) silinmedi, gerekçesiyle yukarıda not edildi: yerel tek-kullanıcılı uygulamada auth katmanı yok, işlem ağ çağrısı içermediği için timeout kavramı geçerli değil.

## Test Strategy
Unit: 60% — backend'de önce/sonra dosya listesi hesaplama mantığı (N limiti, "?" işaretleme, empty/available ayrımı)
Integration: 30% — GET /api/transactions endpoint'inin `preview` alanını doğru döndürdüğü uçtan uca backend testleri (snapshot var/yok/kısmi senaryoları)
E2E: 10% — frontend hover etkileşiminin önizlemeyi doğru gösterdiği az sayıda senaryo

## Benchmark / Başarı Ölçütü
Coverage Target: 80%
Performance Target: <1000ms (hover önizlemesinin yüklenme süresi)
Memory: belirtilmedi
Görsel/UI kriteri: Hover önizlemesi ResultCard/geçmiş panelinde düzeni bozmadan görünmeli; "Değişiklik yok" ve "Önizleme mevcut değil" mesajları görsel olarak ayırt edilebilir olmalı (bu kriter `verify` adımında `vision-test` ile kontrol edilir).
Diğer ölçülebilir kriterler: Önizleme listesi en fazla 10 dosya adı gösterir, fazlası "+N daha" ile özetlenir.

## Kapsam Dışı
- Dosya içeriği diff'i / tam metin karşılaştırması (sadece dosya adı + önce/sonra durum listesi kapsamda)
- Yeni bir authentication/authorization katmanı eklenmesi
- Transaction geçmişinin kendisinin (GET /api/transactions'ın temel davranışı, Saga #294) değiştirilmesi — sadece `preview` alanı eklenir
- **Çoklu geçmiş transaction listesi UI'ı** (`plan` adımında kod taramasıyla ortaya çıktı: frontend'de böyle bir liste bileşeni henüz yok, sadece `ResultCard` en son tek transaction'ı gösteriyor). Bu task hover önizlemesini SADECE `ResultCard`'ın gösterdiği transaction'a uygular; çoklu geçmiş listesi ayrı bir Saga task'ı.

## Etkilenen Dosyalar/Modüller (bilinen)
- Backend: GET /api/transactions endpoint'i (Saga #294'te oluşturulan handler)
- Frontend: ResultCard / transaction geçmiş paneli bileşeni (hover davranışı eklenecek)

## Rollback Beklentisi
Geçerli değil — bu özellik salt okunur bir önizleme, veri değiştirmiyor. Hata durumunda sadece UI'da hata/uyarı mesajı gösterilir, sistem durumu etkilenmez.

## Risks
- Çok sayıda dosya içeren büyük transaction'larda önizleme hesaplama süresi <1000ms hedefini aşabilir (performans riski, henüz ölçülmedi).

## Assumptions
- Snapshot verisi (transaction'ın önce/sonra dosya listesi) zaten bir yerde (muhtemelen transaction kaydının bir parçası olarak) saklanıyor; bu task sıfırdan snapshot toplama mekanizması kurmuyor, var olanı önizleme için kullanıyor.

## Unknowns
- Snapshot verisinin gerçek saklama formatı ve konumu netleşmedi — `plan` adımında kod tabanı incelenerek netleştirilmeli.

## Sorular ve Cevaplar (ham kayıt)
1. 317 neyi ifade ediyor? → Saga task ID (kullanıcı seçimi)
2. İlk N dosya adı limiti kaç olmalı? → İlk 10 dosya (Recommended)
3. Önizleme verisi mevcut endpoint'e mi eklensin, ayrı endpoint mi? → Mevcut endpoint'e alan ekle (Recommended)
4. Transaction'da hiç dosya değişmemişse ne gösterilsin? → "Değişiklik yok" mesajı (Recommended)
5. Snapshot verisi mevcut değilse ne dönmeli? → "Önizleme mevcut değil" mesajı, hata değil (Recommended)
6. Bazı dosyalar hesaplanamazsa kısmi önizleme ne yapmalı? → Hesaplanabilenleri göster + "?" işaretli belirsiz satır (Recommended)
7. Performans hedefi ne olmalı? → <1000ms
8. Dosya içeriği (tam diff) kapsamda mı? → Hayır, sadece dosya adı listesi (Recommended)
9. Test stratejisi oranı? → Unit 60 / Integration 30 / E2E 10 (Recommended)
10. Kabul kriterlerini kim onaylayacak? → Otomatik testler yeterli (Recommended)
11. Coverage hedefi yüzde kaç? → %80 (Recommended)
12. Rollback senaryosu var mı? → Yok — rollback geçerli değil (Recommended)
13. Bilinen risk/varsayım var mı? → Sadece büyük transaction performans riski (Recommended)
