# Verify Report — primitif-katmani-gorsel-regresyon
_Reference: atdd.md, plan.md (code_diff.md/test_diff.md yok — bu task kod/test
yazmıyor, saf doğrulama; atdd.md + plan.md'nin "Kararlar" bölümü tek
referans)_

## Verification Gates
| # | Gate | Result | Evidence / Reason |
|---|------|--------|--------------------|
| 1 | Dosya konumu | PASS | `git status --short` — hiçbir kalıcı dosya değişikliği yok (geçici `ui/src/dev-preview.tsx` ve `main.tsx` swap'ı test sonunda temizlendi, doğrulandı) |
| 2 | Build/derleme | PASS | `npm run build` (`tsc --noEmit && vite build`) — temizlik sonrası sıfır hata, `dist/index.html` + `dist/assets/index-BvAZKmVx.js` üretildi |
| 3 | Supabase şema/canlı doğrulama | N/A | Bu task Supabase'e dokunmuyor — kod değişikliği yok |
| 4 | Lint | N/A | Repo'da yapılandırılmış linter/formatter yok (önceki task'larda da aynı sonuç) |
| 5 | Type check | PASS | `tsc --noEmit` gate 2'nin parçası, sıfır hata |
| 6 | Unit testler | PASS | `npx vitest run` → **238/238 PASS**, temizlik sonrası çalıştırıldı — token/primitif katmanının hâlâ hiçbir mevcut ekranı etkilemediği kod seviyesinde teyit edildi (AC-4) |
| 7 | E2E testler | PASS | Playwright MCP ile gerçek `npm run dev` sunucusuna karşı gerçek backend akışı sürüldü: (1) `%APPDATA%\windows-ai-files\config.json` ile Onboarding atlanıp ChatScreen'e ulaşıldı, (2) gerçek backend (`/api/session`→`/api/plan`→`/api/transactions/apply`, DeepSeek LLM ile) kullanılarak GERÇEK bir transaction oluşturuldu (id=1, 3 dosya taşındı), (3) geçici `dev-preview.tsx` ile `ChatScreen`'in kendisi (App.tsx'in kullandığı gerçek bileşen) sabit örnek `messages` prop'uyla monte edilip screenshot alındı — bkz. gate 12. **Netleştirme (red-team bulgusu):** `dev-preview.tsx`'in ürettiği kompozisyon (sabit `sessionId` + gerçek backend'den `TransactionHistoryPanel` verisi) App.tsx'in gerçek kod yolunda kullanıcının ulaşabileceği bir state DEĞİL — `config.json` ile `sessionId` her zaman `null` kalır (App.tsx satır 159), `dev-preview.tsx` bu iki yolu SADECE token/primitif katmanının görsel etkisini izole test etmek için birleştiriyor. Doğrulanan şey backend/LLM akışının kendisi değil, primitiflerin token'ları doğru render ettiği. |
| 8 | Lighthouse (performans) | N/A | atdd.md Benchmark bölümünde "Uygulanmaz" — tek seferlik doğrulama task'ı, sürekli performans hedefi yok |
| 9 | Erişilebilirlik | N/A | Aynı gerekçe (gate 8) |
| 10 | Güvenlik taraması | N/A | Bu task sıfır kod dosyası değiştiriyor/ekliyor — taranacak bir diff yok |
| 11 | AI code review | PENDING (red-team) | Ayrı adımda |
| 12 | Görsel regresyon | **PASS (manuel Playwright screenshot, Codex vision-test DEĞİL)** | Codex köprüsü (`C:\obss_bridge\ask_codex.py`) bu makinede yok (doğrulandı) — proje emsaline uygun olarak (bkz. `gecersiz-klasor-reddi` task'ı) Playwright screenshot alınıp Claude'un kendisi doğrudan incelendi. Aşağıda AC bazında detay. |
| 13 | DAST (ZAP) | N/A | Web UI'ye dokunuluyor ama bu task için `threat-model` hiçbir `AC-S<n>` üretmedi (auth/PII/ödeme/tenant sınırı yok) |
| 14 | İnsan onayı | PENDING | Kullanıcının açık onayı bekleniyor |

## Görsel Doğrulama Detayı (Gate 12)

**1) OnboardingScreen** — [`01-onboarding-screen.png`](01-onboarding-screen.png)
(Playwright ile kaydedildi, kalıcı kanıt): "Klasör Seç" başlığı, açıklama
metni, mavi "Klasör Seç" butonu (primary token rengi #1E3A8A ile tutarlı),
istek metin kutusu, "Devam" butonu — hepsi önceki (token/primitif
eklenmeden önceki) görünümle tutarlı, layout bozulmamış. **Sonuç:
bozulmamış.**

**2) ChatScreen (boş/kabuk hali)** — [`02-chatscreen-empty-shell.png`](02-chatscreen-empty-shell.png):
`config.json` ile Onboarding atlandıktan hemen sonra (henüz mesaj/primitif
render olmadan) mesaj alanı boş, alt kısımda metin kutusu + "Gönder"
butonu düzgün render ediliyor, layout bozulmamış. **Sonuç: bozulmamış.**

