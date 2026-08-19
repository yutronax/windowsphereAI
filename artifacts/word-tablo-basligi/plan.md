# Plan — word-tablo-basligi
_Reference: atdd.md_

## Unknowns'ın Çözümü

**Yeni modül gerekip gerekmediği:** Evet — `backend/word_table.py`,
`excel_rows.py`/`pdf_pages.py` ile aynı ayrım deseni (PDF/Excel-özel iş
mantığı orchestrator'dan ayrı, test edilebilir bir modülde).

**python-docx API şekli:** Bu adım (`plan`) SADECE OKUMA yapabilir (Glob/
Grep/Read), pip install İÇEREMEZ — bu yüzden gerçek kurulumla DOĞRULANAMADI
(EXCEL_APPEND/PDF_COMPRESS'te openpyxl/pypdf için yapılan canlı doğrulamanın
AYNISI burada yapılamadı, çünkü python-docx henüz kurulu DEĞİL ve kurmak
ortamı değiştirir). Bunun yerine python-docx'in ÇOK UZUN SÜREDİR
(yıllardır) DEĞİŞMEMİŞ, iyi belgelenmiş çekirdek API'si kullanılacak:
- `docx.Document(str(path))` — var olan `.docx`'i açar.
- `document.add_table(rows=N, cols=M)` — belgenin SONUNA yeni bir tablo
  ekler, `N`/`M` ÖNCEDEN bilinmeli (python-docx'in `add_row()`/`add_column()`
  metodları da var ama başlangıç boyutunu `add_table` ile vermek daha
  basit).
- `table.rows[i].cells[j].text = str(value)` — hücre yazma.
- `document.save(str(path))` — kaydetme (openpyxl'in `wb.save` ile aynı
  imza şekli).

**code-copilot'a AÇIKÇA talimat verilecek:** implementasyon subagent'ı
`pip install python-docx` çalıştırıp BU API'yi gerçek kurulumla doğrulamalı
(EXCEL_APPEND'te openpyxl için yapılan disiplinin AYNISI) — plan burada
sadece BİLİNEN/DOKÜMANTE API'yi öneriyor, implementasyon adımı GERÇEKLİĞİNİ
kanıtlamalı.

## Files to Modify
| File | Why | Risk |
|------|-----|------|
| requirements.txt | `python-docx` eklenir (YENİ bağımlılık, projede ilk kullanım) | low |
| backend/models.py | `OperationType.WORD_APPEND_TABLE` (WORD_APPEND_TABLE, PDF_COMPRESS/EXCEL_APPEND'in ardına); `PlanStep`e `tableHeaders: list \| None`, `tableRows: list`; `word_append_table_fields_only_for_word_append_table` model_validator — `append_text_only_for_append`/`excel_append_fields_only_for_excel_append` deseninin kopyası (`tableRows` zorunlu+boş-değil, `fileNames` TAM 1 eleman, `tableHeaders` OPSİYONEL — None olabilir, diğer operationType'larda ikisi de None olmalı) | low — mevcut desenin kopyası |
| backend/orchestrator.py | `from backend import word_table` import; `_SUPPORTED_OPERATION_TYPES`e ekle; `_ROLLBACK_OPERATIONS`e `WORD_APPEND_TABLE: _rollback_append` (EXCEL_APPEND'in AYNI fonksiyonu, DEĞİŞİKLİK GEREKMİYOR — dosya-tipinden bağımsız, sadece `shutil.copy2`); hedef-klasör-oluşturma hariç-tutma listesine ekle; yeni step bloğu — EXCEL_APPEND'in (backend/orchestrator.py, `OperationType.EXCEL_APPEND` bloğu) BİREBİR kopyası, `excel_rows.append_excel_rows` yerine `word_table.append_table` çağrısı | low — mevcut EXCEL_APPEND bloğunun kopyası |

## New Files
| File | Purpose |
|------|---------|
| backend/word_table.py | `append_table(source_path: Path, headers: list \| None, rows: list, backup_path: Path) -> None` — `excel_rows.append_excel_rows`'un AYNI "önce oku, sonra yedekle, sonra tempfile+atomik-replace" deseni; sütun sayısı uyuşmazlığında (`headers` varsa `len(headers)`, yoksa `rows[0]`'un uzunluğu referans alınır, HERHANGİ bir `rows` satırı bundan FARKLIysa) `ValueError` fırlatır, hiçbir şey yazılmaz |
| backend/tests/test_word_table.py | `append_table` unit testleri |

## Dependencies
- `_rollback_append`/`_append_backup_path` (orchestrator.py) — dosya-
  tipinden bağımsız, EXCEL_APPEND'de olduğu gibi DEĞİŞİKLİK GEREKMEDEN
  yeniden kullanılabilir.
- `excel_rows.py`'nin `append_excel_rows` fonksiyonu — DOĞRUDAN
  çağrılmayacak ama mimari EMSAL (backup+tempfile+atomik-replace sırası
  BİREBİR aynı olmalı).

## Migration Required?
No — DB şeması dokunulmuyor. `requirements.txt` güncellemesi bir
"migration" değil, kurulum bağımlılığı — code-copilot adımında
`pip install python-docx` çalıştırılıp venv'e eklenmeli, SETUP.md'ye
(varsa) bu yeni bağımlılık not düşülmeli (commit adımında karar
verilecek).

## Risks
- (atdd.md'den taşındı) python-docx API'si BU PLANDA doğrulanamadı —
  code-copilot'un ilk işi `pip install python-docx` + gerçek API
  doğrulaması olmalı, önerilen imzalar (`add_table`, `.rows[i].cells[j].text`)
  YANLIŞ çıkarsa test-copilot'un yazdığı testler code-copilot'ta
  düzeltilebilir (implementasyon API'ye uysun, testler DEĞİŞMESİN —
  ATDD'nin davranış sözleşmesi API detayından bağımsız).
- `add_table(rows=N, cols=M)`'nin N/M parametrelerini ÖNCEDEN bilmek
  gerektiği doğruysa (python-docx'in eski sürümlerinde `add_row()` ile
  sonradan satır eklemek de mümkün olabilir) — code-copilot hangi
  yaklaşımı seçerse seçsin, DAVRANIŞ (başlıklı/başlıksız doğru tablo)
  değişmemeli.

## Open Questions
Yok — atdd.md'nin Unknowns'ı (yeni modül) bu planla çözüldü. python-docx
API doğrulaması BİLİNÇLİ olarak code-copilot adımına bırakıldı (plan
adımı read-only olduğu için pip install YAPAMAZ) — bu bir açık soru değil,
sıradaki adımın açıkça devraldığı bir görev.
