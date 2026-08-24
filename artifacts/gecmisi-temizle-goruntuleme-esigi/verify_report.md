# Verify Report — gecmisi-temizle-goruntuleme-esigi
_Reference: atdd.md, code_diff.md, test_diff.md_

> Not: Bu task'ta iki süreç olayı yaşandı (izinsiz commit + test dosyası
> kaybı, ve flaky bir zamanlama-bazlı filtre implementasyonun ID-bazlı
> filtreye yeniden tasarlanmasını gerektirdi) — detay için code_diff.md.
> Gate 11 (red-team) bu yüzden özellikle kritik.

## Verification Gates
| # | Gate | Result | Evidence / Reason |
|---|------|--------|--------------------|
| 1 | Dosya konumu | PASS | `git status --short` — `backend/config.py`, `backend/main.py`, `ui/src/components/chat/ChatScreen.tsx` (+testleri) gerçek proje kökünde değişmiş görünüyor. |
| 2 | Build/derleme | PASS | Backend: `.venv/Scripts/python.exe -c "import backend.main"` → hatasız. Frontend: `npm run build` (`tsc --noEmit && vite build`) → temiz, 0 hata. |
| 3 | Supabase şema/canlı doğrulama | N/A | Proje Supabase kullanmıyor (SQLite + SQLAlchemy). |
| 4 | Lint | N/A | Proje genelinde ne backend'de (ruff/flake8 yok) ne frontend'de (eslint yok) yapılandırılmış bir linter var. |
| 5 | Type check | PASS (frontend) / N/A (backend) | Frontend: `tsc --noEmit` (gate 2'nin parçası) → 0 hata. Backend: mypy/pyright yapılandırılmamış. |
| 6 | Unit testler | PASS | Backend: `.venv/Scripts/python.exe -m pytest backend/tests/test_main_integration.py -q` → **92 passed**, **5 ardışık çalıştırmada** tutarlı (flaky olmadığı doğrulandı). Frontend: `npx vitest run` (tüm proje) → **167 passed** (9 dosya). |
| 7 | E2E testler | N/A | Bu dar kapsamlı task için ayrı bir Playwright spec'i yazılmadı — atdd.md'nin E2E %10 payı component-seviyesi (RTL) hover/click testleriyle karşılandı (Saga #317'de de aynı karar). |
| 8 | Lighthouse (performans) | N/A | `lighthouse` MCP sunucusu bu ortamda mevcut değil. |
| 9 | Erişilebilirlik | N/A | Gate 8 ile aynı sebep. |
| 10 | Güvenlik taraması | PASS | `security-scan` skill'i 3 değişen dosyaya karşı çalıştırıldı → verdict: **PASS** (secrets/python_sast/python_deps/node_deps hepsi PASS, 0 bulgu). |
| 11 | AI code review | PENDING (red-team) | Ayrı `red-team` adımında yapılacak — bu task'ta normalden kritik (iki süreç olayı yaşandı, son düzeltme ana akış tarafından yapıldı). |
| 12 | Görsel regresyon | N/A | `vision-test` skill'i Codex CLI'ya bağımlı, kota dolu (bkz. proje hafızası). Kullanıcı isterse manuel gözden geçirebilir. |
| 13 | İnsan onayı | PENDING | Kullanıcı onayı bekleniyor. |

## AC -> Test Mapping
1. [Critical] Eşik ayarlanır, eşikten öncekiler filtrelenir → `test_clear_history_endpoint_sets_cleared_at_timestamp_and_returns_it` + `test_clear_history_filters_transactions_older_than_threshold` → PASS
2. [Critical] Eşik kalıcı, restart sonrası korunur → `test_clear_history_threshold_persists_in_config_json` → PASS
3. [High] İdempotent, tekrar çağrı başarılı → `test_clear_history_is_idempotent_updating_timestamp` → PASS
4. [High] Eşikten sonraki transaction görünür → `test_clear_history_preserves_transactions_created_after_threshold` → PASS
5. [Medium] Boş geçmişte sessiz başarı → `test_clear_history_succeeds_silently_when_no_transactions_exist` → PASS
6. [Medium] Config yazma hatası → 500, veri etkilenmez → `test_clear_history_returns_500_when_config_write_fails` → PASS

Tüm 6 AC'nin en az bir backend + bir frontend testi var.

## Coverage / Quality Notes
- **Tasarım notu (önemli):** Filtre başlangıçta `created_at` (timestamp) bazlıydı, bağımsız test çalıştırmasında flaky olduğu kanıtlandı (bkz. code_diff.md) ve `Transaction.id` bazlı bir tasarıma geçildi — bu, atdd.md'nin orijinal "eşik = zaman damgası" varsayımından bir sapma, ama API sözleşmesi (`clearedAt` ISO string döner/config.json'da görünür kalır) DEĞİŞMEDİ, sadece iç filtreleme mekanizması değişti.
- Test piramidi: atdd.md hedefi Unit 60/Integration 30/E2E 10 idi; gerçekleşen dağılım Saga #317 ile aynı desende (entegrasyon-ağırlıklı backend, component-testi ağırlıklı frontend).
- İki test (`sets_cleared_at_timestamp_and_returns_it`, `is_idempotent_updating_timestamp`) `get_db_session` dependency'sini override ETMİYOR — bu yüzden `clear_history_endpoint`in yeni `db` bağımlılığı gerçek (ama monkeypatch'lenmiş APPDATA'ya izole) bir SQLite engine kullanıyor. Bu, dosyanın kendi test-izolasyon yorumunda ("testler zaten get_db_session'ı TAMAMEN atlıyor") belirtilen varsayımı hafifçe zorluyor — 5x tekrar çalıştırmada sorun çıkmadı ama red-team'de ayrıca değerlendirilmeli.
