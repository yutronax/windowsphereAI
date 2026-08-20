# Test Diff — diff-tray-onizleme-ui

> Not: Codex kotası 15 Eylül 2026'ya kadar dolu (bkz. proje hafızası). Kullanıcı
> onayıyla bu testler Codex yerine doğrudan Claude tarafından yazıldı — bu
> yüzden `red-team` adımı bu değişikliği bağımsız olarak MUTLAKA doğrulamalı.

## Backend — `backend/tests/test_main_integration.py` (mevcut dosyaya eklendi)

| Test | AC |
|---|---|
| `test_transactions_endpoint_preview_lists_file_names_only_not_full_paths` | AC-1, AC-2 (+ Saga #283 path-sızdırmama ilkesi) |
| `test_transactions_endpoint_preview_is_empty_when_transaction_has_no_operations` | AC-3 (davranış sözleşmesi durum 8) |
| `test_transactions_endpoint_preview_truncates_after_ten_files_and_reports_total_count` | AC-5 |
| `test_transactions_endpoint_preview_marks_delete_as_unavailable_when_backup_is_physically_purged` | AC-4 (davranış sözleşmesi durum 3) |
| `test_transactions_endpoint_preview_move_operation_is_never_marked_backup_purged` | AC-4 (negatif — MOVE/RENAME/COPY'de tetiklenmemeli) |
| `test_transactions_endpoint_preview_marks_unreadable_file_as_unknown_without_failing_the_whole_preview` | AC-6 (davranış sözleşmesi durum 7, kısmi başarı) |

## Frontend — `ui/src/components/chat/ResultCard.test.tsx` (mevcut dosyaya eklendi, yeni `describe` bloğu: "ResultCard hover onizleme (Saga #317)")

| Test | AC |
|---|---|
| `fetches and shows the file name preview list on hover` | AC-1, AC-2 |
| `shows a "no changes" message when the preview is empty, distinct from unavailable` | AC-3 |
| `shows an "unavailable" message distinguishable from the empty state when preview.available is false` | AC-4 |
| `shows a "+N daha" summary when the preview was truncated` | AC-5 |
| `marks a file whose before/after state could not be computed with a distinguishable "?" marker` | AC-6 |
| `does not show any preview when transactionId is missing` | scope guard (kapsam dışı olan çoklu-geçmiş varsayımına düşmesin diye) |

Her ikisi de şu an implementasyon olmadığı için KIRMIZI (red) durumda —
backend testleri `preview` alanı response'ta bulunmadığı için `KeyError`/
`None` ile, frontend testleri `result-preview*` test-id'leri DOM'da
bulunmadığı için başarısız olur. Sıradaki adım implementasyon (code-copilot
kapsamı — kota istisnası nedeniyle Claude tarafından yazılacak).
