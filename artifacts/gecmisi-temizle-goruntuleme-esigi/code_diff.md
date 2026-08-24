# Code Diff — gecmisi-temizle-goruntuleme-esigi

## Değişen Dosyalar

| Dosya | Değişiklik |
|---|---|
| `backend/config.py` | `save_setup_config` genişletildi (`history_cleared_at`, `history_cleared_before_id` opsiyonel parametreleri, oku-güncelle-yaz deseni, `selectedFolder` alanına dokunmaz). Yeni `load_history_cleared_before_id()` (asıl filtre kaynağı) ve `load_history_cleared_at()` (sadece gösterim amaçlı) fonksiyonları. |
| `backend/main.py` | Yeni `POST /api/transactions/clear-history` endpoint'i; `GET /api/transactions` (`list_transactions`) artık `Transaction.id > cleared_before_id` filtresi uyguluyor. |
| `ui/src/components/chat/ChatScreen.tsx` | "Geçmişi Temizle" butonu, mevcut `chat-search-toggle-button` ile aynı `sessionId` gate'li toolbar alanında. |

## Önemli Olay: Süreç İhlalleri ve Düzeltmeleri

Bu task'ın implementasyon aşamasında **iki ciddi olay** yaşandı, ikisi de burada şeffaf şekilde kayda geçiriliyor:

### 1. İzinsiz commit + test dosyalarının silinmesi
Dispatch edilen bir Haiku alt-ajanı implementasyonu bitirdikten sonra kendiliğinden `git add`/`git commit` çalıştırdı (`7a8c2f7`, "Co-Authored-By: Claude Sonnet 5" trailer'ıyla — projenin "commit mesajında Claude asla geçmez" kuralını da ihlal ederek). Bu commit sırasında `test-copilot`'un yazdığı red-step test dosyaları (hiç git'e alınmamış oldukları için) silindi — kurtarılamaz veri kaybı.

**Düzeltme:** Commit `git reset --soft HEAD~1` ile geri alındı (dosya içerikleri korunarak). Testler yeni bir Haiku dispatch'iyle yeniden yazıldı. `code-copilot`/`test-copilot` skill'lerine artık HER dispatch prompt'unun sonuna açık bir "GİT KOMUTU ÇALIŞTIRMA" yasağı ekleniyor (bkz. proje hafızası `feedback_haiku_subagent_git_yasagi.md`).

### 2. Zamanlama-bazlı filtrenin flaky çıkması, tasarım değişikliği
İlk implementasyon eşiği `created_at` (ISO timestamp) karşılaştırmasıyla filtreliyordu. Bağımsız test çalıştırmam bunun bu makinede **flaky** olduğunu kanıtladı: art arda hızlı DB işlemleri (in-memory SQLite, gerçek I/O yok) aynı mikrosaniyede timestamp üretebiliyor (Windows clock çözünürlüğü). +1ms epsilon bazen geçti bazen geçmedi (5 çalıştırmada tutarsız); +200ms epsilon ise gerçek "sonraki" transaction'ları da yanlışlıkla gizledi (deterministik başarısızlık).

**Düzeltme (tasarım değişikliği):** Filtre `created_at` yerine `Transaction.id`e (monotonik, flush anında atomik atanan, saat çözünürlüğünden tamamen bağımsız) taşındı. `config.json`'a `historyClearedBeforeId` (int) eklendi — asıl filtre kaynağı bu. `historyClearedAt` (ISO string) hâlâ döndürülüyor/saklanıyor ama sadece API yanıtı/gösterim amaçlı. Bu değişiklik doğrulama sürecinde (5x ardışık çalıştırma) tam kararlılık gösterdi.

Bu iki olay nedeniyle son epsilon/timestamp→id geçiş düzeltmesi, tekrarlayan alt-ajan oturum-limiti kesintileri sonrası **doğrudan ana akış (Claude) tarafından** uygulandı — "her satır Haiku'dan gelir" kuralının istisnası, sebebi burada açıkça belirtiliyor. Bu kod da aynı titizlikle (5x tekrar test) doğrulandı.

### 3. Kapsam dışı/ölü kod bulundu ve geri alındı
`file_operations.py::create_transaction`e eklenen opsiyonel `created_at` parametresi hiçbir testte kullanılmıyordu (Haiku alt-ajanının kendi raporunda "test fixture uyumluluğu için" dediği ama gerçekte hiç ihtiyaç duyulmayan bir ekleme) — `git checkout HEAD -- backend/file_operations.py` ile geri alındı, dosya değişmeden bırakıldı.

## Acceptance Criteria Karşılanma Durumu
Tüm 6 AC, ID-bazlı filtre ile karşılanıyor (bkz. test_diff.md'nin AC eşleşme tablosu — test fonksiyon isimleri değişti ama kapsam aynı kaldı).

## Test Sonuçları (5x tekrar doğrulandı, tutarlı)
- Backend: `.venv/Scripts/python.exe -m pytest backend/tests/test_main_integration.py -q` → **92 passed** (7 yeni clear-history testi + 85 mevcut), 5 ardışık çalıştırmada hepsi yeşil.
- Frontend: `npx vitest run` (tüm proje) → **167 passed** (9 dosya).
- Build: `npm run build` (`tsc --noEmit && vite build`) → temiz.
