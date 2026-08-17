---
task_slug: plan-generation-coklu-operasyon-destegi
priority: medium
coverage_target: "70/0/30"
performance_target: "yok"
test_strategy: "unit (pytest, sahte LLM istemcisi)"
affected_modules:
  - backend/plan_generation.py
  - backend/main.py
saga_task_id: 292
epic_id: 26
---

# ATDD — plan_generation.py Çoklu Operasyon Desteği (Saga #292)

## Goal
LLM'in kullanıcının doğal dil isteğine göre doğru `operationType`'ı
seçebilmesini sağlamak. Kod keşfinde bulunan GERÇEK ve ÖNCELİKLİ boşluk:
`generate_plan_skeleton` kullanıcının `requestText`'ini (session'da zaten
var) HİÇ ALMIYOR — LLM sadece dosya adı+tarih görüyor, "PDF'leri sırala"
mı "yedekle" mi "sil" mi istendiğini bilme imkânı yok. Bu, epic 26'daki
COPY/DELETE/RENAME/LIST implementasyonlarının HİÇBİRİNİN gerçek
kullanıcı isteğiyle asla tetiklenemeyeceği anlamına geliyor.

## Sorular ve Cevaplar (saga-oto tarafından otomatik seçildi)

**S1: `requestText` prompt'a nasıl eklenmeli?** Cevap:
`generate_plan_skeleton`'a yeni bir `request_text: str` parametresi
eklenir, `build_metadata_prompt` bunu prompt'un başına ekler.
`main.py`'nin `create_plan`'ı `session.requestText`'i geçirir (session
zaten bu veriyi taşıyor, sadece kullanılmıyordu). (saga-oto tarafından
otomatik seçildi — mevcut veri akışına en az sürtünmeli entegrasyon)

**S2: PLAN_SYSTEM_PROMPT'a hangi eşleme rehberi eklenmeli?** Cevap:
Kaba bir doğal-dil→operationType eşlemesi: "taşı/sırala/organize et" →
Taşı (varsayılan), "kopyala/yedekle/çoğalt" → Kopyala, "sil/temizle/
kaldır" → Sil, "yeniden adlandır/ismini değiştir" → Yeniden Adlandır,
"listele/göster/say" → Listele. LLM'in yorumlamasına güvenilir (katı
bir regex/keyword eşleştirici YAZILMIYOR — bu, LLM'in doğal dil
anlama gücünü kullanmanın amacı). (saga-oto tarafından otomatik seçildi)

**S3: RENAME için prompt `newFileNames` üretimini nasıl açıklamalı?**
Cevap: Şema açıklamasına `newFileNames` alanı eklenir — SADECE
`operationType` "Yeniden Adlandır" olduğunda dolu olmalı, `fileNames`
ile aynı uzunlukta ve sırada, path separator içermemeli. (saga-oto
tarafından otomatik seçildi — Saga #290'ın şema kısıtlarıyla birebir
tutarlı)

**S4: DELETE/RENAME/LIST için `targetFolder` LLM'e nasıl açıklanmalı
(şema zorunlu ama semantik olarak kullanılmıyor)?** Cevap: Prompt'a
açık bir not eklenir — bu operationType'larda `targetFolder`'ın
GERÇEKTEN kullanılmadığı ama şema gereği yine de geçerli bir YYYY-MM
string'i (ör. dosyaların oluşturulma ayı) olması gerektiği belirtilir.
(saga-oto tarafından otomatik seçildi — Saga #289/#290/#291'in "bilinen
sınırlama" notlarıyla tutarlı, dar kapsam: şema değişikliği YOK, sadece
prompt açıklaması)

## Kabul Kriterleri
1. **AC-1 (kritik):** `generate_plan_skeleton` artık `request_text`
   parametresi alıyor, `build_metadata_prompt` bunu LLM'e iletiyor.
2. **AC-2 (kritik):** `main.py: create_plan`, `session.requestText`'i
   `generate_plan_skeleton`'a geçiriyor.
3. **AC-3 (yüksek):** `PLAN_SYSTEM_PROMPT`, tüm 5 operationType için
   doğal-dil eşleme rehberi + `newFileNames` şema açıklaması içeriyor.
4. **AC-4 (orta):** Mevcut tüm testler (boş `pdf_files` kısayolu,
   şema validasyonu vb.) `request_text` parametresi eklenmesinden
   etkilenmeden geçmeye devam ediyor.

## Riskler / Varsayımlar / Bilinmeyenler
- Gerçek bir LLM'in yeni prompt'la COPY/DELETE/RENAME/LIST'i doğru
  seçtiği bu oturumda UÇTAN UCA doğrulanamadı (LLM istemcisi testlerde
  stub'lanıyor) — bu, canlı bir DeepSeek testiyle ayrıca doğrulanmalı
  (kullanıcı isterse).
- `requestText`'in boş/whitespace olamayacağı zaten `SessionRequest`
  seviyesinde garanti (Saga #256) — `generate_plan_skeleton` bunu
  ayrıca doğrulamıyor, session'dan geldiği için güvenilir kabul ediliyor.

## Test Stratejisi
`backend/tests/test_plan_generation.py`: `request_text`'in prompt'a
gerçekten eklendiğini doğrulayan test (`FakeLLMClient.last_call`
üzerinden); `test_main_integration.py`: `/api/plan`'ın gerçekten
`session.requestText`'i ilettiğini doğrulayan test.
