---
task_slug: ilk-acilis-klasor-secimi-ekrani
jira_id: null
saga_task_id: 250
priority: high
coverage_target: 80
performance_target: "<500ms (ekran render süresi, backend health-check hariç)"
memory_target: null
test_strategy:
  unit: 20
  integration: 30
  e2e: 50
affected_modules:
  - ui/src/components (yeni onboarding/setup ekranı)
  - Tauri sidecar başlatma/health-check mantığı
  - config/DB — ilk kurulum tespiti (config dosyası varlığı)
---

# ATDD — ilk-acilis-klasor-secimi-ekrani

## Jira Kaynağı
Jira'ya bağlı değil — yerel görev (Saga task #250, epic #23 "MVP: Kullanıcı
girişi ve ilk kayıt akışı", proje "windows-ai-files").

## Persona
Türkiye pazarında muhasebeci/avukat gibi teknik olmayan, yoğun dosya/belge
trafiği olan masaüstü kullanıcısı. (kullanıcı mesajından — DESIGN_DECISIONS.md
§1 Ürün Vizyonu)

## Hedef (Neden)
Uygulamanın hangi klasörde çalışmasına izin verildiğini (ALLOWED_PATHS
whitelist kaynağı) en başta, açıkça kullanıcıdan almak — güvenlik sınırının
temelini oluşturur ve sonraki her dosya operasyonu bu seçime dayanır.

## User Story
As a teknik olmayan masaüstü kullanıcısı
I want uygulamayı ilk açtığımda hangi klasörle çalışacağını net biçimde seçebilmek
So that AI asistanının hangi dosyalara erişebileceğini baştan kontrol edebileyim

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. [Critical] Given uygulama ilk kez açılıyor (config dosyası yok) ve backend
   hazır, When Tauri penceresi yüklenir, Then klasör seçimi ekranı 500ms
   içinde görünür ve "Klasör Seç" düğmesi etkindir.
2. [Critical] Given klasör seçimi ekranı açık, When kullanıcı "Klasör Seç"e
   basar ve native Windows dialogundan bir klasör seçer, Then seçilen yol
   ekranda gösterilir ve "Devam" düğmesi etkinleşir.
3. [High] Given klasör seçimi ekranı açık, When kullanıcı native dialogu
   Cancel/İptal ile kapatır, Then hiçbir yol kaydedilmez, ekran açık kalır,
   "Devam" düğmesi devre dışı kalır.
4. [High] Given uygulama açılıyor ve FastAPI sidecar henüz hazır değil, When
   Tauri penceresi yüklenir, Then kısa bir "Başlatılıyor…" göstergesi
   görünür, klasör seçimi/devam düğmesi backend health-check başarılı olana
   kadar devre dışı kalır.
5. [Medium] Given daha önce bir klasör seçilip config'e kaydedilmiş (ikinci
   ve sonraki açılışlar), When uygulama açılır, Then bu ekran hiç
   gösterilmez, doğrudan ana sohbet ekranına geçilir.

## Davranış Sözleşmesi (hangi durumda ne döner)
| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path — ilk açılış, backend hazır | `{status: "ready"}` ekran state'i | Yok (henüz diske yazma yok) | Klasör seçimi ekranı, etkin "Klasör Seç" düğmesi | AC-1 |
| 2 | Kullanıcı native dialogu Cancel ile kapatır | Seçim state'i `null` kalır | Yok | Ekran aynı kalır, "Devam" düğmesi disabled | AC-3 |
| 5 | Backend sidecar hazır değil (dış bağımlılık) | `{status: "starting"}` | Yok | "Başlatılıyor…" göstergesi, tüm etkileşim disabled | AC-4 |
| 6 | Backend health-check zaman aşımı (>10sn — kullanıcıyla teyit edildi, `plan.md` Open Question 1) | `{status: "backend_timeout"}` | Yok | Hata mesajı + "Tekrar dene" düğmesi | AC-4 (genişletildi) |
| 7 | Kısmi başarı | **N/A** — bu task tek adımlı bir ekran gösterimi, birden çok alt-işlem içermiyor | — | — | — |
| 8 | Hiçbir şey yapılamadı ama hata yok | Satır 2 ile aynı senaryo (Cancel) — ayrı bir "sessiz başarı" riski yok çünkü "Devam" düğmesi disabled kalarak durum açıkça görünür kılınıyor | — | — | AC-3 |

**Silinen satırlar ve neden:**
- **3 — Kaynak yok (dosya/kayıt bulunamadı):** Bu ekran herhangi bir dosya/kayıt
  aramaz, sadece bir klasör yolu toplar. Uygulanmaz.
- **4 — Yetkisiz erişim:** Seçilen yolun erişilebilirlik/geçerlilik kontrolü
  bilinçli olarak bu task'ın kapsamı dışında bırakıldı — ayrı Saga task #256
  ("Geçersiz veya erişilemeyen klasör seçimini açıklayıcı hata ile reddet")
  bu satırı kapsayacak.

Kısmi başarı: Uygulanmaz (bkz. satır 7 gerekçesi).
Hiçbir şey yapılamadı ama hata da yok: Cancel senaryosunda (satır 2) "Devam"
düğmesinin disabled kalması, sessiz başarı riskini önlüyor — kullanıcı hiçbir
zaman "seçim yapıldı" izlenimine kapılmıyor.
Boş sonuç ↔ hata ayrımı: Bu ekranda "boş sonuç" kavramı yok (henüz bir sorgu
yapılmıyor); "seçim yok" (Cancel) ile "backend hatası" (satır 6) açıkça farklı
UI durumlarıyla (disabled buton vs. hata mesajı) ayrıştırılıyor.

