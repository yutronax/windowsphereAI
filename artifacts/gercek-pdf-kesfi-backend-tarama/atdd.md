---
task_slug: gercek-pdf-kesfi-backend-tarama
priority: high
coverage_target: "70/0/30 (unit/integration/e2e)"
performance_target: "yok"
test_strategy: "unit + FastAPI TestClient entegrasyon testleri"
affected_modules:
  - backend/pdf_discovery.py (yeni)
  - backend/models.py (PlanRequest)
  - backend/main.py (/api/plan)
saga_task_id: 285
epic_id: 25
---

# ATDD — Gerçek PDF Keşfi: Backend Tarama (Saga #285)

## Goal
`PlanRequest.pdfFiles` istemciden kaldırılıp, backend'in
`session.selectedFolder`'ı kendisi taraması sağlanmalı — bu, epic 25'in
"uçtan uca dosya operasyonu" için gerçek bir önkoşuldu (Saga #273/#277
keşiflerinde bulundu).

## Sorular ve Cevaplar (saga-oto tarafından otomatik seçildi)

**S1: Backend mi tarasın, yoksa frontend Tauri fs plugin mi eklesin?**
Cevap: Backend tarasın. Gerekçe: (a) yeni bir native bağımlılık
gerektirmiyor (dar kapsam ilkesi), (b) whitelist doğrulamasının
güvendiği "kaynak dosya" listesini istemcinin kontrolünden çıkarıp
backend'in kendi taramasına devrediyor — daha az güven sınırı.
(saga-oto tarafından otomatik seçildi)

**S2: Alt klasörler taranmalı mı (recursive)?**
Cevap: Hayır, sadece `selectedFolder`'ın DOĞRUDAN altı. Gerekçe: Saga
#272'nin derinlik/whitelist kısıtlarıyla tutarlı — taşınacak dosyalar
zaten kullanıcının seçtiği kökte olmalı, recursive tarama kapsamı
büyütür ve varsayılan davranışı belirsizleştirir. (saga-oto tarafından
otomatik seçildi, dar kapsam)

**S3: `createdAt` neyden türetilecek?**
Cevap: `Path.stat().st_ctime` (dosya oluşturulma zaman damgası,
Windows'ta gerçek oluşturulma zamanı). ISO 8601 UTC string'e çevrilir.
(saga-oto tarafından otomatik seçildi — DESIGN_DECISIONS.md'de
`dateSource: created_at` zaten bu varsayımı yapıyordu, Saga #269/#270)

## Kabul Kriterleri
1. **AC-1 (kritik):** `POST /api/plan` artık `pdfFiles` alanı BEKLEMİYOR
   (sadece `sessionId`) — gönderilirse yok sayılır (Pydantic fazla alanı
   sessizce görmezden gelir, model'de tanımlı değil).
2. **AC-2 (kritik):** Backend, session'ın `selectedFolder`'ının DOĞRUDAN
   altındaki `.pdf` (case-insensitive) dosyalarını bulup plan üretimine
   ve whitelist doğrulamasına verir.
3. **AC-3 (yüksek):** Alt klasörler taranmaz; `.pdf` olmayan dosyalar
   yok sayılır.
4. **AC-4 (yüksek):** Seçili klasörde hiç PDF yoksa boş bir plan
   (steps=[]) döner, hata fırlatmaz.
5. **AC-5 (kritik):** Bulunan bir PDF'in kendisi sistem-korumalı bir
   kök altına denk gelirse (Saga #272), whitelist yine reddeder — bu
   koruma pdfFiles kaynağı değişse de bozulmamalı.

## Riskler / Varsayımlar / Bilinmeyenler
- **Mimari boşluk bulundu (kapsam dışına alındı):** `ChatScreen.tsx`
  mesaj listesini tamamen kendi iç state'inde tutuyor —
  `initialMessages` sadece mount anında okunuyor, App.tsx'in sonradan
  (asenkron bir `/api/plan` yanıtıyla) yeni bir asistan mesajı
  eklemesinin HİÇBİR yolu yok. Gerçek uçtan uca wiring
  (`App.tsx`→`/api/plan`→`ChatScreen`) bu yüzden `ChatScreen`'in
  "controlled component"a çevrilmesini gerektiriyor — bu, bu task'ın
  kapsamını (backend tarama) aşan ayrı bir frontend refactor'ü. Takip
  task'ı açıldı (bkz. AI_DEVLOG).

## Test Stratejisi
`backend/tests/test_pdf_discovery.py` (7 unit test) +
`backend/tests/test_main_integration.py` güncellemesi (gerçek `tmp_path`
üzerinde dosya oluşturup `/api/plan` üzerinden uçtan uca doğrulama).
