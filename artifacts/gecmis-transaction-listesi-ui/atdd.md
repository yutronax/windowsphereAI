---
task_slug: gecmis-transaction-listesi-ui
priority: low
coverage_target: "70/30/0"
performance_target: "yok"
test_strategy: "unit (RTL, mock fetch) + var olan preview davranışının aynen taşınması"
affected_modules:
  - ui/src/components/chat/HistoryPanel.tsx (yeni)
  - ui/src/components/chat/ChatScreen.tsx
saga_task_id: null
epic_id: 28
---

# ATDD — Çoklu Geçmiş Transaction Listesi UI'ı

## Kaynak
Saga #317 (diff-tray-onizleme-ui) kapsam dışı bırakmıştı: "kod
taramasında ortaya çıktı: `GET /api/transactions` frontend'de hiç
tüketilmiyordu, `ResultCard.tsx` sadece en son tamamlanan TEK
transaction'ı gösteriyordu... çoklu geçmiş listesi UI'ı ayrı bir Saga
task'ına bırakıldı." Bu görev o ayrılan işi kapatır.

## Persona
windows-ai-files kullanıcısı; sadece son işlemi değil, GEÇMİŞTEKİ TÜM
işlemleri görmek/gözden geçirmek isteyen kişi.

## Goal
`ChatScreen`'de, `SearchPanel`/`Geçmişi Temizle` ile AYNI desende (bir
toggle butonu + açılır panel) `GET /api/transactions`'ın döndürdüğü TÜM
transaction'ları listeleyen bir panel. `ResultCard`'daki tekil-kart
önizlemesi DEĞİŞMEZ — bu panel ONA EK, sohbet akışının dışında ayrı bir
görünüm.

## Sorular ve Cevaplar (dar kapsam ilkesiyle otomatik seçildi)
1. **Panel nereye/nasıl açılır?** `SearchPanel`/`Geçmişi Temizle` ile
   BİREBİR AYNI desen: `chat-search-toggle-button` yanına üçüncü bir
   toggle butonu (`chat-history-toggle-button`, "Geçmiş"/"Geçmişi
   kapat"), `isSearchPanelOpen` ile AYNI türden bir `isHistoryPanelOpen`
   state'i. Ayrı bir route/modal YOK.
2. **Veri nereden gelir?** Mevcut `GET /api/transactions` — Saga #294'te
   eklendi, Saga #317'de `preview` alanıyla zenginleştirildi. YENİ bir
   endpoint YOK.
3. **Önizleme (hover) davranışı bu listede de olacak mı?** Evet, ama
   `ResultCard`'daki gibi AYRI bir fetch YOK — `GET /api/transactions`
   TEK çağrısı zaten her transaction için `preview` alanını içeriyor,
   panel açıldığında bir kez çekilir, hover'da ekstra istek YAPILMAZ
   (ResultCard'ın "lazy, tek seferlik" deseninden farklı: burada veri
   zaten elde, sadece görünürlük CSS/state ile kontrol edilir).
4. **`Geçmişi Temizle` ile ilişkisi?** `GET /api/transactions` zaten
   `historyClearedBeforeId` eşiğini uyguluyor (Saga #318) — bu panel o
   filtrelenmiş listeyi olduğu gibi gösterir, KENDİ bir filtre mantığı
   EKLEMEZ.
5. **Silinmiş/purge edilmiş backup'lar?** `TransactionPreview.available
   === false` durumu `ResultCard`'daki AYNI "Önizleme mevcut değil"
   mesajıyla gösterilir — mantık TEKRARLANMAZ, aynı render deseni
   kopyalanır (ayrı bileşen, aynı davranış).
6. **Boş liste?** "Henüz bir işlem geçmişi yok." mesajı — hata değil,
   sessiz boş ekran değil.

## Acceptance Criteria (öncelik sırasıyla)
- AC1 (P0, Critical): `ChatScreen`'de `sessionId` verildiğinde "Geçmiş"
  toggle butonu görünür (`SearchPanel`/`Geçmişi Temizle` butonlarıyla
  aynı satırda). Tıklanınca `HistoryPanel` açılır/kapanır.
- AC2 (P0, Critical): `HistoryPanel` açıldığında `GET /api/transactions`
  çağrılır, dönen HER transaction için: `id`, `createdAt` (okunabilir
  biçimde), `status`, `fileCount`, `targetFolders` gösterilir.
- AC3 (P0, Critical): Yükleme sırasında "Yükleniyor…" durumu; istek
  başarısız olursa "Geçmiş yüklenemedi." hata mesajı (sessiz başarısızlık
  YOK) gösterilir.
- AC4 (P1, High): Liste boşsa "Henüz bir işlem geçmişi yok." mesajı
  gösterilir (ne hata ne sessiz boşluk).
- AC5 (P1, High): Her transaction satırında, `preview.empty` /
  `preview.available === false` / normal dosya listesi ayrımı
  `ResultCard`'daki AYNI üç durumla (mesaj metinleri dahil) gösterilir —
  path SIZDIRILMAZ (sadece dosya adı).
- AC6 (P2, Medium): En yeni transaction en üstte (backend zaten bu
  sırayla döndürüyor — Saga #294 `ORDER BY created_at DESC` — bu AC
  sadece frontend'in sırayı KORUDUĞUNU, yeniden SIRALAMADIĞINI
  doğrular).
- AC7 (P2, Medium): Panel kapatılıp yeniden açıldığında liste TAZELENİR
  (yeniden fetch edilir) — kapalıyken oluşan yeni bir transaction bir
  sonraki açılışta görünür.

## Davranış Sözleşmesi
| Durum | Beklenen |
|---|---|
| Panel ilk açılış, başarılı yanıt, N transaction | Liste render edilir, en yeni üstte |
| Panel açılış, backend 500/network hatası | "Geçmiş yüklenemedi." hata mesajı, panel çökmez |
| Panel açılış, boş liste (`[]`) | "Henüz bir işlem geçmişi yok." |
| Bir transaction'ın `preview.empty === true` | O satırda "Değişiklik yok" |
| Bir transaction'ın `preview.available === false` | O satırda "Önizleme mevcut değil" |
| Panel kapat → tekrar aç | Yeni bir `GET /api/transactions` çağrısı yapılır |

## Kapsam Dışı
- Sayfalama/sonsuz kaydırma (liste zaten `historyClearedBeforeId` ile
  sınırlı, büyük hacim şu an bilinen bir sorun değil).
- Tekil transaction'ı bu panelden GERİ ALMA (`revert`) — bu buton SADECE
  `ResultCard`'da kalır, panel salt-okunur bir gözden geçirme aracı.
- Filtreleme/arama (bu panelin kapsamı SADECE listeleme).

## Test Strategy
Unit — React Testing Library, `fetch` mock (`ResultCard.test.tsx`'in
kullandığı desenle aynı). Backend'de yeni bir değişiklik YOK (endpoint
zaten var, test edilmiş), bu yüzden backend testi eklenmiyor.

## Risks / Assumptions
- Assumption: `preview` render mantığının `ResultCard`'dan panel'e
  kopyalanması (ortak bir alt-bileşene çıkarılması YERİNE) bilinçli — iki
  bileşenin görsel bağlamı farklı (kart içi vs liste satırı), paylaşılan
  bir soyutlama bu dar görev için erken optimizasyon olur.
