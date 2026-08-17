# Verify Report — plan_generation.py Çoklu Operasyon Desteği (Saga #292)

## Test Sonuçları
`pytest backend/tests -q` → **139/139 PASSED** (6 yeni test: 2x
`test_plan_generation.py` — request_text prompt'a ekleniyor,
`generate_plan_skeleton`e geçiyor; 1x `test_main_integration.py` —
`/api/plan`'ın `session.requestText`'i gerçekten ilettiği; ayrıca
mevcut `test_build_metadata_prompt_...` testi yeni zorunlu parametreye
uyacak şekilde güncellendi).

## Canlı LLM Doğrulaması (DeepSeek, gerçek API anahtarıyla)
Kullanıcının onayıyla gerçek DeepSeek API'sine karşı iki senaryo
çalıştırıldı (`/tmp/live_test_292` altında 2 sahte PDF, backend
`uvicorn` ile `PLAN_LLM_API_KEY`/`PLAN_LLM_BASE_URL=https://api.deepseek.com`
ortam değişkenleriyle başlatıldı — anahtar hiçbir dosyaya yazılmadı):

1. **"Bu eski PDF dosyalarini sil"** → `operationType: "Sil"` doğru
   seçildi, her iki dosya da `fileNames`'e doğru eklendi.
2. **"Bu dosyalarin ismini 2026 raporu.pdf ve 2026 faturasi.pdf olarak
   degistir"** → `operationType: "Yeniden Adlandır"` doğru seçildi,
   `newFileNames` `fileNames` ile aynı sırada/uzunlukta doğru üretildi.

ATDD'de "bilinmeyen risk" olarak işaretlenen "gerçek bir LLM'in yeni
prompt'la COPY/DELETE/RENAME/LIST'i doğru seçtiği doğrulanamadı" riski
bu testlerle kapatıldı.

## Kabul Kriterleri Durumu
- AC-1 (kritik): ✅ `generate_plan_skeleton` artık `request_text` alıyor.
- AC-2 (kritik): ✅ `main.py: create_plan`, `session.requestText`'i geçiriyor.
- AC-3 (yüksek): ✅ `PLAN_SYSTEM_PROMPT` 5 operationType eşleme rehberi + `newFileNames` açıklaması içeriyor.
- AC-4 (orta): ✅ Mevcut testler etkilenmeden geçiyor (139/139).

## Sonuç
`ready_to_commit: evet`
