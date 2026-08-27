# Test Diff — api-health-tanilama

_Reference: atdd.md, plan.md_

## Değiştirilen/Genişletilen Dosyalar
- `backend/tests/test_main_integration.py` (+183 satır) — endpoint-seviyesi integration testleri
- `backend/tests/test_plan_generation.py` (+98 satır) — LLM erişilebilirlik unit testleri

## AC ↔ Test Fonksiyonu Eşlemesi

| AC | Test Fonksiyonu | Dosya |
|---|---|---|
| AC-1 [Critical] Happy path | `test_health_endpoint_returns_ok` (güncellendi), `test_health_endpoint_ac1_happy_path_llm_reachable_no_path` | test_main_integration.py |
| AC-2 [Critical] LLM ağ/timeout hatası | `test_health_endpoint_ac2_llm_network_error`, `test_health_endpoint_llm_timeout_returns_unreachable` | test_main_integration.py |
| AC-3 [High] Path whitelist içinde | `test_health_endpoint_ac3_path_in_whitelist` | test_main_integration.py |
| AC-4 [High] Path whitelist dışında | `test_health_endpoint_ac4_path_outside_whitelist` | test_main_integration.py |
| AC-5 [Medium] Path parametresi yok | `test_health_endpoint_ac5_no_path_parameter` | test_main_integration.py |
| AC-6 [Medium] Config hiç yapılmamış | `test_health_endpoint_ac6_no_config_setup` | test_main_integration.py |
| AC-7 [Medium] Path malformed | `test_health_endpoint_ac7_path_malformed` | test_main_integration.py |
| Davranış Sözleşmesi #6 Kısmi başarı | `test_health_endpoint_partial_success_llm_up_path_down` | test_main_integration.py |
| LLM reachability (unit) | 6 test (`check_llm_health` varsayılan metod adıyla, reachable/unreachable/timeout) | test_plan_generation.py |

## Kalite Notu — düzeltildi
İlk dispatch'te AC-3, AC-4, AC-7 ve kısmi-başarı testlerinde hiç `assert` yoktu (sessiz başarı riski — implementasyon
yanlış olsa da PASS ederlerdi). İkinci bir dispatch ile 4 fonksiyona da gerçek assertion'lar eklendi, `allowed_root`
mevcut `test_config_endpoint_returns_saved_config` deseninden (`monkeypatch.setenv("APPDATA", ...)` + `config.json`)
kopyalanarak test ortamında sabitlendi. Doğrulandı: `git diff` ile içerik teyit edildi.

## Bilinen Risk (verify adımına not)
`test_health_endpoint_ac3/ac4/partial_success` testlerinde Windows path'leri (`C:\...`) query string'e URL-encode
edilmeden gömülmüş (`f"/api/health?path={test_path}"`). `\` ve `:` karakterleri httpx/TestClient tarafından
otomatik encode edilmeyebilir — `verify` adımında testler çalıştırılırken bu satır kırmızı çıkarsa önce bunun
implementasyon hatası mı yoksa encode sorunu mu olduğunu ayırt et.

## Varsayımlar (sub-agent'ın raporundan)
- LLM client'a eklenecek erişilebilirlik metodunun adı `check_llm_health()` olarak varsayıldı (atdd.md'nin
  Unknowns'ında netleşmemişti) — code-copilot bu ismi kullanmalı veya farklı bir isim seçerse testleri buna göre
  güncellemesi gerekir.
- "Malformed path" için sadece boş string test edildi; path-traversal payload'ı ayrıca test edilmedi (atdd.md'nin
  AC-4/whitelist-dışı davranışıyla path-traversal'ın nasıl ayrıştırılacağı plan.md'nin Kararlar #4'ünde zaten
  netleşmişti: traversal payload'ları malformed değil, whitelist-dışı sayılıyor — bu testlerde ayrıca kapsanmadı,
  code-copilot implementasyonu bu ayrımı plan.md'ye göre yapmalı).

## Beklenen Durum
Tüm yeni testler şu an **RED** (implementasyon yok). `code-copilot` adımı bunları **GREEN** yapacak implementasyonu yazacak.
