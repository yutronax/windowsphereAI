---
task_slug: gecmis-transaction-listesi-endpoint
priority: medium
coverage_target: "70/30/0"
performance_target: "yok"
test_strategy: "integration (FastAPI TestClient, gerçek SQLAlchemy in-memory DB)"
affected_modules:
  - backend/main.py
  - backend/models.py
saga_task_id: 294
epic_id: 28
---

# ATDD — Geçmiş Transaction'ları Listeleyen Backend Endpoint'i (Saga #294)

## Goal
Kullanıcının önceki işlemlerini görebileceği bir GET endpoint'i. Task
açıklaması iki seçenek sunuyor: global `/api/transactions` veya
session-bazlı `/api/sessions/{id}/transactions`.

## Sorular ve Cevaplar (saga-oto tarafından otomatik seçildi)

**S1: Global mi session-bazlı mı?** Cevap: **Global `/api/transactions`.**
Kod keşfi: `db_models.py: Transaction`'ın `session_id` gibi bir FK'sı
YOK, `SessionContext` (main.py) zaten sadece bellek-içi bir dict
(`_sessions`) — DB'ye hiç yazılmıyor, süreç yeniden başlayınca kaybolur.
Session-bazlı bir endpoint için ÖNCE `Transaction`e bir `session_id`
kolonu eklemek (yeni migration + `apply_plan`'ın her çağrısına
session_id geçirmesi) gerekirdi — bu, henüz var olmayan bir apply
endpoint'inin (Saga #287 bekliyor) kendisiyle birlikte netleşecek bir
mimari genişleme, bu task'ın dar kapsamını aşıyor. Global liste, MVP
için yeterli ve mevcut şemaya SIFIR değişiklikle uyumlu. (saga-oto
tarafından otomatik seçildi — dar kapsam ilkesi)

**S2: Yanıt şeklinde hangi alanlar olmalı?** Cevap: `id`, `createdAt`,
`status`, `fileCount` (operations sayısı), `targetFolders` (operations'ın
`destination_path`'lerinin üst klasör adlarının tekil/sıralı listesi —
sadece klasör ADI, tam path SIZDIRILMAZ, Saga #283'teki "tam path
istemciye sızdırılmaz" ilkesiyle tutarlı). Task açıklamasındaki "tarih,
dosya sayısı, hedef klasörler, status" ile birebir örtüşüyor. (saga-oto
tarafından otomatik seçildi)

**S3: DB session nasıl enjekte edilmeli?** Cevap (red-team sonrası
GÜNCELLENDİ): `get_db_session()` adında yeni bir FastAPI dependency —
engine/session-factory SÜREÇ BAŞINA BİR KEZ (lazy, modül seviyesinde)
oluşturulur, `get_db_session` sadece `factory()`/`yield`/`close()` yapar.
İlk taslak `get_llm_client` ile aynı "her istekte taze oluştur" desenini
kullanıyordu, ama `obss-red-team` incelemesi bunun `get_llm_client`'tan
FARKLI bir maliyet profiline sahip olduğunu buldu (`create_db_engine`
her çağrıda tam şema introspection/ALTER TABLE taraması yapıyor) — sık
poll'lanabilecek bir "geçmiş" endpoint'i için bu gereksiz I/O anlamına
gelirdi. Testler `get_db_session`'ı `dependency_overrides` ile
TAMAMEN atladığı için bu cache test izolasyonunu bozmuyor.

**S4: Sıralama?** Cevap: En yeni transaction ÖNCE (`created_at DESC`) —
kullanıcının "son işlemlerim" beklentisiyle örtüşüyor. (saga-oto
tarafından otomatik seçildi)

## Kabul Kriterleri
1. **AC-1 (kritik):** `GET /api/transactions`, tüm `Transaction`
   kayıtlarını `id`/`createdAt`/`status`/`fileCount`/`targetFolders`
   içeren bir liste olarak, en yeniden en eskiye sıralı döndürüyor.
2. **AC-2 (yüksek):** Hiç transaction yoksa boş liste (`[]`) dönüyor,
   404 DEĞİL.
3. **AC-3 (orta):** `targetFolders` sadece klasör ADLARINI içeriyor, tam
   mutlak path İÇERMİYOR.

## Riskler / Varsayımlar / Bilinmeyenler
- Bu endpoint henüz bir "sadece BENİM işlemlerim" filtresi sunmuyor
  (global) — çok kullanıcılı/çok session'lı bir gelecekte bu yetersiz
  kalır, ama mevcut mimari (tek kullanıcı, session DB'de yok) zaten bunu
  desteklemiyor; gerçek session-bazlı filtreleme AYRI bir şema
  genişletmesi gerektirir, bu task'ın kapsamı dışında bırakıldı ve not
  edildi.

## Test Stratejisi
`backend/tests/test_main_integration.py`: `get_db_session` dependency
override ile in-memory SQLite'a birkaç `Transaction`/`FileOperation`
fixture'ı yazılır, endpoint çağrılır, sıralama/alan/boş-liste
senaryoları doğrulanır.
