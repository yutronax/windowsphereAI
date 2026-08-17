---
task_slug: pdf-plan-skeleton-uretimi
priority: high
coverage_target: "AC'lerin tamamı unit/integration test ile kapsanır"
performance_target: "yok (LLM I/O'ya bağlı, ölçülebilir bir performans hedefi bu task'ta belirlenmedi)"
test_strategy: "80/20/0 (unit/integration) — LLM çağrısı FakeLLMClient ile mock'lanır, gerçek ağ isteği testte YAPILMAZ"
affected_modules: ["backend/models.py", "backend/plan_generation.py", "backend/main.py"]
---

# Pinlenmiş LLM modeliyle yalnızca metadata kullanan plan-skeleton üret (Saga #269)

## Persona
"Bu klasördeki PDF'leri tarihe göre sırala" isteğini gönderen kullanıcı;
dolaylı olarak bu planı tüketecek olan Security/Orchestrator katmanları
(Saga #271-277).

## Goal
FastAPI Decision katmanı, env ile override edilebilen pinlenmiş bir model
kimliğiyle, SADECE PDF dosya adı ve tarih metadata'sından adım adım bir
plan-skeleton üretmelidir. PDF içerikleri bütünüyle LLM'e gönderilmemeli;
plan üretilemezse (LLM hatası, geçersiz JSON, şema dışı yanıt) net bir
hata dönmelidir.

## User Story
Bir kullanıcı olarak, isteğimi gönderdikten sonra sistemin PDF'lerimin
İÇERİĞİNİ bir LLM'e göndermeden, sadece dosya adı/tarihinden güvenli bir
plan üretmesini istiyorum; plan üretilemezse ne olduğunu anlaşılır bir
şekilde öğrenmek istiyorum.

## Acceptance Criteria (öncelik sırasına göre)
1. `generate_plan_skeleton(pdf_files, client, model=None)` fonksiyonu
   sadece `filename` + `createdAt` (metadata) alanlarını prompt'a dahil
   eder — PDF içeriği/binary veri hiçbir şekilde LLM istemcisine
   geçirilmez (fonksiyon imzası zaten içerik parametresi almaz — bu
   yapısal olarak garanti edilir, "unutma" riski yok).
2. Kullanılan model kimliği `PLAN_LLM_MODEL_ID` ortam değişkeniyle
   override edilebilir; belirtilmemişse pinlenmiş bir varsayılana
   (`DEFAULT_MODEL_ID`) düşer.
3. LLM isteği başarısız olursa (network hatası, timeout, herhangi bir
   exception) `PlanGenerationError` fırlatılır — çağıran taraf (FastAPI
   endpoint) bunu HTTP 502 + net bir hata mesajına çevirir.
4. LLM yanıtı geçerli JSON değilse `PlanGenerationError` fırlatılır.
5. LLM yanıtı geçerli JSON ama beklenen şemaya (order/operationType/
   targetFolder/affectedFileCount — Saga #280'deki frontend şemasının
   backend karşılığı) uymuyorsa `PlanGenerationError` fırlatılır
   (fail-closed, Pydantic `PlanStep`/`PlanSkeleton` modelleriyle).
6. `pdf_files` boşsa (klasörde PDF yoksa) LLM'e hiç istek atılmadan boş
   bir `PlanSkeleton(steps=[])` döner (gereksiz LLM çağrısı yapılmaz).
7. `POST /api/plan` endpoint'i: `PlanGenerationError`'ı HTTP 502 + detail
   mesajına çevirir; LLM API anahtarı yapılandırılmamışsa HTTP 503 döner
   (fail-fast, LLM'e hiç istek atmadan).

## Behaviour-contract tablosu
| Durum | Beklenen sonuç |
|---|---|
| Geçerli metadata + LLM geçerli plan JSON'u döner | `PlanSkeleton` nesnesi, `steps` dolu |
| `pdf_files = []` | `PlanSkeleton(steps=[])`, LLM'e istek atılmaz |
| LLM istemcisi exception fırlatır | `PlanGenerationError` |
| LLM yanıtı geçersiz JSON | `PlanGenerationError` |
| LLM yanıtı şema dışı (ör. negatif `order`, bilinmeyen `operationType`) | `PlanGenerationError` |
| `model` parametresi verilmemiş, `PLAN_LLM_MODEL_ID` ortam değişkeni set | O env değeri kullanılır |
| `model` parametresi verilmemiş, env de yok | `DEFAULT_MODEL_ID` kullanılır |
| `/api/plan`'a `PLAN_LLM_API_KEY` yokken istek | 503, LLM'e istek atılmaz |
| `/api/plan`'da plan üretimi başarısız | 502 + net hata detail'i |

## Risks/Assumptions/Unknowns
- Assumption: LLM istemcisi bir `LLMClient` Protocol'ü (yapısal arayüz)
  arkasında soyutlandı — gerçek `OpenAICompatibleLLMClient` (openai SDK,
  BYOK için `base_url` override edilebilir) sadece endpoint'te
  dependency injection ile bağlanıyor. Testler `FakeLLMClient` kullanır,
  GERÇEK AĞ İSTEĞİ YAPMAZ (bu ortamda API anahtarı yok, yapılamaz zaten).
  (saga-oto tarafından otomatik seçildi)
- Assumption: Pinlenmiş model kimliği `DEFAULT_MODEL_ID = "gpt-4o-mini"`
  olarak seçildi — proje henüz hangi sağlayıcıyı/modeli kullanacağına
  karar vermedi (BYOK deseni, proje hafızasında not edildi); bu placeholder
  bir varsayılan, gerçek ürün kararı geldiğinde `PLAN_LLM_MODEL_ID` env
  değişkeniyle değiştirilebilir — kod değişikliği gerektirmez. (saga-oto
  tarafından otomatik seçildi)
- Assumption: `PlanStep`/`PlanSkeleton` Pydantic modelleri backend'de
  YENİDEN tanımlandı (frontend'deki TS `Plan`/`PlanStep` ile aynı alan
  adları/kurallar — order/operationType/targetFolder/affectedFileCount,
  Saga #280'deki `validatePlanResponse` ile aynı kurallar) — iki dilde
  (TS+Python) aynı sözleşmeyi paylaşan tek bir şema kaynağı YOK, bu bir
  kod tekrarı riski ama proje henüz bir OpenAPI/schema-codegen
  altyapısına sahip değil, dar kapsam. (saga-oto tarafından otomatik
  seçildi)
- Risk: Gerçek LLM entegrasyonu (API anahtarı, gerçek prompt kalitesi,
  gerçek JSON-mode desteği sağlayıcıya göre değişir) bu ortamda TEST
  EDİLEMEDİ — sadece FakeLLMClient ile mock'landı. Bu, verify_report.md'ye
  açıkça not düşülecek.

## Test Strategy
80/20/0 unit/integration. `backend/tests/test_plan_generation.py` (saf
fonksiyon, FakeLLMClient) + `backend/tests/test_main_integration.py`'e
`/api/plan` endpoint testleri (dependency override ile FakeLLMClient).

## Benchmark
Kabul kriteri: `python -m pytest backend/ -q` içinde tüm testler yeşil.

## Sorular ve Cevaplar (saga-oto otomatik)
- S: Gerçek bir LLM sağlayıcısına (OpenAI/DeepSeek/vb.) bağlanılacak mı?
  C: Evet ama sadece endpoint seviyesinde (openai SDK, BYOK için base_url
  override edilebilir) — test edilemediği için sadece kod olarak var,
  gerçek entegrasyon doğrulaması ayrı, canlı bir ortamda yapılmalı.
  (saga-oto tarafından otomatik seçildi)
- S: PDF içeriği (metin/OCR) hiç kullanılmıyor mu? C: Hayır, task açıkça
  "PDF içerikleri bütünüyle LLM'e gönderilmemeli" diyor — sadece dosya adı
  + tarih. (saga-oto tarafından otomatik seçildi)
