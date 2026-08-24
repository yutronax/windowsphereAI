---
task_slug: gecmisi-temizle-goruntuleme-esigi
jira_id: null
saga_task_id: 318
priority: low
coverage_target: 80
performance_target: "<100ms"
memory_target: null
test_strategy:
  unit: 60
  integration: 30
  e2e: 10
affected_modules:
  - backend/config.py (kalıcı eşik saklama)
  - backend/main.py (yeni POST endpoint + GET /api/transactions filtresi)
  - ui/src/components/chat/ChatScreen.tsx veya App.tsx (Geçmişi Temizle butonu)
---

# ATDD — gecmisi-temizle-goruntuleme-esigi

## Jira Kaynağı
Jira'ya bağlı değil — kaynak Saga task #318 (Epic #28 "Undo / Geri Alma Kullanıcı Arayüzü").

## Persona
windows-ai-files kullanıcısı; geçmiş işlem listesi zamanla kalabalıklaştığında görünümü sadeleştirmek isteyen kişi.

## Hedef (Neden)
Kullanıcı "Geçmişi Temizle" dediğinde eski işlemler geçmiş panelinde artık görünmesin — ama denetim/undo amacıyla veri DB'de kalsın, sadece görüntüleme eşiği ileri alınsın. Bu eşik backend yeniden başlasa bile korunmalı (kalıcı olmalı).

## User Story
As a windows-ai-files kullanıcısı
I want geçmiş listesini "Geçmişi Temizle" ile sadeleştirmek
So that eski işlemler beni yormadan yeni işlemlere odaklanabileyim, veri kaybı da yaşamadan

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. [Critical] Given geçmişte birden fazla transaction, When kullanıcı "Geçmişi Temizle"ye basar, Then eşik şu anki zamana ayarlanır ve sonraki GET /api/transactions çağrısı bu andan ÖNCEKİ hiçbir transaction'ı döndürmez (DB'den silinmez, sadece filtrelenir).
2. [Critical] Given eşik bir kez ayarlanmış, When backend yeniden başlatılır, Then eşik korunur ve GET /api/transactions filtrelemeye devam eder (eşik `%APPDATA%\windows-ai-files\config.json`'da kalıcı saklanır, bellek-içi `_sessions` dict'inde DEĞİL).
3. [High] Given eşik zaten ayarlanmış, When kullanıcı "Geçmişi Temizle"ye tekrar basar, Then işlem idempotent şekilde başarılı olur (eşik şimdiki zamana güncellenir), hata dönmez.
4. [High] Given eşik ayarlanmış, When eşikten SONRA yeni bir transaction oluşturulur, Then bu yeni transaction GET /api/transactions listesinde GÖRÜNÜR.
5. [Medium] Given hiç transaction yok, When kullanıcı "Geçmişi Temizle"ye basar, Then işlem sessizce başarılı olur (200), hata dönmez.
6. [Medium] Given config.json'a yazma başarısız olur (ör. disk/izin hatası), When "Geçmişi Temizle" çağrılır, Then 500 döner ve mevcut transaction verisi HİÇBİR ŞEKİLDE etkilenmez.

