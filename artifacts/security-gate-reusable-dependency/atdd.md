---
task_slug: security-gate-reusable-dependency
priority: low
coverage_target: "70/0/30"
performance_target: "yok"
test_strategy: "unit + FastAPI TestClient"
affected_modules:
  - backend/main.py
  - backend/security.py
saga_task_id: 283
epic_id: 25
---

# ATDD — Security Gate Reusable Dependency (Saga #283)

## Goal
`/api/plan`'a gömülü session-lookup'ı yeniden kullanılabilir bir
FastAPI `Depends` haline getirmek; `PathWhitelistError`'ı yapılandırılmış
alanlar taşıyacak şekilde genişletmek.

## Sorular ve Cevaplar (saga-oto tarafından otomatik seçildi)

**S1: `get_session_or_404` sessionId'yi nereden alacak?** Cevap:
`PlanRequest` body'sinden — Saga #285'ten sonra `PlanRequest` sadece
`sessionId` taşıyor, `create_plan`'ın artık `payload`'a ihtiyacı yok
(pdfFiles kaldırıldı). `get_session_or_404(payload: PlanRequest) ->
SessionContext` dependency'si body'yi kendisi parse eder, endpoint
sadece çözümlenmiş `SessionContext`'i alır. (saga-oto tarafından
otomatik seçildi — mevcut şemayla en az sürtünmeli entegrasyon)

**S2: `PathWhitelistError`'a hangi alanlar eklenmeli?** Cevap:
`offending_path: str`, `allowed_root: str`, `reason: str` — mesaj
string'i bunlardan otomatik üretiliyor (`__str__` override), ama
main.py artık bu alanlara ayrı ayrı erişip istemciye ne kadarını
göstereceğine bağımsız karar verebiliyor (info-disclosure riski, Saga
#271 red-team notu). Bu task'ta main.py'nin DAVRANIŞI değişmiyor (hâlâ
tam mesajı 403 detail'e koyuyor) — sadece YAPI kuruluyor, gelecekteki
bir karar (mesajı kısaltma) için altyapı hazırlanıyor. (saga-oto
tarafından otomatik seçildi, dar kapsam — davranış değişikliği ayrı
karar)

## Kabul Kriterleri
1. **AC-1 (kritik):** `get_session_or_404` bağımsız bir `Depends`
   fonksiyonu — `/api/plan` bunu kullanıyor, session bulunamazsa hâlâ
   404 dönüyor (regresyon yok).
2. **AC-2 (yüksek):** `PathWhitelistError` artık `offending_path`,
   `allowed_root`, `reason` alanlarını taşıyor; `str(exc)` hâlâ önceki
   okunabilir mesaj formatını üretiyor (mevcut testler kırılmıyor).
3. **AC-3 (orta):** Tüm mevcut backend testleri (105) değişmeden geçiyor.

## Riskler / Varsayımlar / Bilinmeyenler
- `get_session_or_404` şu an sadece `/api/plan`'da kullanılıyor —
  gerçek "tekrar kullanım" ancak gelecekte yeni bir dosya-dokunan
  endpoint eklenince (ör. apply endpoint) kanıtlanacak.

## Test Stratejisi
Mevcut `test_main_integration.py` testleri (regresyon), yeni
`PathWhitelistError` alan testleri `test_security.py`'de.
