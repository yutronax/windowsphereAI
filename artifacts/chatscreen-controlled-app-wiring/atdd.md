---
task_slug: chatscreen-controlled-app-wiring
priority: high
coverage_target: "70/0/30"
performance_target: "yok"
test_strategy: "unit (React Testing Library, gerçek fetch mock)"
affected_modules:
  - ui/src/components/chat/ChatScreen.tsx
  - ui/src/App.tsx
saga_task_id: 287
epic_id: 25
---

# ATDD — ChatScreen Controlled + App.tsx Wiring (Saga #287)

## Goal
`ChatScreen`'in mesaj listesini tamamen kendi iç state'inde tutması
nedeniyle `App.tsx`'in asenkron bir `/api/plan` yanıtını sohbete
yansıtmasının mümkün olmadığı mimari boşluğu kapatmak; `App.tsx`'i
gerçekten `/api/plan`'a bağlamak.

## Sorular ve Cevaplar (saga-oto tarafından otomatik seçildi)

**S1: `ChatScreen` tamamen controlled'a mı çevrilsin, yoksa dual-mode mu
olsun?** Cevap: Dual-mode (`messages`/`onMessagesChange` prop'ları
verilirse controlled, verilmezse mevcut `initialMessages` ile
uncontrolled davranış aynen kalır). Gerekçe: mevcut 30+ test
`initialMessages` + iç state varsayımıyla yazılmış; tamamen controlled'a
zorlamak bu testlerin TAMAMINI kırardı — dar kapsam ilkesi, gereksiz
kırılma yaratmadan gerçek ihtiyacı (App.tsx'in dışarıdan mesaj
ekleyebilmesi) karşılıyor. (saga-oto tarafından otomatik seçildi)

**S2: `/api/plan`'dan dönen 403/404/410/502/503 gibi hatalar nasıl
gösterilecek?** Cevap: Mevcut `planError`/`plan-error-indicator`
mekanizmasına (Saga #267, zaten test edilmiş) yönlendirilecek — yeni bir
hata gösterim mekanizması icat EDİLMEYECEK. `PlanCard`'ın
`securityStatus: 'rejected'` dalı bugün network hatalarından değil,
teorik olarak backend'in gelecekte 200 içinde "rejected" bir plan
dönmesi ihtimaline karşı zaten var (backend bunu hiç yapmıyor, whitelist
ihlali her zaman 4xx döner) — bu task bunu değiştirmiyor. (saga-oto
tarafından otomatik seçildi, dar kapsam)

**S3: `onApprovePlan` gerçek bir Orchestrator/apply çağrısı yapsın mı?**
Cevap: Hayır — `apply_plan` (Saga #274) kasıtlı olarak endpoint'siz.
`onApprovePlan` şimdilik sadece `console.info` ile logluyor (no-op).
Gerçek apply-endpoint wiring'i ayrı bir task. (saga-oto tarafından
otomatik seçildi — task açıklamasında zaten böyle belirtilmiş)

## Kabul Kriterleri
1. **AC-1 (kritik):** `ChatScreen`, `messages`/`onMessagesChange`
   prop'ları verildiğinde CONTROLLED çalışır — kendi iç state'i yerine
   dışarıdan gelen `messages`'ı render eder, her değişiklikte
   `onMessagesChange` çağrılır.
2. **AC-2 (kritik):** `messages` prop'u verilmediğinde (mevcut tüm
   testler) davranış AYNEN eskisi gibi kalır (regresyon YOK).
3. **AC-3 (kritik):** `App.tsx`, mesaj gönderildiğinde gerçekten
   `POST /api/plan` çağırır (sessionId ile), yanıtı yeni bir assistant
   `ChatMessage.plan`'ına (`securityStatus: 'approved'`) yazar.
4. **AC-4 (yüksek):** İstek sürerken `isGeneratingPlan=true`; başarısız
   olursa `planError` set edilir, mevcut hata/retry UI'ı (Saga #267)
   devreye girer.
5. **AC-5 (yüksek):** `onApprovePlan`, gerçek bir network çağrısı
   YAPMAZ (Orchestrator henüz yok) — sadece loglar.

## Riskler / Varsayımlar / Bilinmeyenler
- Gerçek bir Tauri ortamında (backend `http://127.0.0.1:8000`) uçtan uca
  manuel doğrulama bu oturumda yapılamadı — sadece component-seviyesinde
  mock `fetch` ile test edildi.
- "Tekrar dene" (Saga #267) butonunun son gönderilen mesajı tekrar
  denemesi gerekiyor — `App.tsx`'in `onRetry`'ı son kullanıcı mesajını
  saklayıp yeniden `/api/plan` çağırmalı.

## Test Stratejisi
`ChatScreen.test.tsx`'e controlled-mode testleri; `App.test.tsx`'e
(mevcut dosya) `global.fetch` mock'lanarak gerçek uçtan uca akış testleri
(gönder→plan geldi, hata→planError, retry).
