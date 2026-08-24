# Plan — Çoklu Geçmiş Transaction Listesi UI'ı

## Dosya Değişiklikleri

### ui/src/components/chat/HistoryPanel.tsx (yeni)
- `SearchPanel.tsx`'in fetch/loading/error state deseniyle AYNI iskelet.
- Prop: yok (ya da opsiyonel `onClose`) — `sessionId` GEREKMEZ, `GET
  /api/transactions` sessionId almıyor (Saga #294 kararı: global liste).
- Mount olduğunda (her açılışta yeniden mount edilir, bkz. ChatScreen
  wiring) `GET /api/transactions` çağırır.
- State: `'loading' | 'loaded' | 'error'`.
- Render: liste boşsa "Henüz bir işlem geçmişi yok.", her satırda
  `id`/`createdAt`/`status`/`fileCount`/`targetFolders` + `preview`
  (ResultCard'daki `empty`/`available===false`/normal liste üç-durumlu
  render mantığının panel-satırı için kopyası — `PreviewFile`/`Preview`
  tipleri `ResultCard.tsx`'ten YENİDEN TANIMLANIR, import edilmez, iki
  bileşen birbirinden bağımsız kalır).

### ui/src/components/chat/ChatScreen.tsx
- `isHistoryPanelOpen` state'i eklenir (`isSearchPanelOpen` ile aynı
  desen).
- `chat-search-toggle-button`/`chat-clear-history-button` yanına üçüncü
  buton: `chat-history-toggle-button` ("Geçmiş" / "Geçmişi kapat").
- `{isHistoryPanelOpen && <HistoryPanel />}` — `SearchPanel`in
  `{isSearchPanelOpen && sessionId && <SearchPanel ... />}` satırının
  hemen altına, `sessionId` koşulu YOK (panel session'dan bağımsız).
- Panel her `isHistoryPanelOpen` `true` olduğunda yeniden mount edilir
  (React key/conditional-render zaten bunu sağlıyor — AC7 "yeniden aç ->
  yeniden fetch" için ekstra kod GEREKMEZ, conditional mount'un doğal
  sonucu).

## Test Dosyaları
- `ui/src/components/chat/HistoryPanel.test.tsx` (yeni) — AC1-AC7'yi
  kapsayan RTL testleri, `ResultCard.test.tsx`'in mock-fetch desenini
  izler.
- `ui/src/components/chat/ChatScreen.test.tsx` — mevcut dosyaya
  toggle-buton görünürlüğü/aç-kapa testleri eklenir (dosya zaten varsa).

## Bağımlılık
Yeni bağımlılık yok. Backend değişikliği yok.

## Doğrulama Sırası
1. Kırmızı: `HistoryPanel.test.tsx` yazılır, `HistoryPanel.tsx` henüz
   yokken/eksikken testler FAIL eder.
2. Yeşil: `HistoryPanel.tsx` + `ChatScreen.tsx` wiring'i eklenir, testler
   PASS eder.
3. Regresyon: `npm test` ile TÜM frontend suite'i (`ResultCard.test.tsx`,
   `ChatScreen.test.tsx` dahil) çalıştırılır.
4. Bağımsız red-team incelemesi.
