# Plan — excel-create-read-append
_Reference: atdd.md_

## Unknowns'ın Çözümü (kod incelemesiyle netleşti)

**`fileNames=[]` deseninin CREATE için çakışıp çakışmadığı:** Doğrulandı,
ÇAKIŞMA YOK. `PlanStep.fileNames: list[str]` alanında `min_length`
kısıtı YOK; `file_names_not_blank`/`file_names_have_no_path_separators`/
`file_names_have_no_duplicates` validator'ları boş liste için trivially
geçer; `affected_file_count_matches_file_names` sadece `affectedFileCount
== len(fileNames)` istiyor (0==0 geçerli). Hiçbir MEVCUT operationType-özel
validator (`merged_file_name_only_for_merge` vb.) EXCEL_CREATE'e
uygulanmayacağı için 0-kaynak deseni GÜVENLE eklenebilir — MERGE'in
">=2" ve SPLIT/APPEND'in "==1" desenlerinin yanına yeni bir "==0" varyantı.

**`rows`/`appendRows` alan isimlendirmesi:** Proje genelinde HİÇBİR
operationType bir alanı BAŞKA bir operationType'la PAYLAŞMIYOR
(`mergedFileName`, `redactedFileName`, `sortedFileName`, `filteredFileName`,
`compressedFileName` — hepsi tekil). Bu konvansiyonla tutarlı kalmak için
**`createRows`** (EXCEL_CREATE) ve **`appendRows`** (EXCEL_APPEND) AYRI
alanlar olarak eklenecek — "rows" ortak bir alan OLMAYACAK.

## Files to Modify
| File | Why | Risk |
|------|-----|------|
| backend/models.py | `OperationType.EXCEL_CREATE`/`EXCEL_APPEND` enum değerleri (PDF_COMPRESS'in ardına); `PlanStep`e `createRows: list \| None`, `createdFileName: str \| None`, `appendRows: list \| None`; iki model_validator (`excel_create_fields_only_for_excel_create` — fileNames==0 zorunlu, `excel_append_fields_only_for_excel_append` — fileNames==1 zorunlu, APPEND'in `append_text_only_for_append` deseninin kopyası); YENİ `SearchRequest`-benzeri bir `ExcelReadRequest`/`ExcelReadResponse` şeması | medium — CREATE'in "0 kaynak" deseni İLK KEZ ekleniyor, dikkatli test edilmeli |
| backend/orchestrator.py | `from backend import excel_create, excel_append` (veya tek `excel_rows.py`) import; `_SUPPORTED_OPERATION_TYPES`e ekle; `_ROLLBACK_OPERATIONS`e `EXCEL_CREATE: _rollback_copy`, `EXCEL_APPEND: _rollback_append` (PDF APPEND'in AYNI fonksiyonu — dosya-tipi bağımsız, sadece backup_path'ten kopyalıyor); hedef-klasör-oluşturma hariç-tutma listesine ekle; iki yeni step-uygulama bloğu — CREATE: EXCEL_FILTER'ın record+completed deseni (kaynak yok, sadece hedef); APPEND: PDF `OperationType.APPEND` bloğunun (satır 825-847) BİREBİR kopyası, `_forward_append`/`_append_backup_path` yerine yeni bir `_forward_excel_append`/AYNI `_append_backup_path` (backup dizini dosya-tipinden bağımsız, olduğu gibi yeniden kullanılabilir) | low-medium — APPEND bloğu mevcut desenin kopyası, CREATE bloğu yeni ("kaynaksız" step) |
| backend/main.py | YENİ `POST /api/excel/read` endpoint'i — `search_endpoint`'in (satır 545-577) deseniyle AYNI: `SessionContext`/`get_session_for_search` dependency, `allowed_root.is_dir()` 410 kontrolü, `ExcelReadRequest{filename, range: str \| None}` → `ExcelReadResponse{values: list[list], range: str \| None}` | low — mevcut search endpoint'inin kopyası |

## New Files
| File | Purpose |
|------|---------|
| backend/excel_rows.py | `create_excel_file(rows, destination_path) -> None` (hedef zaten varsa `FileExistsError`, düz satır sarma normalizasyonu burada), `append_excel_rows(source_path, rows, backup_path) -> None` (PDF `_forward_append`'in AYNI "önce oku, sonra yedekle, sonra atomik yaz" sırası — openpyxl `load_workbook`+`ws.append`+`wb.save` doğrudan kaynağa yazılabildiği için ayrı bir tempfile+replace GEREKMİYOR, ama `backup_path`'e önce kopyalama YAPILMALI, PDF deseniyle aynı), `read_excel_range(source_path, range_spec: str \| None) -> list[list]` (openpyxl `ws[range_spec]` veya `range_spec` yoksa tüm `ws.iter_rows()`) |
| backend/tests/test_excel_rows.py | `create_excel_file`/`append_excel_rows`/`read_excel_range` unit testleri |

## Dependencies
- `openpyxl.load_workbook`/`Workbook` (zaten proje genelinde kullanılıyor — excel_sort.py'de).
- `_rollback_append`/`_append_backup_path` (orchestrator.py:314-320, 371-372) —
  APPEND'in bu iki yardımcısı dosya-TİPİNDEN BAĞIMSIZ (PdfReader/Writer'a hiç
  değinmiyor, sadece `shutil.copy2`) — EXCEL_APPEND için DEĞİŞİKLİK
  GEREKMEDEN doğrudan yeniden kullanılabilir.
- `_rollback_copy` (orchestrator.py:308) — EXCEL_CREATE için, değişiklik gerekmiyor.
- `SearchRequest`/`SearchResponse`'un session/allowed_root doğrulama deseni
  (`get_session_for_search`) — EXCEL_READ endpoint'i için yeniden kullanılacak.

## Migration Required?
No — DB şeması dokunulmuyor (operationType string, önceki görevlerle aynı
gerekçe). EXCEL_READ hiç DB'ye yazmıyor (salt-okunur, `FileOperation` kaydı yok).

## Risks
- (atdd.md'den taşındı, ÇÖZÜLDÜ) fileNames=[] deseni artık risk değil,
  doğrulandı.
- `append_excel_rows`'un "önce oku, sonra yedekle, sonra kaynağa YAZ" sırası
  PDF'in "tempfile'a yaz, sonra atomik replace" deseninden FARKLI olacak
  (openpyxl `wb.save(str(source_path))` doğrudan üzerine yazıyor, tempfile
  ara adımı yok) — bu, yazma YARIDA KESİLİRSE (ör. disk dolu) kaynağın
  YARIM/BOZUK kalma riskini taşır. **code-copilot'a AÇIKÇA talimat
  verilmeli:** `append_excel_rows` de `backup_path`'e önce kopyalama +
  SONRA tempfile+atomik-replace deseni İZLEMELİ (PDF'in `_forward_append`
  ile birebir aynı güvenlik garantisi), openpyxl'in "doğrudan üzerine
  yaz" kolaylığına GÜVENİLMEMELİ.
- (ÇÖZÜLDÜ) `read_excel_range`'in geçersiz range davranışı gerçek openpyxl
  kurulumuyla DOĞRULANDI: `ws["ZZZ9999999"]` gibi geçersiz bir aralık
  `ValueError` fırlatıyor (ör. "Row numbers must be between 1 and
  1048576") — main.py bu `ValueError`'ı yakalayıp 422'ye çevirmeli.

## Open Questions
Yok — atdd.md'nin iki Unknown'ı da bu planla kod incelemesiyle çözüldü.
