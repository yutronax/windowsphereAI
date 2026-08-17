---
task_slug: orchestrator-planstep-dosya-listesi-ve-kurtarma
priority: high
coverage_target: "70/0/30"
performance_target: "yok"
test_strategy: "unit (pytest, tmp_path + in-memory sqlite)"
affected_modules:
  - backend/models.py (PlanStep)
  - backend/plan_generation.py (prompt)
  - backend/orchestrator.py (_distribute_files_to_steps, recover_incomplete_transactions)
saga_task_id: 286
epic_id: 25
---

# ATDD — PlanStep Dosya Listesi + Crash-Recovery (Saga #286)

## Goal
Saga #274 red-team'in bulduğu iki mimari riski kapatmak: (1) `PlanStep`
hangi dosyanın kendisine ait olduğunu artık AÇIKÇA taşısın (sıralı
dağıtım varsayımı kaldırılsın), (2) süreç `apply_plan` sırasında çökerse
bir sonraki başlangıçta yarım kalmış transaction'lar tespit edilip
tutarlı bir duruma getirilsin.

## Sorular ve Cevaplar (saga-oto tarafından otomatik seçildi)

**S1: `PlanStep`e dosya listesi nasıl eklenmeli — `fileNames: list[str]`
mi, dosya ID'si mi?** Cevap: `fileNames: list[str]`. Gerekçe: proje şu an
dosyalar için ayrı bir ID/DB kaydı üretmiyor (PdfFileMetadata sadece
filename+createdAt), ID eklemek gereksiz bir soyutlama olurdu; filename
zaten `selectedFolder` içinde tekil (aynı klasörde iki dosya aynı ada
sahip olamaz). (saga-oto tarafından otomatik seçildi, dar kapsam)

**S2: `affectedFileCount` kaldırılsın mı, yoksa `fileNames` ile birlikte
mi tutulsun?** Cevap: Tutulsun, ama artık `len(fileNames)` ile eşleşmesi
ZORUNLU (field_validator). Gerekçe: `affectedFileCount` zaten
`PlanCard.tsx`'te UI'da gösteriliyor (frontend'i kırmadan bırakmak
için), ama artık `fileNames`'ten türeyen bir doğrulanmış alan haline
geliyor — LLM'in iki alanı tutarsız üretmesi (say 3 ama liste 2 eleman)
şema seviyesinde reddedilir. (saga-oto tarafından otomatik seçildi)

**S3: Crash-recovery hangi düzeyde olmalı — tam bir "process restart'ta
otomatik tarama" mı, yoksa çağrılabilir bir fonksiyon mu?** Cevap:
Çağrılabilir bir fonksiyon (`recover_incomplete_transactions`), gerçek
bir FastAPI startup event'ine bağlamak KAPSAM DIŞI — çünkü hiçbir apply
endpoint'i henüz yok (Saga #285'in devamı, #287), bağlanacak gerçek bir
uygulama başlatma akışı yok. Fonksiyon saf, test edilebilir, ileride
tek satırla `@app.on_event("startup")`a bağlanabilir. (saga-oto
tarafından otomatik seçildi, dar kapsam — "gerçek entegrasyon ayrı task")

## Kabul Kriterleri
1. **AC-1 (kritik):** `PlanStep.fileNames: list[str]` — LLM prompt'u
   buna göre güncellendi, her step hangi `pdf_files` girdisine karşılık
   geldiğini AÇIKÇA belirtiyor.
2. **AC-2 (kritik):** `affectedFileCount != len(fileNames)` ise Pydantic
   `ValidationError` (plan üretimi `PlanGenerationError`'a düşer).
3. **AC-3 (kritik):** `orchestrator.py`'deki `_distribute_files_to_steps`
   artık pozisyonel dağıtım YAPMIYOR — her step'in `fileNames`'i,
   `pdf_files` listesindeki gerçek `PdfFileMetadata` nesneleriyle
   filename eşleşmesiyle çözülüyor. Bir step'in `fileNames`'inde
   `pdf_files`'ta OLMAYAN bir isim varsa, ya da `pdf_files`'ta olup
   HİÇBİR step'e atanmamış bir dosya varsa, tüm plan reddedilir
   (`PlanApplicationError`).
4. **AC-4 (yüksek):** `recover_incomplete_transactions(session,
   allowed_root)` — DB'de `status="pending"` olan `Transaction`'ları
   bulur, her birinin `FileOperation`'larını `destination_path`'in
   fiziksel olarak var olup olmadığına göre uzlaştırır: varsa
   `"completed"`, yoksa `"rolled_back"` (hiç taşınmamış demektir)
   işaretler, `transaction.status`'u duruma göre günceller.

## Riskler / Varsayımlar / Bilinmeyenler
- `recover_incomplete_transactions` gerçek bir startup hook'una
  bağlanmadı — bu, gelecekteki bir apply-endpoint task'ının (Saga #287
  sonrası) sorumluluğu.
- Mevcut LLM promptu JSON-only zorluyor; `fileNames` eklenmesi prompt'un
  daha karmaşık hale gelmesi anlamına geliyor — gerçek bir LLM ile uçtan
  uca test edilemedi (LLM istemcisi stub'lanıyor, sadece şema uyumu test
  edildi).

## Test Stratejisi
`backend/tests/test_plan_generation.py` (prompt/şema), `backend/tests/
test_orchestrator.py` (dağıtım + recovery), pytest + tmp_path + in-memory
sqlite.
