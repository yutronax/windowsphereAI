# Test Diff — gecmisi-temizle-goruntuleme-esigi

> Not: Bu dosya bir olay sonrası GÜNCELLENDİ — ilk yazılan testler bir
> alt-ajanın izinsiz git işlemi sırasında silindi, aşağıdaki testler
> KURTARMA dispatch'inde yeniden yazıldı (fonksiyon isimleri ilk sürümden
> farklı). Detay için code_diff.md'deki "Önemli Olay" bölümüne bakın.

## Backend — `backend/tests/test_main_integration.py` (mevcut dosyaya eklendi, 7 test)

| Test | AC |
|---|---|
| `test_clear_history_endpoint_sets_cleared_at_timestamp_and_returns_it` | AC-1 |
| `test_clear_history_filters_transactions_older_than_threshold` | AC-1 |
| `test_clear_history_threshold_persists_in_config_json` | AC-2 |
| `test_clear_history_is_idempotent_updating_timestamp` | AC-3 |
| `test_clear_history_preserves_transactions_created_after_threshold` | AC-4 |
| `test_clear_history_succeeds_silently_when_no_transactions_exist` | AC-5 |
| `test_clear_history_returns_500_when_config_write_fails` | AC-6 |

## Frontend — `ui/src/components/chat/ChatScreen.test.tsx` (mevcut dosyaya eklendi, 5 test)

| Test | AC |
|---|---|
| `renders the clear history button when sessionId is provided` (benzeri) | Buton gate |
| `shows success message when clear-history succeeds` | AC-1 |
| `shows error message when clear-history fails` | AC-6 |
| `shows error message when fetch throws an exception` | AC-6 |
| `clears the success message when a new message is sent` | UX detayı |

Test-id'ler: `chat-clear-history-button`, `chat-clear-history-success-message`,
`chat-clear-history-error-message` (metni "Geçmiş temizlenemedi" içerir).

Tüm 12 test (7 backend + 5 frontend) gerçek implementasyona karşı 5+ kez
ardışık çalıştırıldı, tutarlı yeşil. Backend filtrelemesi `Transaction.id`
bazlı (timestamp DEĞİL) — bkz. code_diff.md'deki tasarım değişikliği notu.
