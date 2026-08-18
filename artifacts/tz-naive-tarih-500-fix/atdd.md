---
task_slug: tz-naive-tarih-500-fix
jira_id: null
saga_task_id: 335
priority: low
coverage_target: 90
performance_target: null
memory_target: null
test_strategy:
  unit: 90
  integration: 10
  e2e: 0
affected_modules:
  - backend/main.py
---

# ATDD — tz-naive-tarih-500-fix

## Jira Kaynağı
Jira'ya bağlı değil — yerel görev (Saga #335, epic #27 "Dosya Arama")

## Persona
Muhasebeci — `/api/search` endpoint'ini `modifiedAfter`/`modifiedBefore` filtreleriyle çağıran, ama tarih string'ini offset (`+00:00`/`Z`) olmadan (naive) gönderen kullanıcı veya frontend istemci.

## Hedef (Neden)
Saga #313'ün `verify_report.md`'sinde bilinen bir sınırlama olarak not düşülmüştü: `modifiedAfter`/`modifiedBefore` timezone-naive bir ISO 8601 string'i (örn. `"2024-01-01T00:00:00"`, offset'siz) ile gönderilirse, `backend/main.py`'nin ürettiği naive `datetime` ile `backend/file_search.py`'nin tz-aware (UTC) `st_mtime` karşılaştırması `TypeError` verip 500'e düşüyor. Testler sadece tz-aware string'lerle yazıldığı için bu boşluk kapsanmamıştı. Bu task o boşluğu kapatıyor.

