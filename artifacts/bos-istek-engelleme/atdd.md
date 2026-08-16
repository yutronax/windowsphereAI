---
task_slug: bos-istek-engelleme
jira_id: null
saga_task_id: 255
priority: high
coverage_target: 90
performance_target: null
memory_target: null
test_strategy:
  unit: 70
  integration: 0
  e2e: 30
affected_modules:
  - ui/src/components/onboarding/OnboardingScreen.tsx
  - ui/src/components/onboarding/OnboardingScreen.test.tsx
  - ui/e2e/onboarding.spec.ts
---

# ATDD — bos-istek-engelleme

## Jira Kaynağı
Jira'ya bağlı değil — yerel görev. Saga task #255, epic #23 "MVP: Kullanıcı girişi ve ilk kayıt akışı" (proje: windows-ai-files).

## Persona
Muhasebeci/avukat segmentinden, ilk kez uygulamayı açan ve onboarding akışında çalışma klasörünü seçip doğal dil isteğini yazan kullanıcı.

## Hedef (Neden)
Kullanıcı boş veya sadece boşluk karakterlerinden oluşan bir istekle "Devam" butonuna bastığında şu an hiçbir geri bildirim verilmiyor (sessiz no-op) — kullanıcı ne olduğunu anlamıyor. Bu görev, boş/whitespace-only istek gönderimini engelleyip alan içi net bir hata göstererek bu sessiz başarısızlığı ortadan kaldırıyor.

## User Story
As a onboarding ekranındaki kullanıcı
I want boş veya sadece boşluk içeren bir istekle "Devam"a bastığımda net bir hata görmek
So that isteğimi yazmadan ilerleyemeyeceğimi hemen anlayayım ve ne yapmam gerektiğini bileyim

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. [Critical] Given requestText boşluk olmayan geçerli metin içeriyor ve klasör seçili, When kullanıcı "Devam" butonuna tıklar, Then hata mesajı/kırmızı kenarlık gösterilmez (onContinue'nun çağrılıp çağrılmaması bu task'ın kapsamı dışıdır, no-op kalır).
2. [Critical] Given requestText tamamen boş (`""`), When kullanıcı "Devam"a tıklar, Then textarea'ya `#DC2626` kenarlık uygulanır, altında "Devam etmek için bir istek yazın." mesajı görünür ve `onContinue` ÇAĞRILMAZ.
3. [Critical] Given requestText sadece boşluk karakterlerinden oluşuyor (örn. `"   "`, `"\n\t"`), When kullanıcı "Devam"a tıklar, Then AC-2 ile birebir aynı davranış (trim edilince boş kabul edilir).
4. [High] Given hata gösteriliyor (AC-2/AC-3 tetiklendi), When kullanıcı textarea içeriğini trim edilince boş olmayacak şekilde değiştirir, Then kırmızı kenarlık ve mesaj anında kaybolur — tekrar "Devam"a basmaya gerek yok.
5. [Medium] Given hata mesajı gösteriliyor, Then mesaj `aria-live="polite"` içeren bir container'da render edilir (ekran okuyucu duyurur).
6. [Medium] Given kullanıcı hatayı düzeltip tekrar boş/whitespace bırakır ve tekrar "Devam"a basar, Then hata tekrar gösterilir (kontrol her submit denemesinde tazelenir, tek seferlik değildir).

## Davranış Sözleşmesi (hangi durumda ne döner)
| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path — geçerli metin, "Devam"a tıklanır | `isRequestEmpty: false` (local state) | Yok (bu task kapsamında `onContinue` bağlanmıyor) | Hata yok, normal görünüm | AC-1 |
| 2 | Girdi tamamen boş, "Devam"a tıklanır | `isRequestEmpty: true` | `onContinue` çağrılmaz | Kırmızı (`#DC2626`) kenarlık + "Devam etmek için bir istek yazın." mesajı | AC-2 |
| 3 | Girdi sadece whitespace, "Devam"a tıklanır | `isRequestEmpty: true` (trim() ile tespit) | `onContinue` çağrılmaz | AC-2 ile aynı | AC-3 |
| 4 | Hata gösteriliyorken kullanıcı geçerli metin yazar | `isRequestEmpty: false` | Yok | Kırmızı kenarlık/mesaj anında kalkar | AC-4 |
| 5 | **Hiçbir şey yapılamadı ama hata da yok (önceki davranış)** | Öncesinde: no-op, hiçbir state değişmiyordu | Öncesinde: hiçbiri, sessiz başarısızlık | Şimdi: kullanıcı artık her zaman görsel geri bildirim alır (satır 2/3), sessiz no-op durumu bu değişiklikle ortadan kalkıyor | AC-2, AC-3 |

