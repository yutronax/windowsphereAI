# Plan — dikey-mesaj-akisi (Saga #259)

## Değiştirilecek dosyalar
- **Yeni** `ui/src/components/chat/ChatScreen.tsx` — mesaj listesi + sabit alt yazma alanı.
- **Yeni** `ui/src/components/chat/ChatScreen.test.tsx` — 7 unit test.
- **Değişecek** `ui/src/App.tsx` — placeholder `<main data-testid="main-chat-screen">` yerine `<ChatScreen />` render edilecek, testid ChatScreen içinde korunacak.

## Bağımlılıklar
Yeni npm paketi yok — mevcut React/RTL/vitest altyapısı yeterli.

## Migrasyon
Yok (UI-only, backend/DB dokunulmuyor).

## Riskler
- `App.test.tsx` `main-chat-screen` testid'ine bağlı — ChatScreen kök elemanına aynı
  testid taşındı, regresyon riski yok (test edildi).
