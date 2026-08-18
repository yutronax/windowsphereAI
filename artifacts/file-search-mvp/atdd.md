# ATDD — Dosya Arama MVP (Saga #313)

## Kapsam kararı (task'ın kendi ilk sorusu)
**Arama, /api/plan akışından TAMAMEN AYRI, yeni bir salt-okunur endpoint
olacak** — `plan_generation`in LIST operationType'ına ENTEGRE EDİLMEYECEK.
Gerekçe: plan/apply akışı "onayla → gerçekten uygula (mutasyon)" akışıdır,
arama ise doğrudan sonuç isteyen salt-okunur bir sorgu — plan/onay
adımından geçirmek gereksiz karmaşıklık (YAGNI) ve kullanıcı deneyimini
yavaşlatır (arama sonucu için LLM plan üretimi beklemek anlamsız).
(saga-oto tarafından otomatik seçildi — dar kapsam ilkesi)

## Goal
Kullanıcının seçili klasöründe (allowed_root, `SessionContext.selectedFolder`)
dosya adı substring'i, uzantı ve/veya değişiklik tarihi aralığına göre
salt-okunur arama yapabileceği bir `POST /api/search` endpoint'i +
basit bir sonuç listesi UI'ı.

## Acceptance Criteria
1. **P0** — `POST /api/search`, `sessionId` + opsiyonel `nameContains`,
   `extension`, `modifiedAfter`, `modifiedBefore` alır. `get_session_or_404`
   ile AYNI desende (proje konvansiyonu: her farklı request şekli için
   ayrı, küçük bir session-lookup dependency) bir `get_session_for_search`
   kullanılır.
2. **P0** — Arama SADECE `session.selectedFolder` (`allowed_root`) altında
   yapılır, DOĞRUDAN alt seviye (recursive DEĞİL — `discover_pdf_files`
   ile AYNI dar kapsam, derin tarama Saga #315'e bırakıldı).
3. **P0** — Filtreler AND mantığıyla birleşir: hepsi verilirse hepsine
   uyan dosyalar döner. Hiçbiri verilmezse klasördeki TÜM dosyalar (gizli
   dosyalar hariç, `discover_pdf_files`'taki AYNI kural) döner.
4. **P0** — `nameContains`: düz substring (case-insensitive), glob/regex
   YORUMLANMAZ (eski projenin `_apply_name_contains` dersi — LLM'in
   aşırı geniş glob üretme riskine karşı, ama burada zaten LLM yok,
   yine de deterministik substring en güvenli/basit seçim).
5. **P0** — `extension`: nokta ile veya nokta olmadan verilebilir ("pdf"
   veya ".pdf"), case-insensitive karşılaştırılır.
6. **P0** — `modifiedAfter`/`modifiedBefore`: ISO 8601 tarih-saat, dosyanın
   `st_mtime`'ına göre karşılaştırılır (aralık dahil — `>=`/`<=`).
7. **P0** — Sonuçta MUTLAK path İSTEMCİYE SIZDIRILMAZ (Saga #283
   konvansiyonu) — sadece `filename`, `extension`, `modifiedAt` (ISO),
   `sizeBytes` döner.
8. **P1** — Seçili klasör artık mevcut değilse (`allowed_root.is_dir()`
   False) `/api/plan` ile AYNI 410 Gone hatası döner.
9. **P1** — Frontend'de basit bir arama input'u + sonuç listesi (yeni bir
   chat mesaj türü DEĞİL, epic'in kendi açıklamasındaki "basit sonuç
   listesi" — ayrı, minimal bir component).

## Behavior-Contract Table
| Senaryo | Beklenen |
|---|---|
| Hiçbir filtre yok | Klasördeki tüm görünür dosyalar döner |
| nameContains="fatura" | Adında (case-insensitive) "fatura" geçen dosyalar |
| extension="pdf" veya ".PDF" | Sadece .pdf dosyaları (case-insensitive) |
| modifiedAfter=X, modifiedBefore=Y | mtime bu aralıkta olan dosyalar |
| Klasör artık yok | 410 Gone |
| sessionId bilinmiyor | 404 Not Found |

## Test Strategy
Backend: `backend/tests/test_file_search.py` (yeni modül fonksiyonu için)
+ `backend/tests/test_main_integration.py`'ye endpoint testleri. Frontend:
yeni component için ayrı test dosyası.

## Risks/Assumptions
- İlerleme göstergesi, içerik arama (encoding-toleranslı), fuzzy/regex
  arama BU TASK'IN KAPSAMI DIŞINDA (ayrı Saga task'ları: #314/#315/#316).
- Sadece dosyalar döner, alt klasörler listelenmez (MVP dar kapsam).