Kısmi başarı: Bu task'ta geçerli değil — validasyon atomik bir client-side kontrol, ara durum yok.
Boş sonuç ↔ hata ayrımı: Bu task'ta geçerli değil — backend çağrısı/veri sorgusu yok, sadece local input state kontrol ediliyor.
Kaynak yok / Yetkisiz erişim / Dış bağımlılık hatası / Zaman aşımı satırları silindi: bu görev tamamen client-side senkron bir string kontrolü; ağ, dosya sistemi veya yetkilendirme çağrısı içermiyor.

## Test Strategy
Unit: 70% — `OnboardingScreen.test.tsx`: trim() mantığı, buton tıklama sonrası state, hata mesajı görünürlüğü, aria-live varlığı, hata temizleme (AC-1 — AC-6 hepsi).
Integration: 0% — backend/API entegrasyonu bu task kapsamında yok.
E2E: 30% — `onboarding.spec.ts`: gerçek tarayıcıda boş/whitespace girip "Devam"a basma, kırmızı kenarlık ve mesajın DOM'da görünmesi, yazmaya başlayınca kaybolması.

## Benchmark / Başarı Ölçütü
Coverage Target: 90% (yeni eklenen validasyon mantığı için — proje genelinde zaten component+e2e test altyapısı var, öneri olarak belirlendi, kullanıcı spesifik sayı vermedi)
Performance Target: yok (saf client-side, ağ çağrısı yok)
Memory: yok
Görsel/UI kriteri: Kenarlık tam olarak `#DC2626`, mesaj metni tam olarak "Devam etmek için bir istek yazın." — `verify` adımında `vision-test` ile ekran görüntüsü üzerinden doğrulanmalı.
Diğer ölçülebilir kriterler: Kabul kriteri sahibi otomatik testler (unit+e2e yeşile dönerse task tamamlanmış sayılır, ayrıca manuel kullanıcı onayı istenmiyor).

## Kapsam Dışı
- `onContinue`'nun gerçek backend çağrısı/sonraki ekrana geçiş mantığına bağlanması (şu an no-op kalmaya devam edecek) — ayrı bir Saga task'ının kapsamında.
- `selectedFolder` seçilmemiş durumunun ele alınması (buton zaten `disabled` ile kapatılıyor, bu task'a dahil değil).
- Backend'e boş istek gitmesini engelleyen sunucu tarafı validasyon (bu tamamen client-side bir görev).

## Etkilenen Dosyalar/Modüller (bilinen)
- `ui/src/components/onboarding/OnboardingScreen.tsx` (textarea, "Devam" butonu, state)
- `ui/src/components/onboarding/OnboardingScreen.test.tsx` (yeni unit testler)
- `ui/e2e/onboarding.spec.ts` (yeni e2e senaryoları)

## Rollback Beklentisi
Geçerli değil — state'siz, yan etkisiz bir UI validasyonu; DB/dosya değişikliği yok, standart `git revert` yeterli.

## Risks
- Mevcut testlerde (`OnboardingScreen.test.tsx:125-169`, `onboarding.spec.ts:132-198`) zaten odak/blur kenarlık rengi (`#2563EB` / `#E5E7EB`) test ediliyor — yeni `#DC2626` hata kenarlığı bu odak/blur mantığıyla çakışmamalı (örn. hata varken input focus alırsa hangi renk öncelikli olacak, CSS specificity ile netleştirilmeli).

## Assumptions
- Coverage target %90 olarak varsayıldı (kullanıcı spesifik bir sayı vermedi, proje test altyapısına göre makul bir varsayılan).
- Trim mantığı için JavaScript `String.prototype.trim()` kullanılacağı varsayıldı (tüm whitespace karakterlerini — boşluk, tab, newline — kapsar).

## Unknowns
- Hata kenarlığı ile mevcut focus/blur kenarlık renkleri arasındaki CSS önceliği (bkz. Risks) — implementasyon sırasında netleştirilecek.

## Sorular ve Cevaplar (ham kayıt)
1. Hata (kırmızı kenarlık + mesaj) ne zaman tetiklenmeli? → Sadece "Devam"a basınca
2. Hata gösterildikten sonra kullanıcı tekrar yazmaya başlayınca ne olmalı? → İçerik değişince anında kaybolsun
3. onContinue'nun gerçek çağrılması bu görev kapsamında mı? → Hayır, sadece boş-istek engelleme
4. selectedFolder seçilmemişken bu AC'nin kapsamı ne olmalı? → Sadece requestText boşluk/whitespace kontrolü
5. Test stratejisi oranı (70/0/30) uygun mu? → Evet
6. Kabul kriteri sahibi kim? → Otomatik testler (unit+e2e) yeşile dönerse yeterli
7. Performans/güvenlik kısıtı var mı? → Yok, saf client-side validasyon
8. Hata mesajı aria-live ile duyurulsun mu? → Evet, aria-live="polite"
9. Task-slug 'bos-istek-engelleme' uygun mu? → Evet
10. Rollback beklentisi? → Geçerli değil
