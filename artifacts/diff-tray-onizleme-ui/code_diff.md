# Code Diff — diff-tray-onizleme-ui

> Codex kotası dolu olduğu için (bkz. test_diff.md) implementasyon da
> kullanıcı onayıyla Claude tarafından yazıldı — `red-team` adımı bağımsız
> doğrulama yapmalı.

## Değişen Dosyalar

| Dosya | Değişiklik |
|---|---|
| `backend/models.py` | `TransactionPreviewFile`, `TransactionPreview` modelleri eklendi; `TransactionSummary.preview: TransactionPreview` alanı eklendi. |
| `backend/main.py` | `TransactionPreview`/`TransactionPreviewFile` import edildi; `PREVIEW_FILE_LIMIT = 10`; yeni `_build_transaction_preview()` fonksiyonu; `_transaction_to_summary()` artık `preview` alanını dolduruyor. |
| `ui/src/components/chat/ResultCard.tsx` | `Preview`/`PreviewFile`/`PreviewLoadState` tipleri; `handleHoverLoadPreview()` (hover'da lazy `GET /api/transactions` çağrısı, kendi `transactionId`'sine karşılık gelen `preview`'i bulur); `<section>`e `onMouseEnter`; önizleme render bloğu (`result-preview`/`result-preview-empty`/`result-preview-unavailable`/`result-preview-truncated`/`result-preview-unknown-<name>` test-id'leri). |

## Kararlar / Notlar
- Yeni bir backend endpoint'i EKLENMEDİ — plan.md/atdd.md kararına uygun, mevcut `GET /api/transactions` yeniden kullanıldı.
- Frontend hover'da preview verisi bir kez (`idle` → `loading` → `loaded`) yüklenir, tekrar hover'da tekrar istek atılmaz (basit önbellek).
- `backup_purged` SADECE `OperationType.DELETE` işlemlerinde, `backup_path` DB'de kayıtlı ama fiziksel dosya artık diskte yoksa tetiklenir — MOVE/RENAME/COPY'de asla.
- Kısmi başarı (before/after hesaplanamayan dosya): `status="unknown"`, satır atlanmaz.

## Test Sonuçları (red-team sonrası düzeltmeler dahil)
- Backend: `.venv/Scripts/python.exe -m pytest backend/tests/test_main_integration.py -q` → **85 passed**, regresyon yok.
- Frontend: `npx vitest run ui/src/components/chat/ResultCard.test.tsx` → **26 passed**, regresyon yok.
- Build: `npm run build` (`tsc --noEmit && vite build`) → temiz.

## Red-Team Sonrası Düzeltmeler
Bağımsız `obss-red-team` incelemesi 2 gerçek bulgu buldu, ikisi de düzeltildi (bkz. `red_team.json`):
1. **[high]** `backend/main.py::_build_transaction_preview` transaction-seviyesindeki `available`/`reason`'ı hiç set etmiyordu — atdd.md AC-4'ün vaat ettiği ayrı "Önizleme mevcut değil" sinyali gerçek backend'den asla tetiklenemiyordu. Düzeltildi: dosya-seviyesi sonuçlardan türetiliyor artık.
2. **[medium]** `ResultCard.tsx`'te preview fetch hatasında hiçbir UI geri bildirimi yoktu (sessiz başarısızlık). Düzeltildi: `result-preview-loading`/`result-preview-error` render blokları eklendi.
