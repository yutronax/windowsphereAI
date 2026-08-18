# Plan — Dosya Arama MVP (Saga #313)

## Backend dosya değişiklikleri
- `backend/models.py`: `SearchRequest` (sessionId, nameContains?, extension?,
  modifiedAfter?, modifiedBefore?), `SearchResultItem` (filename, extension,
  modifiedAt, sizeBytes), `SearchResponse` (results: list[SearchResultItem]).
- `backend/file_search.py` (yeni modül, `pdf_discovery.py` ile aynı stil):
  `search_files(folder: Path, *, name_contains: str|None=None,
  extension: str|None=None, modified_after: dt.datetime|None=None,
  modified_before: dt.datetime|None=None) -> list[SearchResultItem]`.
  Non-recursive, `discover_pdf_files`'taki gizli-dosya atlama kuralını
  paylaşır (kod tekrarını en aza indir, aynı `not entry.name.startswith(".")`
  deseni).
- `backend/main.py`: `get_session_for_search` dependency (mevcut
  `get_session_or_404`/`get_session_for_apply` ile AYNI desen) +
  `POST /api/search` endpoint'i.

## Frontend (ayrı, daha küçük bir takip çağrısı)
- Yeni minimal component (ör. `ui/src/components/search/SearchPanel.tsx`)
  — arama input'u + sonuç listesi. Mevcut chat akışına entegre edilmez,
  epic'in kendi tanımındaki "basit sonuç listesi" — bağımsız bir UI parçası.

## Sıra
1. Backend test yazımı (Haiku subagent, red).
2. Backend implementasyon (Haiku subagent, green).
3. Ana oturum: gerçek pytest doğrulaması + diff incelemesi.
4. Frontend (ayrı Haiku çağrısı, test+implementasyon).
5. Ana oturum: frontend test doğrulaması.
6. AI_DEVLOG + commit + push + Saga güncelleme.