## Test Strategy
Unit: 20% — yardımcı fonksiyonlar (config dosyası varlığı → ilk kurulum
tespiti, path kısaltma/gösterim mantığı).
Integration: 30% — frontend↔backend health-check akışı (sidecar başlatma,
`/api/*` health endpoint polling, timeout davranışı).
E2E: 50% — gerçek Tauri penceresinde uçtan uca akış (ekran görünümü, native
dialog etkileşimi simülasyonu, Devam düğmesi durumu, ikinci açılışta
ekranın atlanması).

## Benchmark / Başarı Ölçütü
Coverage Target: 80%
Performance Target: <500ms (Tauri penceresi yüklendikten sonra ekranın
render edilme süresi; backend health-check süresi bu hedefe dahil değil)
Memory: Belirtilmedi (bu task için ölçülmeyecek)
Görsel/UI kriteri: Ekran görüntüsü kullanıcıya (Yusuf) gösterilip görsel
onay alınacak — `vision-test` skill'iyle `verify` adımında kontrol edilir.
Diğer: Otomatik test (unit+integration+e2e) YEŞİL olmalı; kabul kriteri
otomatik test + kullanıcının görsel onayının ikisi birden.

## Kapsam Dışı
- Seçilen klasörün geçerlilik/erişilebilirlik kontrolü (Saga task #256).
- İkinci ve sonraki açılışlarda klasörü değiştirme/ayarlar akışı (ayrı task).
- Metin kutusu/placeholder detayları (Saga task #253/#254 — bu ekranın
  "istek" kısmı değil, yalnızca "klasör seçimi" kısmı bu task'ta).
- Klavye ile tam gezinme detayları (Saga task #257'de ayrıca ele alınacak,
  bu task yalnızca temel görünürlük+seçim akışını kapsar).

## Etkilenen Dosyalar/Modüller (bilinen)
- `ui/src/components/` altında yeni bir onboarding/setup ekranı bileşeni
  (proje henüz sıfırdan yazılıyor, kesin dosya adı `plan` adımında netleşir).
- Tauri sidecar başlatma + health-check mantığı (Rust tarafı, `src-tauri/`).
- Backend tarafında ilk-kurulum tespiti için config/DB kontrolü.

## Rollback Beklentisi
Uygulanmaz (N/A). Bu task hiçbir kalıcı yan etki üretmez — seçilen yol
yalnızca ön uç state'inde tutulur, diske/DB'ye yazma ayrı bir task'ın
(SessionContext oluşturma, Saga task #258) kapsamındadır.

## Risks
- Tauri dialog API'sinin Windows'ta native davranışı henüz doğrulanmadı
  (proje sıfırdan yazılıyor, ilk somut Tauri entegrasyonu bu task olacak).

## Assumptions
- İlk kurulum tespiti, kullanıcı profilinde bir config/DB dosyasının
  var/yok olmasına göre yapılır — başka bir mekanizma (örn. registry key)
  kullanılmaz. (kullanıcı onayı alındı)
- Backend health-check zaman aşımı süresi 10 saniye olarak varsayıldı —
  kullanıcıyla teyit edilmedi, bkz. Unknowns.

## Unknowns
(Hepsi `plan` adımında çözüldü — bkz. plan.md Open Questions, kullanıcı
onayı alındı: timeout 10sn, config konumu `%APPDATA%/windows-ai-files/config.json`.)

## Sorular ve Cevaplar (ham kayıt)
1. Persona / hedef kullanıcı → DESIGN_DECISIONS.md §1'den (kullanıcı
   mesajından, tekrar sorulmadı): Türkiye pazarı, muhasebeci/avukat.
2. Ekran her açılışta mı görünsün, yoksa sadece ilk kurulumda mı? → Sadece
   ilk açılışta; sonraki açılışlarda kayıtlı klasör hatırlanır, ekran atlanır.
3. Klasör seçici mekanizması? → Native Windows klasör seçme dialogu (Tauri
   dialog API).
4. Kullanıcı native dialogu Cancel ile kapatırsa? → Seçim ekranında kal,
   klasör seçili değil, "Devam" disabled.
5. Backend sidecar henüz hazır değilse? → Kısa "Başlatılıyor…" göstergesi,
   etkileşim backend hazır olana kadar disabled.
6. Performans hedefi? → Evet, <500ms (ekranın render süresi).
7. Test stratejisi oranı? → 20/30/50 (unit/integration/e2e), UI-ağırlıklı
   task olduğu için e2e ağırlıklı.
8. Kapsam ne kadar geniş (geçerlilik kontrolü dahil mi)? → Hayır, sadece
   ekran + seçim akışı; geçerlilik kontrolü ayrı task #256'da.
9. Kabul kriteri sahibi kim? → Otomatik test + kullanıcının (Yusuf) görsel
   onayı birlikte.
10. Rollback bu task için geçerli mi? → Hayır, N/A (henüz diske yazma yok).
11. Bilinen risk/varsayım var mı? → Standart varsayım: config dosyası
    yokluğu = ilk kurulum; başka mekanizma kullanılmaz.