## User Story
As a muhasebeci (veya frontend istemci)
I want offset'siz bir tarih string'i gönderdiğimde arama 500 hatasıyla çökmesin
So that hangi formatta tarih gönderdiğime bakmaksızın arama güvenilir çalışsın

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. [Critical] Given `modifiedAfter="2024-01-01T00:00:00"` (naive, offset'siz), When `/api/search` çağrılır, Then 500 yerine 200 döner ve UTC varsayılarak doğru filtrelenmiş sonuçlar gelir.
2. [Critical] Given `modifiedBefore="2024-01-01T00:00:00"` (naive), When `/api/search` çağrılır, Then aynı şekilde 200 döner, UTC varsayılıp doğru filtrelenir.
3. [High] Given `modifiedAfter` naive VE `modifiedBefore` tz-aware (`"2024-01-01T00:00:00+03:00"`) birlikte, When `/api/search` çağrılır, Then her iki alan bağımsız olarak doğru normalize edilir (biri UTC varsayılır, diğeri kendi offset'iyle kalır), 200 döner.
4. [High] Given tamamen bozuk bir tarih string'i (örn. `"not-a-date"`), When `/api/search` çağrılır, Then mevcut davranış korunur — 422 döner (bu task bunu değiştirmiyor).
5. [Medium] Given zaten tz-aware bir string (örn. `"2024-01-01T00:00:00+00:00"`), When `/api/search` çağrılır, Then davranış Saga #313'teki gibi değişmeden 200 döner (regresyon yok).

## Davranış Sözleşmesi (hangi durumda ne döner)
| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path (naive tarih, UTC varsayılıp normalize edilir) | 200 + SearchResponse{results: [...]} | Yok (salt-okunur) | Doğru filtrelenmiş dosya listesi | AC-1, AC-2 |
| 2 | Girdi geçersiz (tamamen bozuk string) | 422 + {detail: "...geçersiz ISO 8601 formatı..."} | Yok | Alan altı hata mesajı (mevcut davranış, değişmiyor) | AC-4 |
| 3 | Kaynak yok (allowed_root artık mevcut değil) | 410 Gone (mevcut davranış, değişmiyor) | Yok | "Seçili klasör artık mevcut değil" | — (313'ten miras) |
| 4 | Yetkisiz erişim | Uygulanmıyor — bu task'ta yetkilendirme katmanı yok, session-tabanlı erişim zaten 313/314'te ele alındı. Silindi. | | | |
| 5 | Dış bağımlılık hatası | Uygulanmıyor — dış bağımlılık yok, saf datetime normalizasyonu. Silindi. | | | |
| 6 | Zaman aşımı | Uygulanmıyor — bu değişiklik content-arama timeout'una (#314) dokunmuyor, sadece tarih parse'ını etkiliyor. Silindi. | | | |
| 7 | Kısmi başarı (modifiedAfter naive, modifiedBefore aware karışık) | 200 + SearchResponse (her iki alan bağımsız normalize edilip AND ile birleşir) | Yok | Doğru filtrelenmiş sonuç, hiçbir alan "yarım" kalmaz | AC-3 |
| 8 | Hiçbir şey yapılamadı ama hata da yok (filtre sonucu 0 eşleşme) | 200 + SearchResponse{results: []} | Yok | Boş liste — bu "hata" değil "sonuç yok" | AC-1 (negatif durum) |

Kısmi başarı: Satır 7 — `modifiedAfter`/`modifiedBefore` birbirinden bağımsız normalize edilir, biri naive biri aware olsa bile ikisi de doğru UTC karşılaştırmasına dönüştürülüp AND mantığıyla birleşir; "yarım" bir normalizasyon durumu yoktur.
Hiçbir şey yapılamadı ama hata da yok: Filtrelere uyan dosya olmazsa `results: []` ile 200 döner — bu normal "sonuç yok" durumudur, hata değildir.
Boş sonuç ↔ hata ayrımı: Boş sonuç (`200 + []`) = eşleşme yok. Format hatası (`422`) = string hiç parse edilemiyor. Klasör yok (`410`) = allowed_root artık mevcut değil. Naive tarih ARTIK bu üçünden hiçbirine düşmez — sessizce UTC varsayılıp normal akışa girer (500 asla dönmemeli).

## Test Strategy
Unit: 90% — naive→UTC normalizasyon fonksiyonunun kendisi (çeşitli naive/aware/karışık girdi kombinasyonları)
Integration: 10% — `/api/search` endpoint'inin naive tarih string'iyle gerçekten 200 döndüğünü doğrulayan bir regresyon testi
E2E: 0% — bu küçük, saf bir normalizasyon düzeltmesi; e2e altyapısı projede zaten yok

## Benchmark / Başarı Ölçütü
Coverage Target: 90%
Performance Target: Yok (saf datetime işlemi, ölçülebilir performans etkisi yok)
Memory: Yok
Görsel/UI kriteri: Yok — backend-only
Diğer ölçülebilir kriterler: Naive + aware + karışık (biri naive biri aware) tüm kombinasyonlar 200 döner, hiçbiri 500 vermez — bu tek başına yeterli ölçülebilir hedef.

## Kapsam Dışı
- Frontend'in tarih seçici formatı — zaten aware gönderiyor olabilir, buna dokunulmuyor.
- Saga #314'te eklenen `content_contains` alanıyla hiçbir ilgisi yok.
- Tamamen bozuk (parse edilemeyen) string'lerin davranışı — mevcut 422 korunuyor, değiştirilmiyor.
- `backend/file_search.py`'de değişiklik yapılmıyor (kullanıcı kararı: düzeltme `backend/main.py`'de, parse anında yapılacak — `search_files()` her zaman tz-aware datetime alacak).

## Etkilenen Dosyalar/Modüller (bilinen)
- `backend/main.py` — `search_endpoint()` içindeki `modifiedAfter`/`modifiedBefore` parse bloğu: `dt.datetime.fromisoformat(...)` sonrası `tzinfo is None` ise `dt.timezone.utc` ata.

## Rollback Beklentisi
Salt-okunur bir düzeltme (dosya sistemi üzerinde yazma yapmıyor) — rollback kavramı uygulanmıyor. Hata durumunda sadece HTTP response döner, kalıcı durum değişmez.

## Risks
- Yok — kapsam çok dar ve iyi tanımlı, bilinen tek risk zaten bu task'ın kendisiyle çözülüyor.

## Assumptions
- Naive datetime'ın UTC varsayılması, dosya sisteminin `st_mtime`'ının zaten UTC ile karşılaştırıldığı (Saga #313/#314'teki mevcut davranış) ile tutarlı — kullanıcı bu yaklaşımı onayladı.

## Unknowns
- Yok.

## Sorular ve Cevaplar (ham kayıt)
1. Naive ISO string geldiğinde nasıl normalize edilsin? → UTC varsay (tzinfo=UTC ata)
2. Düzeltme nerede uygulansın? → backend/main.py — parse anında naive→UTC çevir
3. Geçersiz format için mevcut davranış değişsin mi? → Hayır, mevcut 422 aynen kalsın
4. Test stratejisi oranı? → 90/10/0
5. modifiedAfter/modifiedBefore karışık (biri naive biri aware) verilirse ne olsun? → İkisi de bağımsız normalize edilir
6. Benchmark ne olsun? → Naive+aware+karışık kombinasyonların hepsi 200 döner, hiç 500 olmaz
7. Kapsam dışı ne var? → Frontend tarih seçici formatı, content_contains ile ilgisizlik
8. Kabul kriteri sahibi kimin onayı yeterli? → Otomatik test yeterli, manuel onay istenmiyor
</content>