**3-5) PlanCard + ResultCard + TransactionHistoryPanel** —
[`03-chatscreen-plancard-resultcard-history.png`](03-chatscreen-plancard-resultcard-history.png)
(tek ekranda üçü birden):
- **PlanCard** (`dev-preview.tsx` ile örnek `Plan` verisiyle render
  edildi): "1. Taşı — 2026-09 (2 dosya)" satırı, mavi "Planı onayla"
  butonu (yüksekliği/radius/renk tutarlı — #1E3A8A) ve beyaz "Planı
  değiştir" butonu doğru şekilde render edildi, kart border/padding
  bozulmamış. **Sonuç: bozulmamış.**
- **ResultCard** (örnek `TransactionResult` verisiyle): "3 dosya
  işlendi" başlığı, "2026-09" hedef klasör listesi, "İşlem tamamlandı."
  durum metni ve kırmızı outline "Geri al" butonu (#DC2626 border/text)
  doğru render edildi. **Sonuç: bozulmamış.**
- **TransactionHistoryPanel** (sol panel, gerçek backend'den GERÇEK
  transaction verisiyle — mock DEĞİL): "İşlem Geçmişi" başlığı, "✓ Bağlı"
  durumu, "2026-09 → 3 dosya · 3 saat önce" satırı doğru render edildi.
  **Sonuç: bozulmamış.**

**Kanıt kalıcılığı (red-team bulgusu üzerine düzeltildi):** 3 PNG dosyası
`artifacts/primitif-katmani-gorsel-regresyon/` altında kalıcı olarak
saklanıyor — ilk koşumda (red-team incelemesi öncesi) screenshot'lar
saklanmamıştı, bu PASS iddiasını denetlenemez kılıyordu; red-team
bulgusu üzerine ekranlar TEKRAR yakalanıp kalıcı kanıt olarak eklendi.

**Ham Vitest kanıtı (red-team bulgusu üzerine eklendi):**
```
Test Files  14 passed (14)
     Tests  238 passed (238)
```

**Temizlik doğrulaması:** `git status --short` — geçici `dev-preview.tsx`,
`main.tsx` değişikliği ve `.playwright-mcp/` önbellek klasörü tamamen
geri alındı/silindi, hiçbir iz kalmadı (sadece 3 kalıcı PNG + bu rapor
kaldı); test klasörü (`plan_test_dir`) ve
`%APPDATA%\windows-ai-files\config.json` proje dışı geçici dosyalar,
silindi.

## AC -> Test Mapping
1. AC-1 (OnboardingScreen bozulmamış) → Manuel Playwright screenshot (oturum başında) → **PASS**
2. AC-2 (ChatScreen + PlanCard/ResultCard/TransactionHistoryPanel bozulmamış) → Manuel Playwright screenshot (`dev-preview.tsx` + gerçek backend transaction verisi) → **PASS**
3. AC-3 (gate 12'nin bu task için aktif çalışması, N/A ile geçilmemesi) → Yukarıdaki tablo, gate 12 açıkça PASS/kanıtlı → **PASS**
4. AC-4 (Vitest suite 238/238, kod-seviyeli ek kanıt) → `npx vitest run` → **PASS**

## Coverage / Quality Notes
- Davranış Sözleşmesi'nin "kısmi başarı" (#7) ve "hiçbir şey yapılamadı"
  (#8) satırları bu koşumda tetiklenmedi (5/5 ekran başarıyla render
  edildi, dev server ilk denemede ayaktaydı) — bu satırlar test edilmiş
  değil, sadece atdd.md'de teorik olarak tanımlı kaldı. Gelecekte dev
  server açılmazsa bu satırların gerçekten "PASS" değil "BAŞLATILAMADI"
  raporlanacağı davranışı bu koşumda GÖZLEMLENMEDİ (kod yok, sadece süreç
  disiplini — ama yine de not düşülüyor).
- `vision-test` skill'inin Codex bağımlılığı bu makinede çalışmıyor —
  bu, sadece bu task'a özgü değil, projenin genelinde tekrarlayan bir
  durum (bkz. `gecersiz-klasor-reddi`, `ilk-istek-oturum-baglami`). Bu
  `postmortem`'in "tekrar eden gate arızası" kalıbına aday bir bulgu.
