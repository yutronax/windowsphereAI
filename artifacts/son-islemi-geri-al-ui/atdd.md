---
task_slug: son-islemi-geri-al-ui
priority: medium
coverage_target: "60/40/0"
performance_target: "yok"
test_strategy: "unit (pytest backend + vitest/testing-library frontend)"
affected_modules:
  - backend/models.py
  - backend/main.py
  - ui/src/components/chat/ResultCard.tsx
saga_task_id: 295
epic_id: 28
---

# ATDD — "Son İşlemi Geri Al" UI'ı (Saga #295)

## Goal
`ResultCard`'a bir "Geri al" butonu eklemek. Kod keşfinde bulunan gerçek
boşluk: task'ın varsaydığı "backend'in yeni revert-transaction
endpoint'i" HENÜZ YOK — sadece çağrılabilir `revert_transaction()`
fonksiyonu (Saga #293) ve salt-okunur `GET /api/transactions` (Saga
#294) var. Bu task, dar kapsamlı bir POST endpoint'ini de İÇERİYOR
(butonun çağıracağı gerçek bir şey olması için önkoşul).

## Sorular ve Cevaplar (saga-oto tarafından otomatik seçildi)

**S1: Endpoint'in imzası ne olmalı?** Cevap:
`POST /api/transactions/{transaction_id}/revert`, body: `{allowedRoot: str}`.
`revert_transaction(session, transaction, allowed_root)` `allowed_root`'u
ZORUNLU parametre olarak alıyor (Saga #293 red-team kararı) ama
`Transaction` tablosunda bir `allowed_root`/`session_id` kolonu YOK
(Saga #294'te aynı gerekçeyle şema değişikliği reddedildi — dar kapsam
tutarlılığı). Bu yüzden `allowedRoot`'un DOĞRUDAN istek gövdesinde
istemciden gelmesi gerekiyor — istemci zaten bunu biliyor (session'ın
`selectedFolder`'ı). Path normalizasyonu `SessionRequest`teki AYNI
`normalize_selected_folder` ile yapılır (tutarlılık). (saga-oto
tarafından otomatik seçildi — şema değişikliği olmadan en dar çözüm)

**S2: Hata durumları nasıl HTTP status'lere eşlenmeli?** Cevap:
(a) transaction id bulunamazsa → 404. (b) transaction `status !=
"committed"` ise (henüz denemeden ÖNCE kontrol edilir, `revert_transaction`
çağrılmadan) → 409 Conflict. (c) `revert_transaction` çağrıldıktan SONRA
fiziksel bir rollback adımı başarısız olursa (`TransactionRevertError`,
ama transaction zaten "committed" durumundaydı) → bu bir İSTEMCİ HATASI
DEĞİL, gerçek bir operasyon SONUCU — 200 OK ile `{"status":
"revert_failed"}` gövdesi döner (ResultCard'ın zaten sahip olduğu
completed/partial/failed üçlü-durum modeline uyar). Bu ayrım, hata
mesajını PARSE ETMEDEN, `revert_transaction`i çağırmadan ÖNCE
`transaction.status`u kontrol ederek netleştiriliyor (string-eşleştirme
kırılganlığından kaçınmak için). (saga-oto tarafından otomatik seçildi)

**S3: "Geri alma onayı" gerekli mi (PlanCard'ın fail-closed deseniyle
tutarlı)?** Cevap: EVET, ama PlanCard'ın "backend onayı olmadan buton
DEVRE DIŞI" deseninden FARKLI bir risk sınıfı — burada backend'in
kendisi zaten güvenli (whitelist + committed-only kontrolü var), risk
SADECE kullanıcının YANLIŞLIKLA tıklaması. Bu yüzden İKİ AŞAMALI inline
onay yeterli: ilk tıklama butonu "Emin misiniz?" + "Evet, geri al"/"Vazgeç"
çiftine çevirir, SADECE ikinci tıklama gerçek isteği gönderir. Ayrı bir
modal/dialog İCAT EDİLMEDİ (YAGNI, mevcut kod tabanında hiç modal
deseni yok). (saga-oto tarafından otomatik seçildi — dar kapsam, mevcut
UI birincil desenlerine (inline durum geçişi, PlanCard'ın `hasApproved`
state'i gibi) tutarlı)

**S4: Buton ne zaman hiç GÖSTERİLMEZ?** Cevap: `result.transactionId`
VEYA yeni `selectedFolder` prop'u eksikse (fail-closed: geri alma
isteğini GÜVENLE oluşturamıyorsak buton hiç gösterilmez). Backend
zaten `allowed_root` içermeyen bir istek gönderilemeyeceği için bu
istemci tarafı bir UX kolaylığı, güvenlik sınırı DEĞİL — asıl güvenlik
sınırı backend'in kendisinde (`is_path_allowed` + committed-only
kontrolü). (saga-oto tarafından otomatik seçildi)

**S5: İstek başarısız olursa (network hatası, 404, 409) UI'da ne
olmalı?** Cevap: Yeni bir `ResultCard` YOK — mevcut kartın İÇİNDE bir
hata metni `aria-live="polite"` bölgesinde gösterilir (PlanCard'ın
`statusText` deseniyle tutarlı), buton yeniden etkinleşir (kullanıcı
tekrar deneyebilsin). (saga-oto tarafından otomatik seçildi)

## Kabul Kriterleri
1. **AC-1 (kritik):** `POST /api/transactions/{id}/revert` var,
   `allowedRoot`u `revert_transaction`e geçiriyor, committed-olmayan
   transaction'ı 409 ile reddediyor, bilinmeyen id'yi 404 ile
   reddediyor, fiziksel başarısızlığı 200 + `revert_failed` ile
   döndürüyor.
2. **AC-2 (kritik):** `ResultCard`, `transactionId` VE `selectedFolder`
   ikisi de verilmişse bir "Geri al" butonu gösteriyor; ikisinden biri
   eksikse GÖSTERMİYOR.
3. **AC-3 (yüksek):** Butona TEK tıklama isteği GÖNDERMİYOR — önce bir
   "Emin misiniz?" onay adımına geçiyor, SADECE ikinci ("Evet, geri
   al") tıklama gerçek isteği tetikliyor. "Vazgeç" ilk duruma dönüyor.
4. **AC-4 (yüksek):** Başarılı geri alma SONRASI yeni bir sonuç mesajı
   (`aria-live` bölgesinde) gösteriyor; başarısız istek/ağ hatası
   butonu tekrar etkinleştirip bir hata metni gösteriyor.

## Riskler / Varsayımlar / Bilinmeyenler
- Gerçek bir apply endpoint'i (Saga #287) hâlâ yok — bu yüzden
  `ResultCard`'ın `transactionId`/`selectedFolder` prop'larını GERÇEKTEN
  dolduran bir `ChatScreen` akışı da henüz yok; bu task sadece
  BİLEŞENİN/endpoint'in kendisini doğru inşa ediyor, uçtan uca gerçek
  kullanıcı akışına bağlanması AYRI (Saga #287 sonrası) bir iş.

## Test Stratejisi
Backend: `test_main_integration.py`e yeni testler (404/409/200-reverted/
200-revert_failed senaryoları, in-memory DB + gerçek geçici dosyalarla).
Frontend: `ResultCard.test.tsx`e yeni testler (buton görünürlüğü, iki
aşamalı onay, başarılı/başarısız fetch senaryoları — `vi.stubGlobal('fetch', ...)`).
