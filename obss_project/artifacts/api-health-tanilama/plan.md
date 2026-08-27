# Plan — api-health-tanilama
_Reference: atdd.md_

## Files to Modify
| File | Why | Risk |
|------|-----|------|
| backend/main.py | `/api/health` endpoint'i genişletilir: opsiyonel `path` query parametresi eklenir, `HealthCheckResponse` döner, LLM reachability + `is_path_allowed` çağrılarını orkestre eder (AC-1..7) | medium |
| backend/plan_generation.py | `OpenAICompatibleLLMClient`'a hafif bir erişilebilirlik kontrolü eklenir (bkz. Kararlar — `models.list()` ile ping, `complete()`'i tetiklemez, token/kota tüketmez). API key hiç yoksa (`get_llm_client` gibi 503 fırlatmadan) `llm_reachable=False` döndürebilecek raise-etmeyen bir yardımcı fonksiyon eklenir | low |
| backend/models.py | Yeni `HealthCheckResponse` Pydantic modeli eklenir: `status: str`, `llm_reachable: bool`, `path_allowed: bool | None` | low |

## New Files
(Yok — mevcut 3 dosyaya ek yapılıyor, yeni modül gerekmiyor.)

## Dependencies
- `backend.config.load_setup_config()` — `selectedFolder`'ı (allowed_root) okumak için (mevcut, main.py zaten `/api/config`'te kullanıyor).
- `backend.security.is_path_allowed(path, allowed_root)` — whitelist kontrolü, DEĞİŞTİRİLMEDEN doğrudan çağrılacak.
- `os.environ.get("PLAN_LLM_API_KEY")` / `os.environ.get("PLAN_LLM_BASE_URL")` — LLM erişilebilirlik kontrolü için api_key/base_url kaynağı (mevcut `get_llm_client()` ile AYNI env var'lar — bkz. Kararlar, atdd.md'nin "config.json'dan okunuyor" varsayımını düzeltir).
- `backend.plan_generation.OpenAICompatibleLLMClient` — reachability ping'i bu client üzerinden yapılacak.

## Migration Required?
No — şema/DB değişikliği yok, sadece yeni bir Pydantic response modeli ve mevcut fonksiyonların endpoint içinde orkestrasyonu.

## Kararlar (keşif sırasında netleşen, atdd.md'nin Unknowns'ını çözen)

1. **LLM erişilebilirlik kontrolü için hangi API çağrısı?** → `client.models.list()` (OpenAI SDK'nın standart, ücretsiz/düşük-maliyetli endpoint'i — chat completion gibi token/kota tüketmez, sadece kimlik doğrulama + bağlantıyı test eder). DeepSeek gibi OpenAI-uyumlu sağlayıcılarda da desteklenir. Gerekçe: atdd.md Risk bölümünde "gereksiz LLM kotası tüketimi" endişesi vardı — `models.list()` bunu bertaraf ediyor.

2. **API key hiç yoksa ne olur?** → Mevcut `get_llm_client()` (main.py:211-216) api_key yoksa `HTTPException(503)` fırlatıyor — bu davranış health endpoint'i için UYGUN DEĞİL (AC-6: config/setup eksikse health check hâlâ 200 dönmeli). Bu yüzden health endpoint'i `get_llm_client()`'ı ÇAĞIRMAYACAK; onun yerine `os.environ.get("PLAN_LLM_API_KEY")` doğrudan kontrol edilip yoksa `llm_reachable=False` (exception fırlatmadan) döner.

3. **`allowed_root` kaynağı düzeltmesi** → atdd.md'de "config'ten" deniyordu, gerçek kaynak `backend.config.load_setup_config()["selectedFolder"]` (config.json, `%APPDATA%/windows-ai-files/config.json`). LLM api_key ise AYRI bir kaynaktan (env var) geliyor — ikisi birbirinden bağımsız, biri eksik diğerini etkilemez (AC-6 bunu yansıtmalı: setup yapılmamışsa `path_allowed=null` çünkü allowed_root yok, ama `llm_reachable` env var'a bağlı olarak true/false olabilir — atdd.md'deki "her ikisi de false" varsayımı hafifçe yanlıştı, düzeltildi).

4. **"Malformed path" tanımı** → `path` query param'ı verildiğinde `Path(path)` oluşturma veya `.resolve()` çağrısı `OSError`/`ValueError` fırlatırsa (ör. Windows'ta geçersiz karakterler) 400 döner. Path traversal payload'ları (`../../`) AYRICA malformed sayılmaz — bunlar `is_path_allowed()`'ın zaten ele aldığı normal "whitelist dışı" durumu (`path_allowed: false`), 400 değil 200 döner (AC-4).

## Risks
(atdd.md'den taşınan + keşifte netleşen)
- LLM'e her `/api/health` çağrısında gerçek bir `models.list()` isteği atmak sık çağrılırsa (izleme aracı vb.) gereksiz ağ/latency yükü yaratır — bu görev kapsamında cache/rate-limit eklenmiyor (atdd.md'nin Risk bölümünde zaten kabul edilmiş).
- `path.resolve()` Windows'ta bazı geçersiz karakter durumlarında farklı exception tipleri fırlatabilir (`OSError` vs `ValueError`) — main.py'de her ikisi de yakalanmalı, sadece biri değil.

## Open Questions
(Yok — atdd.md'nin Unknowns bölümündeki iki soru yukarıdaki Kararlar #1 ve #4'te kod keşfiyle netleşti, Haiku dispatch'ine gerek kalmadı.)

## Not: UI/vision-test etkisi
Bu plan hiçbir `.html`/`.tsx`/`.jsx`/CSS dosyası içermiyor (sadece backend Python) — `verify` adımında gate 11 (`vision-test`) N/A kalır.