## Davranış Sözleşmesi (hangi durumda ne döner)
| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path | 200 + `{"clearedAt": "<ISO-8601>"}` | `config.json`'a `historyClearedAt` alanı yazılır | Geçmiş listesi bir sonraki yüklemede eski işlemleri göstermez | AC-1, AC-2 |
| 2 | Girdi geçersiz/eksik | Uygulanmadı — endpoint parametresiz bir POST, gönderilecek bir gövde yok, bu yüzden "geçersiz girdi" durumu geçerli değil | — | — | — |
| 3 | Kaynak yok (dosya/kayıt bulunamadı) | Uygulanmadı — bu endpoint bir ID/kaynak aramıyor, sadece eşik yazıyor | — | — | — |
| 4 | Yetkisiz erişim | Uygulanmadı — tek kullanıcılı yerel uygulamada auth katmanı yok (mevcut `/api/transactions` ile aynı güven sınırı, Saga #317'de de aynı gerekçeyle N/A) | — | — | — |
| 5 | Dış bağımlılık hatası (config.json yazma başarısız — disk/izin) | 500 + `{"detail": "Geçmiş temizlenemedi"}` | YOK — eşik güncellenmez, transaction verisi hiç etkilenmez | Hata mesajı gösterilir, buton tekrar denenebilir durumda kalır | AC-6 |
| 6 | Zaman aşımı | Uygulanmadı — işlem yerel dosya yazma, ağ çağrısı yok | — | — | — |
| 7 | **Kısmi başarı** (bir kısmı oldu, kalanı olmadı) | Uygulanmadı — eşik güncelleme TEK bir atomik dosya yazma işlemi, ara/kısmi bir durum yok (ya tamamen yazılır ya da hiç yazılmaz) | — | — | — |
| 8 | **Hiçbir şey yapılamadı ama hata da yok** (hiç transaction yokken veya eşik zaten güncelken tekrar çağrılırsa) | 200 + `{"clearedAt": "<ISO-8601>"}` — işlem YİNE DE gerçek bir yazma yapar (eşik şimdiki zamana güncellenir), bu yüzden "hiçbir şey yapılmadı" değil, idempotent bir başarıdır | `config.json` güncellenir (aynı veya daha yakın bir zaman damgasıyla) | Geçmiş listesi boş/değişmemiş görünür — ama bu SESSİZ BAŞARISIZLIK değil, gerçek bir başarılı çağrı | AC-3, AC-5 |

Kısmi başarı: Uygulanmadı — tek atomik dosya yazma işlemi, ara durum yok (satır 7'de gerekçelendirildi).
Hiçbir şey yapılamadı ama hata da yok: Satır 8'de detaylandırıldı — bu endpoint HER başarılı çağrıda gerçekten bir yazma yapar, bu yüzden "sessiz sahte-başarı" riski taşımaz; boş/değişmemiş görünüm her zaman gerçek bir yazmanın sonucu.
Boş sonuç ↔ hata ayrımı: GET /api/transactions'ın eşik sonrası boş dönmesi ("değişiklik yok" gibi) ile POST clear-history'nin 500 dönmesi ("işlem başarısız") birbirinden HTTP durum koduyla açıkça ayrılır — aynı değeri paylaşmazlar.

Uygulanmayan satırlar (2, 3, 4, 6, 7) silinmedi, gerekçesiyle yukarıda not edildi: endpoint parametresiz/kaynaksız/authsız/ağsız/atomik bir işlem.

## Test Strategy
Unit: 60% — eşik hesaplama/karşılaştırma mantığı (`created_at >= threshold` filtresi), config.json okuma/yazma fonksiyonları
Integration: 30% — POST clear-history + GET /api/transactions uçtan uca backend testleri (filtreleme, idempotency, restart-sonrası kalıcılık simülasyonu)
E2E: 10% — frontend "Geçmişi Temizle" butonunun tıklanınca listeyi güncellediği az sayıda senaryo

## Benchmark / Başarı Ölçütü
Coverage Target: 80%
Performance Target: <100ms (basit bir zaman damgası yazma/karşılaştırma işlemi)
Memory: belirtilmedi
Görsel/UI kriteri (varsa): "Geçmişi Temizle" butonu tıklandıktan sonra liste görünür şekilde güncellenmeli (bu kriter `verify` adımında `vision-test` ile kontrol edilir).
Diğer ölçülebilir kriterler: eşik değeri backend restart sonrası da doğru filtrelemeye devam etmeli (AC-2).

## Kapsam Dışı
- "Geçmişi geri getir" / clear işlemini geri alma (undo-the-undo) — bu task sadece TEK YÖNLÜ ileri alma kapsıyor.
- Eşiği kullanıcı bazlı/session bazlı yapmak — uygulama tek-kullanıcılı/authsız olduğu için eşik GLOBAL bir değer (görev başlığındaki "oturum bazlı" ifadesi yanıltıcı, gerçek kapsam global).
- Transaction verisinin DB'den fiziksel olarak silinmesi — bu KESİNLİKLE yapılmaz, sadece görüntüleme filtrelenir.

## Etkilenen Dosyalar/Modüller (bilinen)
- Backend: `backend/config.py` (yeni `historyClearedAt` alanı, mevcut `save_setup_config`/`load_setup_config` deseniyle tutarlı), `backend/main.py` (yeni `POST /api/transactions/clear-history` endpoint'i + `GET /api/transactions`'ın filtre mantığı)
- Frontend: "Geçmişi Temizle" butonu (henüz yok, yeni eklenecek — muhtemelen `ChatScreen.tsx` veya geçmiş panelinin bulunduğu bileşen)

## Rollback Beklentisi
config.json yazma başarısız olursa (satır 5) eşik güncellenmez ve transaction verisi hiçbir şekilde etkilenmez — işlem tamamen atomik, yarım bir durum bırakmaz.

## Risks
- Eşiğin `%APPDATA%\windows-ai-files\config.json`'da (mevcut `selectedFolder` ile aynı dosyada) saklanması, dosyanın eşzamanlı yazılması durumunda (aynı anda başka bir config güncellemesiyle çakışma) bir race condition riski taşıyabilir — düşük olasılık, tek kullanıcılı yerel uygulamada eşzamanlı çoklu istek beklenmiyor.

## Assumptions
- Yeni endpoint adı `POST /api/transactions/clear-history` olarak varsayıldı (kesin isim `plan` adımında kod tabanı incelenerek netleştirilebilir/değiştirilebilir).
- Eşik `config.json`'a yeni bir `historyClearedAt` (ISO-8601 string) alanı olarak eklenir, mevcut `selectedFolder` alanının yanına.

## Unknowns
- Frontend'de "Geçmişi Temizle" butonunun tam olarak hangi bileşende/nerede görüneceği netleşmedi — `plan` adımında kod tabanı incelenerek karara bağlanmalı.

## Sorular ve Cevaplar (Haiku alt-ajanı tarafından yanıtlandı)
1. Persona: kullanıcı geçmiş listesi kalabalıklaştığında UI'ı sadeleştirmek için temizler — (Haiku alt-ajanı tarafından yanıtlandı: masaüstü uygulamada sonuçlar zamanla birikir, yeni operasyonlara odaklanmak için eski olanları gizlemek pratiktir)
2. Eşik saklama: config.json'a yeni bir alan, GLOBAL (oturum bazlı değil) — (Haiku alt-ajanı tarafından yanıtlandı: uygulama tek-kullanıcılı/authsız, zaten kalıcılık için config.py deseni var, yeni DB tablosuna gerek yok)
3. Happy path: POST clear-history (body yok) → config.json'a zaman damgası yazılır → GET /api/transactions filtrelenir — (Haiku alt-ajanı tarafından yanıtlandı: en basit, düz tasarım)
4. Art arda 2 kez basma: idempotent no-op, eşik güncellenir, hata yok — (Haiku alt-ajanı tarafından yanıtlandı: başarılı ikinci çağrı 200 döner, veri kaybı olmaz)
5. Eşikten sonra yeni transaction: listede görünür — (Haiku alt-ajanı tarafından yanıtlandı: yeni işlemin timestamp'i eşik koşulunu sağlar)
6. HTTP happy path: 200 + `{clearedAt: ISO-8601}`, GET /api/transactions `created_at >= threshold` filtrelenir — (Haiku alt-ajanı tarafından yanıtlandı: REST standardı ve mevcut endpoint'lerle tutarlılık)
7. Girdi/body: parametresiz POST, eşik her zaman şu anki zaman — (Haiku alt-ajanı tarafından yanıtlandı: basitlik ilkesi)
8. Hiç transaction yokken temizleme: 200, sessiz başarı — (Haiku alt-ajanı tarafından yanıtlandı: hata değil, normal durum)
9. Performans/coverage: <100ms / %80+ — (Haiku alt-ajanı tarafından yanıtlandı: basit bir yazma+filtreleme işlemi, Saga #317 ile tutarlı)
10. Kapsam dışı: geri getirme/undo-clear kapsam dışı, tek yönlü — (Haiku alt-ajanı tarafından yanıtlandı: "Geçmişi Temizle" adı zaten tek yönlü bir işlemi ima ediyor)
11. Rollback: config.json yazma hatası → 500, transaction verisi etkilenmez — (Haiku alt-ajanı tarafından yanıtlandı: eşik güncelleme başarısız olsa da yapılan işlemler DB'de tutarlı kalır)
12. Test dağılımı: Unit 60 / Integration 30 / E2E 10 — (Haiku alt-ajanı tarafından yanıtlandı: Saga #317 ile paralel, endpoint basit, UI minimal)
