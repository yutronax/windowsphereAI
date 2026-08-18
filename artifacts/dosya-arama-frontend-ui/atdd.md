---
task_slug: dosya-arama-frontend-ui
jira_id: null
saga_task_id: 334
priority: medium
coverage_target: 85
performance_target: "debounce 300ms, boş filtrede otomatik istek yok"
memory_target: null
test_strategy:
  unit: 70
  integration: 20
  e2e: 10
affected_modules:
  - ui/src/components/search/SearchPanel.tsx (yeni)
  - ui/src/components/chat/ChatScreen.tsx (toggle entegrasyonu)
---

# ATDD — dosya-arama-frontend-ui

## Jira Kaynağı
Jira'ya bağlı değil — yerel görev (Saga #334, epic #27 "Dosya Arama")

## Persona
Muhasebeci — ChatScreen'de çalışırken ara sıra isim/uzantı/tarih aralığına göre dosya araması yapmak isteyen, backend #313/#314'ün zaten sağladığı `/api/search`'ü kullanacak kullanıcı.

## Hedef (Neden)
Backend arama (#313) ve içerik arama (#314) tamamlandı ama hiçbir arayüzü yok — kullanıcı bu özelliği hiç kullanamıyor. Bu task minimal, sohbet akışına entegre olmayan bağımsız bir arama paneli ekliyor.

## User Story
As a muhasebeci
I want ChatScreen'den açabildiğim bir arama paneliyle isim/uzantı/tarih aralığına göre dosya arayabilmek
So that sohbet akışını bozmadan hızlıca dosya bulabileyim

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. [Critical] Given ChatScreen açık, When kullanıcı "Ara" toggle/tab'ına tıklar, Then SearchPanel açılır (boş liste + "Aramak için bir filtre girin" ipucu, otomatik istek atılmaz).
2. [Critical] Given SearchPanel açık, When kullanıcı isim/uzantı/tarih filtrelerinden birine değer girer, Then ~300ms debounce sonrası `/api/search`'e otomatik istek atılır ve sonuç listesi (filename/extension/modifiedAt/sizeBytes) güncellenir.
3. [High] Given SearchPanel açık ve bir arama sürüyorken kullanıcı yazmaya devam eder, Then sadece EN SON debounce edilen istek sonucu gösterilir (yarışan istekler arasında en son gönderilen kazanır — App.tsx'teki mevcut `latestRequestIdRef` desenine benzer).
4. [High] Given backend hata döner (404/410/422/ağ hatası), When arama isteği başarısız olur, Then panel içinde kısa bir hata mesajı gösterilir ve sonuç listesi boşaltılır.
5. [Medium] Given filtrelere uyan hiçbir dosya yok, When arama tamamlanır, Then boş liste + "Sonuç bulunamadı" benzeri bir metin gösterilir (hata mesajından görsel olarak ayrı).
6. [Medium] Given SearchPanel açıkken kullanıcı toggle'a tekrar tıklar, Then panel kapanır, mevcut sonuç/filtre durumu bir sonraki açılışta sıfırlanır (AC-1'deki başlangıç durumuna döner).
7. [Medium] Given bir arama sonucu satırı render edilir, When kullanıcı satıra tıklar, Then hiçbir işlem tetiklenmez (salt-okunur liste, MVP kapsamı).

## Davranış Sözleşmesi (hangi durumda ne döner)
| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path (filtre girilir, sonuç bulunur) | Component state: `results: SearchResultItem[]`, `error: null` | Yok (UI state) | Sonuç listesi (filename/extension/tarih/boyut) | AC-2 |
| 2 | Girdi geçersiz (backend 422 — örn. geçersiz tarih formatı) | Component state: `results: []`, `error: "<backend detail mesajı>"` | Sonuç listesi boşalır | Hata mesajı, boş liste | AC-4 |
| 3 | Kaynak yok (backend 410 — allowed_root artık yok) | Component state: `results: []`, `error: "Seçili klasör artık mevcut değil"` | Sonuç listesi boşalır | Hata mesajı | AC-4 |
| 4 | Yetkisiz erişim | Uygulanmıyor — session-tabanlı erişim zaten backend'de (#313/#314) ele alınıyor, bu UI katmanında ayrı bir yetkilendirme yok. Silindi. | | | |
| 5 | Dış bağımlılık hatası (ağ hatası — fetch reddi) | Component state: `results: []`, `error: "Sunucuya ulaşılamadı. Lütfen tekrar deneyin."` | Sonuç listesi boşalır | Hata mesajı (ChatScreen'in mevcut `planError` deseniyle tutarlı metin) | AC-4 |
| 6 | Zaman aşımı | Ayrı bir client-side timeout YOK — backend zaten kendi 10sn timeout'unu (#314) `partial:true` ile yönetiyor; bu UI'da modifiedAfter/Before/nameContains/extension aranıyor, content arama bu task'ta yok, backend'in timeout senaryosu bu ekranı etkilemiyor. Silindi. | | | |
| 7 | Kısmi başarı (bazı filtreler geçerli, biri geçersiz format) | Backend zaten AND ile tek istek olarak validize ediyor — geçersiz TEK bir alan tüm isteği 422 yapar (backend #313/#314 davranışı), UI bunu satır 2'deki gibi ele alır, "kısmi" bir UI durumu yok | Sonuç listesi boşalır | Hata mesajı | AC-4 |
| 8 | Hiçbir şey yapılamadı ama hata da yok (filtre yok VEYA sonuç 0) | Component state: `results: []`, `error: null`, `hint: "Aramak için bir filtre girin"` (filtre hiç girilmediyse) VEYA `"Sonuç bulunamadı"` (filtre girildi ama eşleşme yok) | Yok | İki farklı mesaj — biri "henüz aramadın", diğeri "aradın ama bulamadın" | AC-1, AC-5 |

Kısmi başarı: Satır 7 — UI seviyesinde kısmi başarı durumu yok, backend zaten tüm filtreleri tek istekte AND ile doğruluyor; herhangi bir alan geçersizse tüm istek 422 olarak reddedilir, UI bunu standart hata gösterimiyle ele alır.
Hiçbir şey yapılamadı ama hata da yok: Satır 8 — "hiç filtre girilmedi" (henüz arama yapılmadı) ile "arandı ama 0 sonuç" birbirinden AYRI mesajlarla gösterilir, aynı boş-liste görünümüne indirgenmez.
Boş sonuç ↔ hata ayrımı: `results: [] + error: null + hint` (arama yapılmadı veya 0 sonuç) ile `results: [] + error: "<mesaj>"` (istek başarısız oldu) UI'da görsel olarak farklı (hata kırmızı/uyarı stilinde, boş-sonuç nötr) — aynı görünüme düşmez.

## Test Strategy
Unit: 70% — debounce mantığı, filtre state yönetimi, yarışan istek sırası (AC-3), boş-filtre/hint mantığı (AC-1/AC-8)
Integration: 20% — React Testing Library ile SearchPanel'in fetch'i tetiklemesi, hata/başarı response'larına göre render değişimi (mevcut `ChatScreen.test.tsx`/`PlanCard.test.tsx` deseniyle tutarlı, `fetch` mock'lanır)
E2E: 10% — panel açma/kapama + tek bir happy-path arama senaryosu (varsa mevcut e2e altyapısı kullanılır, yoksa bu oran component-test'e kayar ve not düşülür)

## Benchmark / Başarı Ölçütü
Coverage Target: 85%
Performance Target: Debounce 300ms; boş/filtre-yok durumunda otomatik istek atılmaz (gereksiz backend çağrısı yok)
Memory: Belirtilmedi
Görsel/UI kriteri: Panel açılış/kapanış layout'u bozulmamalı, hata mesajı görünür olmalı, sonuç listesi okunur şekilde render edilmeli — bu kriter `verify` adımında `vision-test` ile kontrol edilecek.
Diğer ölçülebilir kriterler: Yarışan isteklerde (AC-3) sadece en son debounce edilen isteğin sonucu gösterilir — testte doğrulanabilir.

## Kapsam Dışı
- İçerik arama (`contentContains`, Saga #314) alanı bu UI'da YOK — sadece isim/uzantı/tarih aralığı.
- Sonuç satırına tıklayınca dosya açma/seçme/explorer entegrasyonu — salt-okunur liste.
- Sohbet akışına (ChatScreen mesaj listesine) entegrasyon — panel bağımsız bir toggle/overlay, mesaj geçmişine karışmaz.
- Büyük klasör ilerleme göstergesi (Saga #315) — bu UI'da yok.
- Fuzzy/regex arama (Saga #316) — bu UI'da yok.

## Etkilenen Dosyalar/Modüller (bilinen)
- `ui/src/components/search/SearchPanel.tsx` (yeni) — arama input'ları + sonuç listesi + debounce + hata/hint state yönetimi.
- `ui/src/components/chat/ChatScreen.tsx` — toggle butonu + SearchPanel'in koşullu render'ı eklenir (mevcut component'in dışına yeni bir state, `isSearchPanelOpen` gibi).
- `ui/src/lib/backendHealth.ts` içindeki `BACKEND_ORIGIN` sabiti muhtemelen SearchPanel'in fetch çağrısında da kullanılacak (mevcut App.tsx deseniyle tutarlı).

## Rollback Beklentisi
Salt-okunur bir UI özelliği — hiçbir kalıcı state/DB değişikliği yok. Hata durumunda sadece component state'i (results/error) sıfırlanır, rollback kavramı uygulanmıyor.

## Risks
- SearchPanel'in `sessionId`'ye nasıl erişeceği (App.tsx'te `sessionId` state'i var ama ChatScreen'e prop olarak GEÇİRİLMİYOR, sadece `onSendMessage`/`onApprovePlan` gibi callback'ler geçiriliyor) — plan aşamasında netleştirilmeli, muhtemelen `sessionId`'nin ChatScreen'e (ve oradan SearchPanel'e) prop olarak eklenmesi gerekecek.

## Assumptions
- Toggle butonunun ChatScreen'in üst kısmında (header benzeri bir yerde) yer alacağı varsayıldı — kesin konum plan aşamasında ChatScreen.tsx'in gerçek layout'una bakılarak netleştirilecek.

## Unknowns
- `sessionId`'nin ChatScreen → SearchPanel'e nasıl ulaştırılacağı (prop drilling mi, yoksa App.tsx'te doğrudan mı yönetilecek) — plan adımında koda bakılarak çözülmeli.

## Sorular ve Cevaplar (ham kayıt)
1. Kullanıcı arama paneline nasıl ulaşsın? → ChatScreen'de bir toggle/tab ile açılır-kapanır
2. Arama sonucundaki bir dosyaya tıklanırsa ne olsun? → Hiçbir şey, salt-okunur liste
3. Arama input'u nasıl tetiklensin? → Debounce'lu canlı arama (~300ms)
4. İçerik araması bu UI'da yer alsın mı? → Hayır, sadece isim/uzantı/tarih
5. Hata olursa kullanıcı ne görsün? → Panel içinde kısa hata mesajı, sonuç listesi boşalır
6. Benchmark ne olsun? → Debounce 300ms, boş filtrede otomatik istek yok, coverage %85
7. Test stratejisi oranı? → 70/20/10
8. Boş/filtre-yokken ne görünsün? → Boş liste + "Aramak için bir filtre girin" ipucu, otomatik istek yok
</content>
