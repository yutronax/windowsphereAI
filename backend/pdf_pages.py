import os
import tempfile
from pathlib import Path

from pypdf import PdfReader, PdfWriter


def parse_page_spec(page_spec: str, page_count: int) -> list[int]:
    """`page_spec`i (ör. "1,3,5-9") 1-indexed, sıralı, tekilleştirilmiş bir
    sayfa numarası listesine çözer (Saga #321, ATDD AC-1/AC-6/AC-7).

    Virgülle ayrılmış tekil sayfa numaraları ve `başlangıç-bitiş` aralıkları
    karışık olarak desteklenir. Boşluklar trim edilir (AC-6). Tekrarlanan
    sayfa numaraları sessizce tekilleştirilir, İLK GÖRÜLDÜKLERİ sırayla
    korunur (AC-7). Ters aralık (başlangıç>bitiş) veya `page_count`'u aşan
    bir sayfa numarası `ValueError` fırlatır (AC-3/AC-4) — TÜM istek
    reddedilir, kısmi sonuç YOK. Boş/whitespace-only `page_spec` de
    `ValueError` fırlatır."""
    normalized = page_spec.strip()
    if normalized == "":
        raise ValueError("page_spec must not be empty or whitespace-only")

    seen: set[int] = set()
    result: list[int] = []
    for chunk in normalized.split(","):
        token = chunk.strip()
        if token == "":
            raise ValueError(f"page_spec contains an empty entry: '{page_spec}'")
        if "-" in token:
            start_str, _, end_str = token.partition("-")
            try:
                start = int(start_str.strip())
                end = int(end_str.strip())
            except ValueError:
                raise ValueError(f"page_spec contains an invalid range: '{token}'") from None
            if start > end:
                raise ValueError(f"page_spec contains a reversed range: '{token}'")
            page_numbers = range(start, end + 1)
        else:
            try:
                page_numbers = [int(token)]
            except ValueError:
                raise ValueError(f"page_spec contains an invalid page number: '{token}'") from None

        for page_number in page_numbers:
            if page_number < 1 or page_number > page_count:
                raise ValueError(
                    f"page_spec contains a page number out of document range (1-{page_count}): {page_number}"
                )
            if page_number not in seen:
                seen.add(page_number)
                result.append(page_number)

    return result


def _write_pages(source_path: Path, page_numbers_zero_indexed: list[int], destination_path: Path) -> None:
    reader = PdfReader(str(source_path))
    writer = PdfWriter()
    for page_index in page_numbers_zero_indexed:
        writer.add_page(reader.pages[page_index])

    fd, temp_path_str = tempfile.mkstemp(
        suffix=".tmp", prefix=destination_path.name + ".", dir=str(destination_path.parent)
    )
    temp_path = Path(temp_path_str)
    os.close(fd)
    try:
        with open(temp_path, "wb") as f:
            writer.write(f)
        temp_path.replace(destination_path)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise


def extract_pdf_pages(source_path: Path, page_spec: str, destination_path: Path) -> None:
    """`source_path`teki PDF'in `page_spec`te belirtilen SEÇİLİ sayfalarını
    (orijinal sırayla) YENİ bir dosyaya (`destination_path`) yazar - kaynağa
    asla dokunulmaz (Saga #321, ATDD AC-1). `page_spec` geçersizse (ters
    aralık, belge-dışı sayfa, boş) `ValueError` fırlatır, hiçbir dosya
    yazılmaz - `excel_sort.py`'nin tempfile+atomik-replace deseniyle AYNI."""
    reader = PdfReader(str(source_path))
    page_numbers = parse_page_spec(page_spec, page_count=len(reader.pages))
    _write_pages(source_path, [page_number - 1 for page_number in page_numbers], destination_path)


def delete_pdf_pages(source_path: Path, page_spec: str, destination_path: Path) -> None:
    """`source_path`teki PDF'ten `page_spec`te belirtilen sayfaları ÇIKARIP
    kalan sayfaları (orijinal sırayla) YENİ bir dosyaya (`destination_path`)
    yazar - kaynağa asla dokunulmaz (Saga #321, ATDD AC-2). `page_spec`
    geçersizse (ters aralık, belge-dışı sayfa, boş) `ValueError` fırlatır,
    hiçbir dosya yazılmaz. TÜM sayfalar silinirse (0 sayfa kalır) da
    `ValueError` fırlatılır - 0 sayfalık bir PDF sessizce üretilmez (AC-5)."""
    reader = PdfReader(str(source_path))
    page_count = len(reader.pages)
    pages_to_delete = set(parse_page_spec(page_spec, page_count=page_count))
    remaining_pages_zero_indexed = [
        index for index in range(page_count) if (index + 1) not in pages_to_delete
    ]
    if len(remaining_pages_zero_indexed) == 0:
        raise ValueError("all pages would be deleted - refusing to write an empty PDF")
    _write_pages(source_path, remaining_pages_zero_indexed, destination_path)
