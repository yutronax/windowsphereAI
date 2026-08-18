# Plan — Bulk-onay eşiği (Saga #311)

## Dosya değişiklikleri
- `ui/src/components/chat/PlanCard.tsx`: `BULK_CONFIRM_THRESHOLD=20`,
  `isConfirmingBulk` state, `totalAffectedFileCount` hesaplaması,
  `handleApprove`'un iki-aşamalı hale getirilmesi, `ResultCard`'ın
  revert onayıyla aynı desende (confirm/cancel çift buton) yeni bir dal.
- `ui/src/components/chat/PlanCard.test.tsx`: 3 yeni test.

## Yaklaşım
Sadece frontend, backend'e HİÇ dokunulmadı — `affectedFileCount` zaten
mevcut şemada. `ResultCard`'ın revert onayındaki (`confirming` state)
AYNI iki-aşamalı desen tekrar kullanıldı, yeni bir mekanizma icat
edilmedi.

## Araç notu
Küçük/izole bir frontend değişikliği olduğu için doğrudan Claude
tarafından yazıldı (aider-bridge/subagent delegasyonu gerekmedi —
2026-08-18'de netleşen "küçük görevlerde doğrudan yaz" kuralı).
Tam red-team yerine hafif bir öz-inceleme yapıldı (düşük risk, sadece
UI onay akışı, veri kaybı/güvenlik senaryosu yok).
