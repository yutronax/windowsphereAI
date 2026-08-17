# Verify Report — "Son İşlemi Geri Al" UI'ı (Saga #295)

## Test Sonuçları
- Backend: `pytest backend/tests -q` → **154/154 PASSED** (8 yeni test:
  404 bilinmeyen id, 409 committed-olmayan durum + hiçbir dosyaya
  dokunulmaması, 200+`reverted` gerçek dosya sistemi doğrulamasıyla,
  200+`revert_failed` gerçek OSError tetikleyen bir senaryoyla).
- Frontend: `vitest run` → **135/135 PASSED** (16'sı `ResultCard.test.tsx`
  içinde, 11'i bu task'ın yeni testleri: buton görünürlük/gizlilik
  koşulları, iki aşamalı onay [ilk tık istek GÖNDERMİYOR, vazgeç geri
  dönüyor], başarılı revert sonrası aria-live mesajı, kısmi başarısız
  revert mesajı, HTTP-hata ve network-hatası senaryolarında butonun
  tekrar etkinleşmesi).
- `tsc --noEmit` → temiz, hiçbir tip hatası yok.

## Kabul Kriterleri Durumu
- AC-1 (kritik): ✅ `POST /api/transactions/{id}/revert` — 404/409/200
  (reverted)/200 (revert_failed) hepsi test edildi.
- AC-2 (kritik): ✅ Buton SADECE `transactionId` VE `selectedFolder`
  ikisi de verildiğinde görünüyor (3 ayrı test: ikisi eksik, biri
  eksik, ikisi de var).
- AC-3 (yüksek): ✅ Tek tıklama istek GÖNDERMİYOR (`fetchSpy` çağrılmadı
  doğrulandı), ikinci tıklama gönderiyor, "Vazgeç" ilk duruma dönüyor.
- AC-4 (yüksek): ✅ Başarı/kısmi-başarısızlık/ağ-hatası hepsi
  `aria-live="polite"` içinde farklı mesajlarla gösteriliyor, hata
  durumunda buton "Tekrar dene" ile yeniden etkinleşiyor.

## Red-Team Bulgusu ve Düzeltmesi
`obss-red-team` bloklayıcı bir bulgu bulmadı. Üç düşük-önem bulgu:
(1) `allowedRoot` istemciden geliyor, sahte/geniş bir değer path-
containment kontrolünü etkisiz kılabilir — ama HANGİ dosyaların
işleneceği zaten DB'deki `transaction.operations` satırlarıyla SABİT,
`allowedRoot` sadece containment'ı etkiliyor; mimari bir öneri olarak
**Saga #301** takip task'ı açıldı (bloklamadı, uygulama zaten authsız
tek-kullanıcılı). (2) Eşzamanlı iki revert isteği için TOCTOU/kilitleme
yok — tek-kullanıcılı yerel masaüstü uygulaması için kabul edilebilir
risk, ikinci istek `destination_path.exists()` kontrolü sayesinde
zaten "başarılı" (no-op) döner, veri kaybına yol açmaz. (3) Frontend'de
`handleConfirmRevert`in render zamanlamasına GÜVENEREK çift-tıklamayı
engellemesi — HEMEN düzeltildi: `revertState === 'reverting'` erken
çıkışı eklendi (render zamanlamasından bağımsız bir garanti). 135/135
frontend testi bu düzeltmeden sonra da yeşil kaldı.

## Sonuç
`ready_to_commit: evet`
