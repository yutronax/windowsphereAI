# Code Diff — sohbet-ekrani-gorsel-iyilestirme
_Reference: atdd.md, plan.md, test_diff.md_

Yazan: Haiku alt-ajanı (code-copilot dispatch, green step). Orkestratör
tarafından `Read` ile doğrulandı ve `npx vitest run` ile gerçekten
çalıştırıldı (sadece sub-agent'ın kendi özetine güvenilmedi).

## Değiştirilen Dosyalar
1. **ui/src/tokens.ts** — `colors` objesine 10 yeni alan eklendi: `dangerBannerBg/Border/Text`, `dangerMessageBg/Border/Text`, `successBg/Border/Text`, `connected`. Mevcut alanlar değişmedi.
2. **ui/src/components/chat/ChatScreen.tsx** — `import { tokens } from '../../tokens'` eklendi; `<style>` bloğundaki tüm ham hex renkler ilgili `tokens.colors.*` referanslarına taşındı (mesaj balonları, scroll-to-latest, plan-error-indicator, clear-history success/error mesajları, plan-retry, search-toggle butonları vb.).
3. **ui/src/components/chat/TransactionHistoryPanel.tsx** — `import { tokens } from '../../tokens'` eklendi; `chat-left-panel` border, `connection-status` rengi (connected/disconnected), loading/error/empty metin renkleri, liste öğesi border/renk `tokens.*`'a taşındı.

## Doğrulama (orkestratör tarafından)
- `git status --short` ile üç dosyanın da gerçekten değiştiği doğrulandı.
- Her üç dosya `Read` ile satır satır incelendi — pixel-perfect (aynı hex değerler, sadece kaynak `tokens.*`), layout/davranış/data-testid/aria değişmemiş.
- `npx vitest run tokens.test.ts ChatScreen.test.tsx TransactionHistoryPanel.test.tsx` (repo kökünden, vite.config.ts kökte) çalıştırıldı: **3 test dosyası, 84 test — hepsi PASS.**
- Test dosyalarına (tokens.test.ts, ChatScreen.test.tsx, TransactionHistoryPanel.test.tsx) dokunulmadığı doğrulandı (test-copilot'un bıraktığı haliyle aynı).

## Acceptance Criteria Karşılanması
| AC | Durum |
|----|-------|
| AC-1 (ham hex → tokens, pixel-perfect) | ✅ Karşılandı — testlerle doğrulandı |
| AC-2 (Button/Card primitifleri) | ✅ Plan.md kararı gereği KULLANILMADI (kapsam dışı bırakıldı, doğru) |
| AC-3 (mevcut testler regresyonsuz) | ✅ 84/84 test geçti |
| AC-4 (disconnected → tokens.colors.danger) | ✅ Karşılandı |
| AC-5 (tokens.ts genişletme) | ✅ 10 yeni alan eklendi, mevcut hex değerlerle birebir |
| AC-6 (build/lint hatasız, data-testid korunur) | ✅ Testler geçti (data-testid'lere bağlı testler dahil); lint/build `verify` adımında ayrıca çalıştırılacak |

## CAVEMAN Self-Review
Yeni dosya yok, yeni soyutlama/yardımcı fonksiyon yok — sadece renk kaynağı değişti. Minimum değişiklik ilkesine uygun.

## Kalan / Sonraki Adım
- `verify` adımı: lint, build, tam test suite, ve rendered `.tsx` dosyaları değiştiği için `vision-test` (gate 11) aktif çalışmalı.
