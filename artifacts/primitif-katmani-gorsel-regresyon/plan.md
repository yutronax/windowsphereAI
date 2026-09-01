# Plan — primitif-katmani-gorsel-regresyon
_Reference: atdd.md_

## Files to Modify
(Yok — bu task bir doğrulama/rapor task'ı, hiçbir kod dosyası değişmiyor.)

## New Files
| File | Purpose |
|------|---------|
| artifacts/primitif-katmani-gorsel-regresyon/verify_report.md | Standart `verify` raporu; gate 12 (Görsel regresyon) bu task için AKTİF, 5 ekran/bileşen için ayrı kanıt satırıyla. |
| artifacts/primitif-katmani-gorsel-regresyon/*.png (opsiyonel, kanıt) | `verify_report.md`'ye referans verilen ekran görüntüleri — geçici Playwright dosyaları kalıcı kanıt gerekmiyorsa silinir (bkz. `vision-test` adım 5), gerekiyorsa burada saklanır. |

## Dependencies / Kod Keşfi Bulguları

**Unknown #1 çözüldü — ChatScreen'in PlanCard/ResultCard/TransactionHistoryPanel
state'lerine gerçek UI akışıyla nasıl ulaşılacağı:**
- `App.tsx` (satır 148-164): `config === undefined` ise `null` render eder;
  `config || sessionId` doğruysa doğrudan `ChatScreen`'i render eder,
  aksi halde `OnboardingScreen`'i.
- `config`, `GET /api/config`'ten gelir (`App.tsx` satır 35-38) —
  bu da `backend/config.py`'deki `load_setup_config()`'in
  `%APPDATA%\windows-ai-files\config.json` dosyasını okumasına dayanır.
  Dosya `{"selectedFolder": "<path>"}` içeriyorsa `/api/config` 200 döner
  ve **Onboarding'in Tauri native klasör diyaloğu (tarayıcı önizlemesinde
  çalışmıyor, bu oturumda daha önce doğrulandı) hiç devreye girmeden**
  doğrudan `ChatScreen` render edilir.
- Doğrulandı: `%APPDATA%\windows-ai-files\config.json` şu an mevcut değil
  — üzerine yazma/geri yükleme riski yok, test sonunda dosya silinecek
  (temiz durum).
- `ChatScreen`'e ulaşıldıktan sonra gerçek UI akışı (mock/test-double
  DEĞİL):
  1. `sessionId` App.tsx state'inde `OnboardingScreen.onContinue` ile
     set edilirdi normalde — config.json yoluyla `ChatScreen`'e
     doğrudan düşüldüğünde `sessionId` `null` kalır (satır 159:
     `sessionId ?? undefined`). `TransactionHistoryPanel` sadece
     `sessionId` varsa render edilir (satır 163) — bu yüzden
     `TransactionHistoryPanel`'i görmek için **gerçek bir session
     oluşturmak gerekiyor**, bu da Onboarding'in `onContinue`
     çağrılmasını (yani klasör diyaloğunun bir şekilde tamamlanmasını)
     gerektiriyor.
  2. **Çözüm:** `OnboardingScreen`'in "Klasör Seç" akışı native diyalog
     olmadan tamamlanamıyor, AMA `App.tsx`'in `sessionId` state'i sadece
     `OnboardingScreen`'in `onContinue` prop'undan geliyor — bu prop'u
     tetiklemenin native diyalog dışında bir yolu React kod
     düzeyinde yok. Bu nedenle `TransactionHistoryPanel`'i **gerçek
     tarayıcı önizlemesinde** görmek için ya (a) `npm run tauri:dev` ile
     GERÇEK Tauri penceresi (native diyalog çalışır) kullanılmalı, ya da
     (b) sadece bu görsel-doğrulama task'ı için, `App.tsx`'e DOKUNMADAN,
     `ChatScreen`'i `sessionId` prop'u ELLE verilerek (geçici, Playwright
     ile enjekte edilen bir test URL'i/route DEĞİL — bkz. Open Questions)
     izole render edilmesi gerekir.
  - Bu, `plan` adımının kendi başına çözemeyeceği gerçek bir açık soru —
    aşağıda **Open Questions**'a taşındı.

**PlanCard ve ResultCard için gerçek akış (Onboarding engelini aşmadan da
mümkün, kısmi kapsam):**
- `config.json` ile `ChatScreen`'e düşüldüğünde `sessionId` `null` olsa
  bile, `handleSendMessage`/`requestPlan` fonksiyonu `sessionId` `null`
  ise hiçbir şey yapmaz (`App.tsx` satır 108-111: `if (!sessionId) return;`)
  — yani PlanCard'ı tetiklemek için de gerçek bir `sessionId` şart.
- **Sonuç:** `config.json` yöntemi TEK BAŞINA sadece `ChatScreen`'in BOŞ
  halini (mesaj yok, `TransactionHistoryPanel` yok) gösterir — PlanCard/
  ResultCard/TransactionHistoryPanel'e ulaşmak için gerçek bir `sessionId`
  gerekiyor, bu da ya native Tauri penceresi ya da izole bileşen render'ı
  gerektiriyor.

**Vision-test altyapısı — kısmen kullanılamaz durumda, proje emsali var:**
- `C:\obss_bridge\ask_codex.py` (vision-test skill'inin dayandığı Codex
  köprüsü) bu makinede MEVCUT DEĞİL — doğrulandı (`ls` başarısız).
- Proje geçmişinde AYNI durum defalarca yaşanmış (bkz.
  `artifacts/gecersiz-klasor-reddi/atdd.md`, `ilk-istek-oturum-baglami/
  atdd.md`: "Codex vision-test kotası dolu, manuel/Playwright screenshot
  yöntemi kullanılacak") ve `artifacts/gecersiz-klasor-reddi/
  verify_report.md`'de gerçek emsal var: gate 12 "PASS (manuel screenshot,
  Codex vision-test DEĞİL)" olarak işaretlenmiş, Playwright screenshot
  `artifacts/<slug>/*.png` olarak saklanıp Claude'un kendisi doğrudan
  incelemiş.
- **Bu task da aynı emsali izleyecek** — atdd.md'nin "Assumptions"
  bölümündeki "vision-test nitel JSON sonucu" varsayımı, Codex köprüsü
  yokluğunda "Playwright screenshot + Claude'un kendi görsel incelemesi,
  verify_report.md'de 'Codex vision-test DEĞİL' notuyla" şeklinde
  güncellenmelidir (aşağıda Kararlar'a işlendi).

## Migration Required?
No — kod/şema değişikliği yok.

## Risks
- (atdd.md'den) `vision-test`'in Codex bağımlılığı çalışmıyor —
  DOĞRULANDI, proje emsaline göre (manuel Playwright screenshot) çözüldü,
  artık bir risk değil, bir karar.
- TransactionHistoryPanel'e native Tauri penceresi olmadan ulaşmanın kod
  değişikliği gerektirmeden mümkün olup olmadığı — Open Questions'a taşındı.

## Open Questions
1. `TransactionHistoryPanel`'i (ve tam akışla PlanCard/ResultCard'ı)
   görsel olarak doğrulamak için hangi yöntem kullanılmalı: (a) gerçek
   `npm run tauri:dev` penceresi (native klasör diyaloğu çalışır, ama
   Playwright bunu bir tarayıcı sekmesi gibi kolayca hedefleyemeyebilir —
   Tauri WebView'ı ayrı bir otomasyon gerektirir), (b) `%APPDATA%`
   config.json + backend API'ye (bu oturumda zaten çalışır durumda
   doğrulanan gerçek DeepSeek LLM bağlantısı ve `/api/session` /
   `/api/plan` / `/api/transactions/apply` uçları) DOĞRUDAN `curl`/
   `requests` ile bir session açıp `sessionId`'yi tarayıcıya nasıl
   aktaracağımız (React state'i dışarıdan set etmenin bir yolu yok,
   App.tsx bunu desteklemiyor), (c) bu 3 alt-bileşen (PlanCard/ResultCard/
   TransactionHistoryPanel) için SADECE bu doğrulama amacıyla App.tsx'e
   DOKUNMADAN mevcut testlerindeki (`PlanCard.test.tsx` vb.) render
   deseninin AYNISINI kullanan geçici, commit'lenmeyecek bir Vite giriş
   noktası (`ui/src/dev-preview.tsx` gibi, iş bitince silinir) mı
   kullanılmalı?

## Kararlar
1. **Seçenek (c) — geçici, commit'lenmeyecek `ui/src/dev-preview.tsx` ile
   izole render.** (Haiku alt-ajanı tarafından yanıtlandı: (a) Tauri
   WebView'ı Playwright'in kolayca hedefleyemeyeceği ayrı bir otomasyon
   gerektiriyor; (b) React state'i dışarıdan set etmenin App.tsx'te bir
   yolu yok; (c) mevcut `PlanCard.test.tsx`/`ResultCard.test.tsx`'teki
   render deseninin aynısını kullanan geçici bir Vite giriş noktası en az
   riskli/en hızlı yol.)
   - **Önemli netleştirme (atdd.md'nin Unknowns'ı ile çelişmesin diye):**
     `dev-preview.tsx` App.tsx'i TAKLİT ETMEZ, App.tsx'e hiç dokunmaz —
     sadece `ChatScreen`'i (App.tsx'in zaten kullandığı GERÇEK bileşen)
     doğrudan, sabit örnek `messages`/`plan`/`result` prop'larıyla monte
     eder (aynı `PlanCard.test.tsx`'in `render(<PlanCard plan={...} />)`
     deseni, ama gerçek tarayıcıda). Bu "mock/test-double" değil, "gerçek
     bileşeni gerçek proplarla izole render etme" — çünkü doğrulanan şey
     token/primitif katmanının GÖRSEL etkisi (ya da etkisizliği),
     backend/LLM akışının kendisi değil.
   - `verify` adımında kullanılacak, `code-copilot`/`test-copilot`
     tarafından YAZILMAYACAK (kalıcı bir implementasyon/test dosyası
     değil, tek seferlik görsel doğrulama aracı) — `verify` kendisi
     oluşturup işi bitince silecek.
2. **Vision-test Codex köprüsü yerine Playwright screenshot + Claude'un
   kendi görsel incelemesi kullanılacak**, proje emsaline uygun (bkz.
   Dependencies bölümü, `gecersiz-klasor-reddi` task'ındaki PASS kaydı).
   `verify_report.md`'de gate 12 "PASS (manuel screenshot, Codex
   vision-test DEĞİL)" formatıyla işaretlenecek.
