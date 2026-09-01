---
task_slug: primitif-katmani-gorsel-regresyon
jira_id: null
saga_task_id: 348
priority: medium
coverage_target: 100
performance_target: null
memory_target: null
test_strategy:
  unit: 0
  integration: 0
  e2e: 100
affected_modules:
  - (kod dosyası yok — bu bir doğrulama/rapor task'ı)
---

# ATDD — primitif-katmani-gorsel-regresyon

## Jira Kaynağı
Jira'ya bağlı değil — yerel görev (Saga #348, Epic #36 "Tasarım Sistemi
Temeli", epic'in son task'ı).

## Persona
Geliştirici / pipeline'ın kendisi (quality-gate) — Epic #36'nın (tokens.ts
+ Button/Card primitifleri) hiçbir mevcut ekranı bozmadığını, kod
testlerinin ötesinde gerçek render edilen piksel seviyesinde son bir kez
doğrulayan kişi/adım. İnsan onayı (pipeline'ın standart "İnsan onayı"
gate'i) bu doğrulamanın son tüketicisidir.

## Hedef (Neden)
Saga #345 (tokens.ts) ve #346 (Button/Card primitifleri) atdd.md'lerinde
"hiçbir mevcut ekran değişmiyor" iddiası vardı ve bu iddia her iki task'ın
kendi test suite'inde (238/238 PASS, `git diff` ile sıfır mevcut dosya
değişikliği) doğrulandı — ama bu, DOM/render testleri (jsdom), gerçek
tarayıcıda render edilen görsel çıktıyı garanti etmez (ör. CSS cascade
sırası, global stil sızıntısı, font yükleme farkı jsdom'da hiç
yakalanmaz). Bu task, o iddiayı gerçek `npm run dev` render'ında görsel
olarak bir kez daha doğrular — Epic #36'yı kapatmadan önceki son kalite
kapısı.

## User Story
As a pipeline / geliştirici
I want tokens.ts ve Button/Card primitiflerinin eklenmesinden sonra 5
mevcut ekranın (Onboarding, ChatScreen + içindeki PlanCard/ResultCard/
TransactionHistoryPanel) hâlâ öncekiyle görsel olarak aynı göründüğünü
doğrulamak
So that Epic #36'yı "hiçbir ekran değişmedi" iddiasıyla güvenle
kapatabileyim ve bir sonraki epic'te (ekranların primitife taşınması)
başlangıç noktasının bozulmamış olduğundan emin olabileyim.

## Acceptance Criteria (Given-When-Then, önceliklendirilmiş)
1. [Critical] Given `npm run dev` çalışan uygulama, When OnboardingScreen
   render edilir, Then `vision-test` skill'inin ürettiği JSON raporunda bu
   ekran için "layout bozulmamış / beklenmedik görsel öğe yok" sonucu
   döner.
2. [Critical] Given `npm run dev` çalışan uygulama ve bir sohbet oturumu
   (ChatScreen render edilecek şekilde), When ChatScreen (+ içinde
   PlanCard, ResultCard, TransactionHistoryPanel render olacak state'ler)
   sırayla tetiklenir, Then her biri için `vision-test` raporunda "layout
   bozulmamış" sonucu döner (toplam 5 ekran/bileşen).
3. [High] Given 5 ekranın tamamı için `vision-test` çalıştırıldı, Then
   `verify_report.md`'ye (bu pipeline'ın standart raporu) gate 12 (Görsel
   regresyon) satırı PASS/FAIL olarak, her ekran için ayrı kanıtla işlenir
   — genel bir "N/A" ile geçilmez (bu task'ın AC-1/AC-2 gate 12'yi bizzat
   aktive eden task olduğu için).
4. [Medium] Given görsel doğrulamayla eş zamanlı, When mevcut Vitest suite
   (238 test) çalıştırılır, Then hâlâ 238/238 PASS olur (kod-seviyeli
   kanıt, görsel kanıtı tamamlar — biri diğerinin yerine geçmez).

## Davranış Sözleşmesi (hangi durumda ne döner)
| # | Durum | Dönen değer / durum kodu | Yan etki | Kullanıcı ne görür | AC |
|---|---|---|---|---|---|
| 1 | Happy path: 5 ekranın tamamı görsel olarak bozulmamış | `vision-test` JSON'da her ekran için "ok"/layout sorunu yok | `verify_report.md` gate 12 PASS, kanıt olarak 5 ekranın JSON özeti eklenir | Kullanıcıya "5/5 ekran görsel olarak sağlam" özeti | AC-1, AC-2, AC-3 |
| 2 | Bir veya daha fazla ekranda görsel sorun tespit edilirse | `vision-test` JSON'da o ekran için sorun açıklaması (ör. "buton kesiliyor", "beklenmedik boşluk") | `verify_report.md` gate 12 FAIL, hangi ekran/hangi sorun açıkça yazılır; bu task KOD DÜZELTMEZ (kapsam dışı) | Kullanıcıya hangi ekranda ne sorun olduğu net şekilde raporlanır, düzeltme için #345/#346'nın ilgili commit'ine işaret edilir | AC-1, AC-2, AC-3 |
| 7 | Kısmi başarı: 5 ekrandan bazıları render edilebildi, bazıları edilemedi (ör. LLM'e bağlı bir state açılamadı) | Rapor "X/5 ekran doğrulandı, Y ekran render edilemedi (neden: ...)" şeklinde AÇIKÇA kısmi olarak işaretlenir — asla "5/5 PASS" gibi tam başarı iddia edilmez | `verify_report.md`'de bu gate FAIL (tamamlanmamış) olarak işaretlenir, eksik ekranlar isimleriyle listelenir | Kullanıcı hangi ekranların doğrulanamadığını ve nedenini görür | AC-1, AC-2 |
| 8 | Hiçbir şey yapılamadı ama hata yok (ör. dev server hiç açılmadı, 0 ekran denendi) | Bu durum "PASS" olarak ASLA raporlanmaz — `verify_report.md` gate 12 açıkça "N/A değil, BAŞLATILAMADI: dev server açılamadı" şeklinde işaretlenir, sessiz atlama yasak | Kullanıcı dev server'ı başlatması gerektiğini net şekilde görür | AC-1, AC-2 |

Boş sonuç ↔ hata ayrımı: Uygulanmaz — bu bir sorgu/API değil, görsel
doğrulama task'ı. "Hiçbir ekran kontrol edilmedi" (satır 8) ile "kontrol
edildi ve sorun bulunamadı" (satır 1) birbirinden `verify_report.md`'deki
açık metinle (kaç ekran gerçekten render edildi) ayrılır, aynı "PASS"
etiketi ASLA ikisi için de kullanılmaz.

## Test Strategy
Unit: 0% — bu task yeni kod/fonksiyon eklemiyor, mevcut kod-seviyeli
testler zaten #345/#346'da yazıldı (238/238 PASS, bu task onları tekrar
çalıştırıp aynı sonucu teyit eder ama yeni unit test yazmaz).
Integration: 0% — aynı gerekçe.
E2E: 100% — bu task'ın TAMAMI görsel/render doğrulaması (`vision-test`
skill'i, Playwright screenshot + vision model JSON raporu).

## Benchmark / Başarı Ölçütü
Coverage Target: 100% — 5 ekranın (Onboarding, ChatScreen, PlanCard,
ResultCard, TransactionHistoryPanel) TAMAMI görsel olarak kontrol edilmeli,
"örneklem" kabul edilmez.
Performance Target: Uygulanmaz — bu bir tek seferlik doğrulama task'ı,
sürekli çalışan bir sistem değil.
Memory: Uygulanmaz.
Görsel/UI kriteri: **Bu task'ın ÖZÜ görsel kriter** — 5 ekranın tamamında
layout/renk/spacing öncekiyle (yani #345/#346 öncesi haliyle) fark
edilmez olmalı. `vision-test` skill'i piksel-diff yüzdesi DEĞİL, yapısal/
görsel bir JSON değerlendirmesi (Codex vision model'in "bu ekran bozuk mu"
sorusuna verdiği yanıt) üretir — bu yüzden Haiku alt-ajanının önerdiği
"%0.5 diff eşiği" gibi sayısal bir piksel-fark toleransı bu projenin
`vision-test` skill'inin gerçek çalışma şekliyle uyuşmuyor (bkz.
Assumptions) ve KULLANILMAYACAK; bunun yerine `vision-test`'in ürettiği
JSON'daki nitel "layout bozulmamış / bozulmuş" sonucu esas alınacak.
Diğer ölçülebilir kriterler: Vitest tam suite 238/238 PASS (ek kanıt
olarak, görsel doğrulamanın YERİNE değil).

## Kapsam Dışı
- Ekranların (Onboarding/ChatScreen/PlanCard/ResultCard/
  TransactionHistoryPanel) Button/Card primitiflerine taşınması — bu Epic
  #36'nın değil, gelecekteki ekran-özel epic'lerin işi.
- Bu task sırasında bir görsel regresyon BULUNURSA onu düzeltmek — bu
  task sadece raporlar, kod yazmaz/düzeltmez (bulunursa kullanıcıya
  bildirilir, düzeltme ayrı bir task/skill akışına bırakılır).
- Otomatik CI pipeline kurulumu, otomatik "issue açma" veya "merge
  block" mekanizması — Haiku alt-ajanının önerdiği bu tür CI-entegrasyonu
  bu projede mevcut değil (repo'da `.github/workflows` yok, doğrulandı);
  bu task sadece `verify_report.md` üretir, otomatik bir CI kapısı kurmaz.
- Performans/Lighthouse ölçümü — atdd.md'nin Benchmark bölümünde
  "Uygulanmaz" olarak zaten belirtildi.

## Etkilenen Dosyalar/Modüller (bilinen)
Kod dosyası yok. Üretilecek tek çıktı:
`artifacts/primitif-katmani-gorsel-regresyon/verify_report.md` (standart
`verify` skill raporu, gate 12'nin bu task için AKTİF çalıştığı hali).

## Proje Ortamı Kısıtı (arama/grep kapsamı)
Doğrulandı: git reposunun kökü proje klasörünün (`windows-ai-files`)
kendisi, daha geniş bir ev dizini değil (`git status`/`git log` bu oturum
boyunca tutarlı şekilde proje köküne göre çalıştı). Ayrı bir kısıtlama
gerekmiyor.

## Rollback Beklentisi
Uygulanmaz — bu task hiçbir dosya değiştirmiyor, sadece bir rapor üretiyor.
Eğer görsel regresyon BULUNURSA, rollback kararı #345/#346'nın kendi
commit'lerine (`git revert`) ait olur, bu task'ın sorumluluğu değildir —
sadece bulguyu net şekilde raporlar.

## Risks
- `vision-test` skill'inin çalışması Codex CLI'a bağımlı; bu araç bu
  makinede kurulu/erişilebilir değilse task Codex bağımlılığı olmadan
  tamamlanamaz — bu durumda (Haiku'nun "hiçbir şey yapılamadı" satırı,
  #8) açıkça raporlanacak, sessizce N/A geçilmeyecek.
- Ekranlardan bazıları (ChatScreen içindeki PlanCard/ResultCard/
  TransactionHistoryPanel) belirli bir uygulama state'ine ulaşmadan
  render edilmiyor (ör. bir plan üretilmiş olması gerekebilir) — bu
  state'lere ulaşmak backend'in (ve muhtemelen LLM'in) çalışır olmasını
  gerektirebilir, `plan` adımında netleştirilecek.

## Assumptions
- Haiku alt-ajanının önerdiği "%0.5 piksel-diff eşiği", "exit code"ları,
  "./reports/task-348-regression-visual.json" dosya yolu ve "Saga issue
  otomatik açma" mekanizması bu projenin gerçek `vision-test` skill'inin
  (Playwright screenshot → Codex CLI vision model → JSON) çalışma şekliyle
  ve pipeline'ın gerçek dosya konumu konvansiyonuyla (`artifacts/<slug>/`)
  UYUŞMUYOR — bunlar KULLANILMADI, bunun yerine projenin gerçek `verify`
  skill'i ve `vision-test` skill'inin ürettiği nitel JSON sonucu esas
  alındı. Bu, atdd.md yazarının (ana ajan) bilinçli bir düzeltmesidir,
  kullanıcı onayı bekliyor.
- "5 ekran" olarak sayılan PlanCard/ResultCard/TransactionHistoryPanel'in
  aslında ayrı sayfalar değil, ChatScreen içinde koşullu render edilen alt
  bileşenler olduğu varsayıldı (kod tabanında önceki task'larda
  doğrulanmıştı) — bu yüzden "5 ekran" tek bir `npm run dev` oturumunda,
  ChatScreen'i farklı state'lere getirerek (plan üretilmiş, sonuç dönmüş,
  geçmiş açılmış vb.) taranacak, 5 ayrı route/URL olarak değil.

## Unknowns
- ChatScreen'in PlanCard/ResultCard/TransactionHistoryPanel'i render
  ettiği state'lere gerçek uygulama akışıyla mı (backend + LLM çalışır
  halde) yoksa mock/test-double bir yolla mı ulaşılacağı — `plan`
  adımında netleştirilecek.
- `vision-test` skill'inin bu projede daha önce hiç çalıştırılıp
  çalıştırılmadığı (Codex CLI kurulu mu) — `plan` adımında kontrol
  edilecek.

## Sorular ve Cevaplar (ham kayıt)
(Haiku alt-ajanı tarafından yanıtlandı — claude-omni bu makinede kurulu
değil, Adım B fallback kullanıldı)

1. Persona → CI quality-gate + lokal geliştirici doğrulaması (Haiku
   alt-ajanı tarafından yanıtlandı; atdd.md yazarı CI kısmını "bu projede
   CI yok" gerekçesiyle çıkarıp sadece "pipeline'ın kendisi / geliştirici"
   olarak sadeleştirdi)
2. Ana hedef → jsdom test'lerinin yakalayamayacağı gerçek render
   sorunlarını (CSS cascade, stil sızıntısı) yakalamak (Haiku alt-ajanı
   tarafından yanıtlandı)
3. Happy path → npm run dev + vision-test ile 5 ekran/bileşen taraması,
   baseline'a gerek yok çünkü #345/#346 testleri zaten "hiçbir ekran
   dokunulmadı" kanıtını verdi (Haiku alt-ajanı tarafından yanıtlandı)
4. Edge case 1 (render hatası) → o ekran için açıkça "render edilemedi"
   raporlanır, tüm task kısmi/FAIL sayılır (Haiku alt-ajanı tarafından
   yanıtlandı)
5. Edge case 2 (küçük görsel fark) → Haiku %0.5 piksel-eşiği önerdi, ama
   bu projenin `vision-test`'i piksel-diff değil nitel JSON ürettiği için
   atdd.md yazarı bunu nitel "bozulmuş/bozulmamış" değerlendirmesine
   çevirdi (bkz. Assumptions)
6. Davranış sözleşmesi → tabloya işlendi, Haiku'nun "exit code" ve
   "Saga issue otomatik aç" önerileri bu projede karşılığı olmadığı için
   (CI yok) çıkarılıp `verify_report.md`/kullanıcı bildirimine
   sadeleştirildi
7. Benchmark → 5/5 ekran, nitel "bozulmamış" sonucu (Haiku'nun sayısal
   eşiği yerine)
8. Kapsam dışı → ekran taşıması HARİÇ (zaten description'da netti),
   regresyon bulunursa DÜZELTMEK de hariç, otomatik CI/issue mekanizması
   da hariç (proje gerçeğiyle uyuşmadığı için atdd.md yazarı ekledi)
9. Bağımlılıklar/rapor → Haiku'nun önerdiği `./reports/...json` yolu
   yerine projenin gerçek konvansiyonu (`artifacts/<slug>/verify_report.md`)
   kullanıldı (atdd.md yazarı düzeltti)
10. Performans/güvenlik → yok, tek seferlik doğrulama (Haiku alt-ajanı
    tarafından yanıtlandı, süre sınırı iddiası çıkarıldı çünkü CI yok)
11. Rollback → bu task kod yazmıyor, regresyon bulunursa #345/#346'nın
    commit'lerine işaret eder (Haiku alt-ajanı tarafından yanıtlandı,
    "Saga issue aç" kısmı çıkarıldı)
12. Test stratejisi → %100 E2E/görsel, %0 unit/integration (Haiku alt-ajanı
    tarafından yanıtlandı)
13. Kabul kriteri sahibi → vision-test raporu + son gate olarak her zaman
    kullanıcının insan onayı (pipeline'ın standart "İnsan onayı" gate'i,
    Haiku'nun "QA lead" önerisi bu projede karşılığı olmadığı için
    kullanıcının kendisine sadeleştirildi)
