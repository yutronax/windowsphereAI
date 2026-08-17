# Verify Report — Saga #286

| Gate | Sonuç | Kanıt |
|---|---|---|
| Backend test (pytest) | PASS | 101/101 test geçti (mevcut 95'e +6: 3 yeni orchestrator dağıtım testi, 4 yeni recovery testi (1'i red-team sonrası eklendi: mixed completed+pending durum), mevcut testler fileNames'e uyarlandı) |

## Kapsam dışı (ATDD'de belgelendi)
- `recover_incomplete_transactions` gerçek bir FastAPI startup event'ine bağlanmadı (Saga #287 sonrası).
- Gerçek bir LLM ile `fileNames` üretiminin uçtan uca doğrulanması (LLM istemcisi stub'lanıyor).
