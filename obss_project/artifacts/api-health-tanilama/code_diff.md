# Code Diff — api-health-tanilama

_Reference: atdd.md, plan.md, test_diff.md_

## Değiştirilen Dosyalar
- `backend/main.py` (+~47 satır) — `/api/health` genişletildi, yeni `get_llm_client_for_health()` dependency eklendi
- `backend/models.py` (+9 satır) — `HealthCheckResponse` Pydantic modeli
- `backend/plan_generation.py` (+9 satır) — `OpenAICompatibleLLMClient.check_llm_health()`

Yeni dosya yok.

## AC Karşılama
| AC | Karşılandı mı | Not |
|---|---|---|
| AC-1 Happy path | ✓ | `check_llm_health()` True, path yok → `path_allowed: null` |
| AC-2 LLM ağ/timeout hatası | ✓ | `check_llm_health()` her exception'da False döner (asla raise etmez) |
| AC-3 Path whitelist içinde | ✓ | `is_path_allowed()` doğrudan kullanıldı |
| AC-4 Path whitelist dışında | ✓ | 200 + `path_allowed: false`, 400 değil |
| AC-5 Path parametresi yok | ✓ | `path_allowed: null`, whitelist kontrolü atlanıyor |
| AC-6 Config/API key yok | ✓ | `get_llm_client_for_health()` None döner, hiçbir yerde raise yok — 500/503 imkansız |
| AC-7 Path malformed | ✓ | boş string veya `Path().resolve()` OSError/ValueError → 400 |

## Mimari çözülen çelişki (code-copilot öncesi keşfedildi)
`plan.md`'nin "health endpoint get_llm_client()'ı çağırmayacak" kararı ile `test-copilot`'un
zaten yazdığı testlerin `get_llm_client`'ı override etmesi FastAPI'nin dependency-override
mekanizması yüzünden (override sadece Depends()'e verilen birebir aynı objede çalışır) birlikte
karşılanamıyordu. Çözüm: tamamen ayrı bir `get_llm_client_for_health()` dependency'si eklendi,
mevcut `get_llm_client()` (ve ona bağımlı `/api/plan` + onun mevcut 503 testi) hiç değişmedi.
Bu değişikliğe uyacak şekilde `test_main_integration.py`'deki 10 health testinin override
hedefi de `get_llm_client_for_health`'e güncellendi (ayrı bir düzeltme dispatch'i ile,
plan/diğer testlere dokunulmadı — doğrulandı: 10/9 override sayımı).

## Temizlenen sorunlar (code-copilot review sırasında bulundu)
1. **Sessiz başarı riski:** ilk taslakta `hasattr(client, "check_llm_health")` dalı vardı —
   "eski client" senaryosu projede hiç yok (spekülatif), ve metod yoksa hiç kontrol etmeden
   `llm_reachable = True` döndürüyordu. Kaldırıldı, artık `check_llm_health()` doğrudan
   çağrılıyor (tüm exception'lar False'a düşüyor).
2. **Ölü kod:** `test_path.resolve().parts == ()` kontrolü hiçbir zaman True olamayacak bir
   koşuldu (resolved path her zaman en az drive/root içerir). Kaldırıldı.
3. **Test tutarsızlığı:** `test_health_endpoint_returns_ok` (AC-1) `_StubLLMClient` (check_llm_health
   yok) kullanırken, aynı AC'yi hedefleyen `test_health_endpoint_ac1_happy_path_...` `_HealthCheckLLMClient`
   kullanıyordu — implementasyon tarafında #1'deki hasattr dalının asıl sebebiydi. Test düzeltildi
   (`_HealthCheckLLMClient(is_reachable=True)`), artık ikisi de tutarlı.

## Kapsam Dışı (dokunulmadı, doğrulandı)
- `get_llm_client()` ve `/api/plan` endpoint'i — değişmedi.
- `test_plan_endpoint_*` testleri (9 adet) — değişmedi.

## Varsayımlar
- `check_llm_health()` metod adı `plan.md`'nin Unknowns'ını `test-copilot`'un ilk dispatch'i
  sırasında bu isimle varsaymıştı; implementasyon bu ismi birebir kullandı.

## Sonraki Adım
`verify` — testleri gerçekten çalıştırıp AC-1..AC-7'nin GREEN olduğunu doğrulamalı. Bu adımda
testler hiç ÇALIŞTIRILMADI, sadece kod okunarak (Read + git diff) statik doğrulama yapıldı.
