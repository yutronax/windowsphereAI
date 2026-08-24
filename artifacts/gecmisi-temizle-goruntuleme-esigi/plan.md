# Plan — gecmisi-temizle-goruntuleme-esigi
_Reference: atdd.md_

## Files to Modify
| File | Why | Risk |
|------|-----|------|
| backend/config.py | Kalıcı eşik saklamak için `save_setup_config`/`load_setup_config`e AYNI dosyada (`%APPDATA%\windows-ai-files\config.json`) yeni bir `historyClearedAt` alanı eklenecek (AC-2). Mevcut fonksiyonlar `selectedFolder`'a özel yazılmış — genişletilecek veya yanına eşdeğer `save_history_cleared_at`/`load_history_cleared_at` eklenecek. | low |
| backend/main.py | Yeni `POST /api/transactions/clear-history` endpoint'i (AC-1, AC-3, AC-5, AC-6) + `list_transactions`'ın (main.py:321-331) eşik sonrası filtre uygulaması (AC-1, AC-4). Yeni route, `/api/transactions/{transaction_id}/revert`den (main.py:334) farklı bir son segment taşıdığı için path çakışması yok. | medium |
| ui/src/components/chat/ChatScreen.tsx | "Geçmişi Temizle" butonu — mevcut `chat-search-toggle-button` deseniyle (satır 354-362) AYNI yerde, yanında bir buton olarak eklenecek (AC-1). | low |

## New Files
Yok — mevcut config.py/main.py/ChatScreen.tsx dosyalarına ekleme yapılıyor, yeni dosya gerekmiyor.

Not: Bu değişiklik bir rendered web UI dosyasına (`ChatScreen.tsx`) dokunuyor — `verify` adımında gate 11 (`vision-test`) N/A değil aktif çalışmalı.

## Dependencies
- `backend/config.py::config_path()` — `%APPDATA%\windows-ai-files\config.json` yolunu döner, yeni eşik fonksiyonları bunu yeniden kullanmalı, yeni bir path fonksiyonu icat edilmemeli.
- `backend/db_models.Transaction.created_at` — filtre bunun üzerinden yapılacak (`created_at >= threshold`).
- `backend/main.py::_transaction_to_summary`/`list_transactions` — mevcut sıralama deseni (main.py:328-330, `created_at.desc(), id.desc()`) korunmalı, filtre bu sorguya bir `.where()` olarak eklenir.
- Frontend: `ui/src/lib/backendHealth.ts::BACKEND_ORIGIN` (ResultCard.tsx'in kullandığı AYNI sabit) — yeni fetch çağrısı bunu kullanmalı.

## Migration Required?
Hayır. `Transaction`/`FileOperation` şemasında yeni kolon gerekmiyor — eşik DB'de değil, mevcut `config.json` dosya deseninde saklanıyor (atdd.md'nin Soru 2 kararı). Şema değişikliği yok.

## Risks
- (atdd.md'den taşındı) `config.json`'ın eşzamanlı yazılması durumunda race condition riski — düşük olasılık, tek kullanıcılı yerel uygulama.
- `historyClearedAt` alanı `selectedFolder` ile AYNI dosyada saklandığı için, mevcut `load_setup_config()`'in "sadece `selectedFolder` string ise geçerli" doğrulaması (config.py:23-25) yeni alanı YOK SAYMALI, bozmamalı — implementasyon bu fonksiyonu dikkatli genişletmeli (yeni bir doğrulama dalı, mevcut olanı bozmadan).

## Kararlar (Haiku alt-ajanı tarafından yanıtlandı)

Kod keşfinde ortaya çıkan tek açık soru: mevcut UI'da "geçmiş paneli" yok
(Saga #317'de de aynı bulgu) — "Geçmişi Temizle" butonu nereye konmalı?
Haiku alt-ajanına soruldu:

**Karar: `ChatScreen.tsx`'teki `chat-search-toggle-button`'ın yanına, AYNI
`sessionId` gate'iyle eklenir** — (Haiku alt-ajanı tarafından yanıtlandı:
"Geçmiş listesi bileşeni yoksa, butonu listeleme paneline bağlamak
imkansız. Kapsamı korumak için: eşik kaydeden backend endpoint'ini çağıran
minimalist düğme yerine getir, listeleme UI'ı başka task'a ertelenir" —
Saga #317'nin "çoklu geçmiş listesi kapsam dışı" kararı korunur).
