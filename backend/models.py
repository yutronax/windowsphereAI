import datetime as dt
import os
import re
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from backend.request_normalization import normalize_request_text, normalize_selected_folder

# YYYY-MM, ay 01-12 aralığında olmalı (red-team bulgusu, Saga #270: "2026-13"
# gibi geçersiz aylar eskiden bu regex'ten geçiyordu).
TARGET_FOLDER_PATTERN = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


class SessionRequest(BaseModel):
    selectedFolder: str
    requestText: str

    @field_validator("selectedFolder")
    @classmethod
    def normalize_folder(cls, value: str) -> str:
        return normalize_selected_folder(value)

    @field_validator("requestText")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return normalize_request_text(value)


class SessionContext(BaseModel):
    sessionId: str
    selectedFolder: str
    requestText: str


class OperationType(str, Enum):
    MOVE = "Taşı"
    COPY = "Kopyala"
    DELETE = "Sil"
    RENAME = "Yeniden Adlandır"
    LIST = "Listele"
    MERGE = "Birleştir"
    # Saga #305: SPLIT MERGE'in tam tersi - 1 kaynak PDF -> N tek-sayfalik
    # cikti dosyasi.
    SPLIT = "Böl"
    OCR = "OCR"
    # Saga #320: REDACT - MERGE/SPLIT ile AYNI "1 kaynak PDF, COPY semantigiyle
    # rollback (sadece hedefi sil)" deseni, ama TAM OLARAK 1 kaynak -> 1 hedef.
    REDACT = "Karart"
    # Saga #324: EXCEL_SORT - MERGE/REDACT ile AYNI "1 kaynak -> 1 hedef,
    # kaynak asla degismez" deseni, ama Excel (.xlsx) sayfasi uzerinde
    # satir sirasi degistirir (formul-guvenlik-agi ile korunur).
    EXCEL_SORT = "Excel Sırala"
    # Saga #325: EXCEL_FILTER - EXCEL_SORT ile AYNI "1 kaynak -> 1 hedef,
    # kaynak asla degismez" deseni, satir sirasi degil satir ALT KUMESI
    # (bir sutun degerine esit satirlar) uretir.
    EXCEL_FILTER = "Excel Filtrele"
    # Saga #321: PDF_EXTRACT_PAGES/PDF_DELETE_PAGES - EXCEL_FILTER ile AYNI
    # "1 kaynak -> 1 hedef, kaynak asla degismez" deseni, PDF sayfa
    # aralığı/listesi (`pageSpec`) uzerinde calisir.
    PDF_EXTRACT_PAGES = "PDF Sayfa Çıkar"
    PDF_DELETE_PAGES = "PDF Sayfa Sil"
    # Saga #322: PDF_COMPRESS - EXCEL_SORT'un "1 kaynak -> 1 hedef, kaynak
    # asla degismez" deseniyle AYNI, tek bir cikti dosya adi disinda ek
    # zorunlu alan yok (filterColumn/filterValue gibi bir esleme yok).
    PDF_COMPRESS = "PDF Sıkıştır"
    # Saga #323: APPEND - 1 kaynak PDF'in SONUNA appendText'ten render
    # edilmis yeni bir sayfa eklenir, kaynak dosya YERINDE guncellenir
    # (gecici-dosya+atomik-replace deseniyle, bkz. orchestrator._forward_append).
    APPEND = "Ekle"
    # Saga #326: EXCEL_CREATE - kaynaksız bir operasyon (fileNames tam
    # olarak 0 eleman - MERGE'in ">=2"/SPLIT/APPEND'in "==1" desenlerinin
    # yanına yeni bir "==0" varyantı), sıfırdan bir .xlsx dosyası
    # (createdFileName) yazar.
    EXCEL_CREATE = "Excel Oluştur"
    # Saga #326: EXCEL_APPEND - PDF APPEND'in BİREBİR AYNI "kaynağı
    # YERİNDE güncelle" deseni, ama metin sayfası yerine satır (appendRows)
    # ekler.
    EXCEL_APPEND = "Excel Ekle"
    # Saga #327: WORD_APPEND_TABLE - EXCEL_APPEND ile AYNI "kaynağı YERİNDE
    # güncelle" deseni, ama satır (appendRows) yerine bir Word tablosu
    # (tableHeaders opsiyonel + tableRows zorunlu) ekler.
    WORD_APPEND_TABLE = "Word Tablo Ekle"
    # Saga #339: WORD_TO_PDF - EXCEL_FILTER ile AYNI "1 kaynak -> 1 hedef,
    # kaynak asla degismez" deseni, .docx dosyasini LibreOffice --convert-to
    # pdf ile .pdf'e donusturur.
    WORD_TO_PDF = "Word'u PDF Yap"
    # Saga #328: ZIP_CREATE/ZIP_ADD/ZIP_EXTRACT/ZIP_MERGE - zipfile stdlib
    # üzerinden dört temel zip operasyonu (bkz. artifacts/zip-temel-
    # operasyonlar/atdd.md).
    ZIP_CREATE = "Zip Oluştur"
    ZIP_ADD = "Zip'e Ekle"
    ZIP_EXTRACT = "Zip Çıkar"
    ZIP_MERGE = "Zip Birleştir"
    # Saga #329: IMAGE_CROP/IMAGE_THUMBNAIL - EXCEL_FILTER ile AYNI "1
    # kaynak -> 1 hedef, kaynak asla degismez" deseni, gorsel (PNG/JPEG vb.)
    # uzerinde piksel-uzayinda kirpma/kucultme yapar.
    IMAGE_CROP = "Görsel Kırp"
    IMAGE_THUMBNAIL = "Görsel Küçük Resim"


class CropBox(BaseModel):
    """Saga #329: IMAGE_CROP icin kirpma alani - `RedactionRegion`'in
    x0/y0/x1/y1 alan yapisinin kopyasi, ama PDF-nokta-uzayindaki `page`
    alani OLMADAN (IMAGE_CROP tek-gorsel, piksel-uzayinda calisir).
    ÖNEMLİ: geometri (x1>x0/y1>y0) VE kaynak sınırlarını aşma kontrolü
    BİLİNÇLİ olarak burada YAPILMAZ (test_orchestrator.py AC-3 çalışma
    zamanında `PlanApplicationError` bekliyor, şema seviyesinde
    `ValidationError` değil) — bu kontrol `image_ops.crop_image` içinde
    ELLE yapılır (plan.md Risks)."""

    x0: float
    y0: float
    x1: float
    y1: float


class RedactionRegion(BaseModel):
    """Saga #320: REDACT edilecek TEK bir sayfa uzerindeki dikdortgen bolge.

    Koordinatlar PDF NOKTA uzayindadir (72 nokta/inch, sayfanin
    `mediabox`'iyla AYNI birim ve koken sozlesmesi) - x0/y0 sayfanin
    SOL-ALT kosesi, x1/y1 SAG-UST kosesi (PDF'in kendi koordinat
    sistemi, GORUNTU/piksel uzayi DEGIL). `pdf_redact.redact_pdf_page`
    bunlari rasterize edilen goruntunun piksel uzayina (sol-ust kokenli)
    donusturur - bkz. Saga #320 red-team bulgusu 1 (once yanlislikla
    dogrudan piksel uzayinda cizdiriliyordu)."""

    page: int
    x0: float
    y0: float
    x1: float
    y1: float

    @field_validator("page")
    @classmethod
    def page_at_least_one(cls, value: int) -> int:
        if value < 1:
            raise ValueError("page must be >= 1")
        return value

    @field_validator("x0", "y0", "x1", "y1")
    @classmethod
    def coordinate_non_negative(cls, value: float) -> float:
        if value < 0:
            raise ValueError("coordinates must be >= 0")
        return value

    @model_validator(mode="after")
    def x1_greater_than_x0_and_y1_greater_than_y0(self) -> "RedactionRegion":
        if self.x1 <= self.x0:
            raise ValueError("x1 must be greater than x0")
        if self.y1 <= self.y0:
            raise ValueError("y1 must be greater than y0")
        return self


class PlanStep(BaseModel):
    order: int
    operationType: OperationType
    targetFolder: str
    affectedFileCount: int
    # Saga #286 red-team bulgusu: önceden hangi dosyanın hangi step'e ait
    # olduğu belirtilmiyordu, Orchestrator pdf_files'ı sırayla dağıtıyordu
    # (kırılgan varsayım — LLM/istemci sırası uyuşmazsa dosyalar YANLIŞ
    # step'e taşınabilirdi). Artık her step kendi dosyalarını AÇIKÇA
    # taşıyor.
    fileNames: list[str]
    # Saga #290: RENAME için yeni dosya adları — fileNames ile PARALEL
    # bir liste (aynı sıra, aynı uzunluk). SADECE operationType==RENAME
    # olduğunda dolu olmalı; diğer operationType'larda None kalmalı (bu
    # alanın MOVE/COPY/DELETE'te anlamı yok — şema netliği için
    # kısıtlandı).
    newFileNames: list[str] | None = None
    # Saga #304: MERGE için N kaynak PDF'in birleştirileceği yeni dosya adı —
    # newFileNames ile AYNI desende (SADECE operationType==MERGE olduğunda
    # dolu olmalı, diğer operationType'larda None kalmalı).
    mergedFileName: str | None = None
    # Saga #320: REDACT icin - karartilacak bolgeler ve cikti dosya adi,
    # mergedFileName ile AYNI desende (SADECE operationType==REDACT
    # olduğunda dolu olmalı, diğer operationType'larda None kalmalı).
    redactionRegions: list["RedactionRegion"] | None = None
    redactedFileName: str | None = None
    # Saga #324: EXCEL_SORT icin - siralanacak sutun + yon + cikti dosya adi,
    # mergedFileName/redactedFileName ile AYNI desende (SADECE
    # operationType==EXCEL_SORT olduğunda dolu olmalı, diğer operationType'larda
    # None kalmalı).
    sortColumn: str | None = None
    sortAscending: bool | None = None
    sortedFileName: str | None = None
    # Saga #325: EXCEL_FILTER icin - filtrelenecek sutun + esitlenecek deger
    # + cikti dosya adi, sortColumn/sortedFileName ile AYNI desende (SADECE
    # operationType==EXCEL_FILTER olduğunda dolu olmalı, diğer
    # operationType'larda None kalmalı).
    filterColumn: str | None = None
    filterValue: str | int | float | None = None
    filteredFileName: str | None = None
    # Saga #321: PDF_EXTRACT_PAGES/PDF_DELETE_PAGES icin - cikarilacak/
    # silinecek sayfalari belirten "1,3,5-9" bicimindeki metin +
    # operationType'a gore cikti dosya adi, filterColumn/filteredFileName ile
    # AYNI desende (SADECE ilgili operationType'da dolu olmali, digerlerinde
    # None kalmali).
    pageSpec: str | None = None
    extractedFileName: str | None = None
    remainingFileName: str | None = None
    # Saga #322: PDF_COMPRESS icin - sikistirilmis ciktinin dosya adi,
    # sortedFileName ile AYNI desende (SADECE operationType==PDF_COMPRESS
    # olduğunda dolu olmalı, diğer operationType'larda None kalmalı).
    compressedFileName: str | None = None
    # Saga #339: WORD_TO_PDF icin - donusturulen PDF ciktinin dosya adi,
    # compressedFileName ile AYNI desende (SADECE operationType==WORD_TO_PDF
    # olduğunda dolu olmalı, diğer operationType'larda None kalmalı).
    pdfFileName: str | None = None
    # Saga #323: APPEND icin - kaynagin sonuna eklenecek metin, mergedFileName
    # ile AYNI desende (SADECE operationType==APPEND olduğunda dolu olmalı,
    # diğer operationType'larda None kalmalı). max_length=5000 (Threat-Model
    # Notu, atdd.md: DoS mitigasyonu).
    appendText: str | None = Field(default=None, max_length=5000)
    # Saga #326: EXCEL_CREATE icin - sifirdan yazilacak satirlar + cikti
    # dosya adi, mergedFileName ile AYNI desende (SADECE
    # operationType==EXCEL_CREATE olduğunda dolu olmalı, diğer
    # operationType'larda None kalmalı). "rows" ORTAK bir alan DEGIL -
    # EXCEL_APPEND kendi appendRows'unu kullanir (plan.md, bilincli tercih).
    createRows: list | None = None
    createdFileName: str | None = None
    # Saga #326: EXCEL_APPEND icin - kaynagin sonuna eklenecek satirlar,
    # appendText ile AYNI desende (SADECE operationType==EXCEL_APPEND
    # olduğunda dolu olmalı, diğer operationType'larda None kalmalı).
    appendRows: list | None = None
    # Saga #327: WORD_APPEND_TABLE icin - eklenecek tablonun basligi
    # (opsiyonel) ve veri satirlari, appendRows ile AYNI desende (SADECE
    # operationType==WORD_APPEND_TABLE olduğunda dolu olmalı, diğer
    # operationType'larda None kalmalı).
    tableHeaders: list | None = None
    tableRows: list | None = None
    # Saga #328: ZIP_CREATE icin - olusturulacak zip'in dosya adi,
    # mergedFileName ile AYNI desende (SADECE operationType==ZIP_CREATE
    # olduğunda dolu olmalı, diğer operationType'larda None kalmalı).
    zippedFileName: str | None = None
    # Saga #328: ZIP_EXTRACT icin - cikarilacak hedef klasor adi. targetFolder
    # (YYYY-MM'e kilitli) ile AYNI ALAN DEGIL - plan.md karari geregi AYRI,
    # serbest-formatli bir alan (path-separator validator'i var ama YYYY-MM
    # kisiti YOK).
    destinationFolder: str | None = None
    # Saga #328: ZIP_ADD icin - zip'e eklenecek dosyalarin listesi (fileNames
    # ile AYNI tip), addedFileName eklenmis ciktinin dosya adi.
    filesToAdd: list[str] | None = None
    addedFileName: str | None = None
    # Saga #328: ZIP_MERGE icin - birlestirilmis ciktinin dosya adi,
    # mergedFileName ile AYNI desende ama ZIP_MERGE'e ozel.
    mergedZipFileName: str | None = None
    # Saga #329: IMAGE_CROP icin - kirpilacak piksel-uzayi alani + cikti
    # dosya adi, filterColumn/filteredFileName ile AYNI desende (SADECE
    # operationType==IMAGE_CROP olduğunda dolu olmalı, diğer
    # operationType'larda None kalmalı).
    cropBox: "CropBox | None" = None
    croppedFileName: str | None = None
    # Saga #329: IMAGE_THUMBNAIL icin - en-boy orani korunarak kucultmenin
    # ust siniri + cikti dosya adi, cropBox/croppedFileName ile AYNI
    # desende (SADECE operationType==IMAGE_THUMBNAIL olduğunda dolu olmalı,
    # diğer operationType'larda None kalmalı).
    maxWidth: int | None = None
    maxHeight: int | None = None
    thumbnailFileName: str | None = None

    @field_validator("mergedFileName")
    @classmethod
    def merged_file_name_has_no_path_separators(cls, value: str | None) -> str | None:
        if value is not None and ("/" in value or "\\" in value):
            raise ValueError("mergedFileName must not contain path separators")
        return value

    @field_validator("redactedFileName")
    @classmethod
    def redacted_file_name_has_no_path_separators(cls, value: str | None) -> str | None:
        if value is not None and ("/" in value or "\\" in value):
            raise ValueError("redactedFileName must not contain path separators")
        return value

    @field_validator("sortedFileName")
    @classmethod
    def sorted_file_name_has_no_path_separators(cls, value: str | None) -> str | None:
        if value is not None and ("/" in value or "\\" in value):
            raise ValueError("sortedFileName must not contain path separators")
        return value

    @field_validator("filteredFileName")
    @classmethod
    def filtered_file_name_has_no_path_separators(cls, value: str | None) -> str | None:
        if value is not None and ("/" in value or "\\" in value):
            raise ValueError("filteredFileName must not contain path separators")
        return value

    @field_validator("extractedFileName")
    @classmethod
    def extracted_file_name_has_no_path_separators(cls, value: str | None) -> str | None:
        if value is not None and ("/" in value or "\\" in value):
            raise ValueError("extractedFileName must not contain path separators")
        return value

    @field_validator("remainingFileName")
    @classmethod
    def remaining_file_name_has_no_path_separators(cls, value: str | None) -> str | None:
        if value is not None and ("/" in value or "\\" in value):
            raise ValueError("remainingFileName must not contain path separators")
        return value

    @field_validator("compressedFileName")
    @classmethod
    def compressed_file_name_has_no_path_separators(cls, value: str | None) -> str | None:
        if value is not None and ("/" in value or "\\" in value):
            raise ValueError("compressedFileName must not contain path separators")
        return value

    @field_validator("pdfFileName")
    @classmethod
    def pdf_file_name_has_no_path_separators(cls, value: str | None) -> str | None:
        if value is not None and ("/" in value or "\\" in value):
            raise ValueError("pdfFileName must not contain path separators")
        return value

    @field_validator("createdFileName")
    @classmethod
    def created_file_name_has_no_path_separators(cls, value: str | None) -> str | None:
        if value is not None and ("/" in value or "\\" in value):
            raise ValueError("createdFileName must not contain path separators")
        return value

    @field_validator("zippedFileName")
    @classmethod
    def zipped_file_name_has_no_path_separators(cls, value: str | None) -> str | None:
        if value is not None and ("/" in value or "\\" in value):
            raise ValueError("zippedFileName must not contain path separators")
        return value

    @field_validator("destinationFolder")
    @classmethod
    def destination_folder_has_no_path_separators(cls, value: str | None) -> str | None:
        if value is not None and ("/" in value or "\\" in value):
            raise ValueError("destinationFolder must not contain path separators")
        return value

    @field_validator("addedFileName")
    @classmethod
    def added_file_name_has_no_path_separators(cls, value: str | None) -> str | None:
        if value is not None and ("/" in value or "\\" in value):
            raise ValueError("addedFileName must not contain path separators")
        return value

    @field_validator("mergedZipFileName")
    @classmethod
    def merged_zip_file_name_has_no_path_separators(cls, value: str | None) -> str | None:
        if value is not None and ("/" in value or "\\" in value):
            raise ValueError("mergedZipFileName must not contain path separators")
        return value

    @field_validator("filesToAdd")
    @classmethod
    def files_to_add_has_no_path_separators(cls, value: list[str] | None) -> list[str] | None:
        if value is not None and any("/" in name or "\\" in name for name in value):
            raise ValueError("filesToAdd entries must not contain path separators")
        return value

    @field_validator("croppedFileName")
    @classmethod
    def cropped_file_name_has_no_path_separators(cls, value: str | None) -> str | None:
        if value is not None and ("/" in value or "\\" in value):
            raise ValueError("croppedFileName must not contain path separators")
        return value

    @field_validator("thumbnailFileName")
    @classmethod
    def thumbnail_file_name_has_no_path_separators(cls, value: str | None) -> str | None:
        if value is not None and ("/" in value or "\\" in value):
            raise ValueError("thumbnailFileName must not contain path separators")
        return value

    @field_validator("appendText")
    @classmethod
    def append_text_not_blank_if_given(cls, value: str | None) -> str | None:
        # AC-5: None kabul edilir (APPEND dışı operationType'larda hiç
        # geçirilmez) ama verilmişse boş/whitespace-only reddedilir —
        # SearchRequest.contentContains ile AYNI desen.
        if value is not None and value.strip() == "":
            raise ValueError("appendText must not be empty or whitespace-only")
        return value

    @field_validator("order", "affectedFileCount")
    @classmethod
    def non_negative(cls, value: int) -> int:
        if value < 0:
            raise ValueError("must be a non-negative integer")
        return value

    @field_validator("targetFolder")
    @classmethod
    def target_folder_matches_year_month(cls, value: str) -> str:
        if not TARGET_FOLDER_PATTERN.match(value.strip()):
            raise ValueError("must be a YYYY-MM folder name (e.g. '2026-08')")
        return value

    @field_validator("fileNames")
    @classmethod
    def file_names_not_blank(cls, value: list[str]) -> list[str]:
        if any(name.strip() == "" for name in value):
            raise ValueError("fileNames must not contain empty or whitespace-only entries")
        return value

    @field_validator("fileNames")
    @classmethod
    def file_names_have_no_path_separators(cls, value: list[str]) -> list[str]:
        # Saga #286 red-team bulgusu: bugün `_distribute_files_to_steps`
        # sadece `pdf_files`'ta (zaten ayraçsız) BULUNAN isimleri kabul
        # ettiği için traversal fiilen kapalı, ama bu şema-seviyesinde
        # DEĞİL — PdfFileMetadata.filename ile aynı defense-in-depth
        # ilkesi burada da uygulanmalı (Saga #272 deseni).
        if any("/" in name or "\\" in name for name in value):
            raise ValueError("fileNames entries must not contain path separators")
        return value

    @model_validator(mode="after")
    def affected_file_count_matches_file_names(self) -> "PlanStep":
        if self.affectedFileCount != len(self.fileNames):
            raise ValueError("affectedFileCount must equal len(fileNames)")
        return self

    @model_validator(mode="after")
    def file_names_have_no_duplicates(self) -> "PlanStep":
        # Red-team bulgusu (Saga #290): çapraz-step tekrarı zaten
        # orchestrator._distribute_files_to_steps'te engelleniyordu ama
        # AYNI step İÇİNDE fileNames'in kendisi tekrar içerebiliyordu —
        # RENAME için bu, `dict(zip(fileNames, newFileNames))`'in bir
        # eşlemeyi SESSİZCE kaybetmesine yol açardı (ör. fileNames=
        # ["a.pdf","a.pdf"], newFileNames=["x.pdf","y.pdf"] → sadece
        # a.pdf->y.pdf uygulanır, x.pdf'e dönüştürme niyeti sessizce
        # kaybolur). 3. red-team turunda (Windows case-insensitive dosya
        # sistemi) `os.path.normcase` ile normalize edilerek genişletildi —
        # "a.pdf" ve "A.pdf" de aynı gerçek dosyayı temsil eder.
        normalized = [os.path.normcase(name) for name in self.fileNames]
        if len(set(normalized)) != len(normalized):
            raise ValueError("fileNames must not contain duplicate entries (case-insensitive)")
        return self

    @model_validator(mode="after")
    def new_file_names_only_for_rename(self) -> "PlanStep":
        if self.operationType == OperationType.RENAME:
            if self.newFileNames is None:
                raise ValueError("newFileNames is required when operationType is RENAME")
            if len(self.newFileNames) != len(self.fileNames):
                raise ValueError("newFileNames must have the same length as fileNames")
            if any(name.strip() == "" for name in self.newFileNames):
                raise ValueError("newFileNames must not contain empty or whitespace-only entries")
            if any("/" in name or "\\" in name for name in self.newFileNames):
                raise ValueError("newFileNames entries must not contain path separators")
            normalized_new = [os.path.normcase(name) for name in self.newFileNames]
            if len(set(normalized_new)) != len(normalized_new):
                raise ValueError("newFileNames must not contain duplicate entries (case-insensitive)")
            # Red-team bulgusu (Saga #290): newFileNames, AYNI step'teki
            # BAŞKA bir fileNames (kaynak) girdisiyle çakışırsa
            # "zincirleme rename" oluşur — ör. a.pdf->b.pdf VE b.pdf->c.pdf
            # aynı step'te olursa, b.pdf hem bir taşımanın hedefi hem
            # başka bir taşımanın kaynağı olur; işlem sırasına göre
            # b.pdf'in ORİJİNAL içeriği sessizce kaybolabilir. Bu tamamen
            # yasaklanıyor. ÖNEMLİ: kendi kendine (AYNI index'teki)
            # sadece-harf-büyüklüğü rename'i (a.pdf->A.pdf) İSTİSNA —
            # bu güvenli bir tek-dosya işlemidir, "çakışma" DEĞİLDİR (3.
            # red-team turu bulgusu — ilk saf normcase-set kesişimi bunu
            # yanlışlıkla reddediyordu).
            normalized_sources = [os.path.normcase(name) for name in self.fileNames]
            for dest_index, dest in enumerate(normalized_new):
                for source_index, source in enumerate(normalized_sources):
                    if dest_index != source_index and dest == source:
                        raise ValueError(
                            f"newFileNames[{dest_index}] ('{self.newFileNames[dest_index]}') "
                            f"collides with fileNames[{source_index}] ('{self.fileNames[source_index]}') "
                            "(case-insensitive) — chained rename within a single step is not allowed"
                        )
        elif self.newFileNames is not None:
            raise ValueError("newFileNames must be omitted unless operationType is RENAME")
        return self

    @model_validator(mode="after")
    def merged_file_name_only_for_merge(self) -> "PlanStep":
        # Saga #304: RENAME'in newFileNames'iyle AYNI desen — mergedFileName
        # SADECE MERGE için zorunlu, diğer operationType'larda tamamen
        # yasak (şema netliği için). Ayrıca en az 2 dosya birleştirilmeden
        # (fileNames uzunluğu < 2) MERGE anlamsız — burada şema seviyesinde
        # reddedilir.
        if self.operationType == OperationType.MERGE:
            if self.mergedFileName is None:
                raise ValueError("mergedFileName is required when operationType is MERGE")
            if self.mergedFileName.strip() == "":
                raise ValueError("mergedFileName must not be empty or whitespace-only")
            if len(self.fileNames) < 2:
                raise ValueError("fileNames must contain at least 2 entries when operationType is MERGE")
            # Red-team bulgusu (Saga #304): mergedFileName, AYNI step'teki
            # fileNames (kaynak) girdilerinden BİRİYLE çakışırsa,
            # orchestrator._forward_merge kaynak dosyayı hem okumak
            # (PdfWriter.append) hem de AYNI path'e yazmak (hedef) zorunda
            # kalır — bu kaynak dosyanın içeriğini bozabilir/kesebilir,
            # "kaynak dosyalara asla dokunulmaz" garantisini ihlal eder.
            # RENAME'in newFileNames/fileNames çakışma kontrolüyle AYNI
            # desen (os.path.normcase, case-insensitive).
            normalized_merged = os.path.normcase(self.mergedFileName)
            normalized_sources = [os.path.normcase(name) for name in self.fileNames]
            if normalized_merged in normalized_sources:
                raise ValueError(
                    f"mergedFileName ('{self.mergedFileName}') collides with one of this "
                    "step's fileNames (case-insensitive) — merge output must not overwrite "
                    "a source file"
                )
        elif self.mergedFileName is not None:
            raise ValueError("mergedFileName must be omitted unless operationType is MERGE")
        return self

    @model_validator(mode="after")
    def redact_fields_only_for_redact(self) -> "PlanStep":
        # Saga #320: mergedFileName/newFileNames ile AYNI desen -
        # redactionRegions/redactedFileName SADECE REDACT icin zorunlu,
        # diger operationType'larda tamamen yasak.
        if self.operationType == OperationType.REDACT:
            if not self.redactionRegions:
                raise ValueError("redactionRegions is required (non-empty) when operationType is REDACT")
            if self.redactedFileName is None or self.redactedFileName.strip() == "":
                raise ValueError("redactedFileName is required when operationType is REDACT")
            if len(self.fileNames) != 1:
                raise ValueError("fileNames must contain exactly 1 entry when operationType is REDACT")
            normalized_redacted = os.path.normcase(self.redactedFileName)
            normalized_sources = [os.path.normcase(name) for name in self.fileNames]
            if normalized_redacted in normalized_sources:
                raise ValueError(
                    f"redactedFileName ('{self.redactedFileName}') collides with one of this "
                    "step's fileNames (case-insensitive) — redact output must not overwrite "
                    "a source file"
                )
        else:
            if self.redactionRegions is not None:
                raise ValueError("redactionRegions must be omitted unless operationType is REDACT")
            if self.redactedFileName is not None:
                raise ValueError("redactedFileName must be omitted unless operationType is REDACT")
        return self

    @model_validator(mode="after")
    def excel_sort_fields_only_for_excel_sort(self) -> "PlanStep":
        # Saga #324: mergedFileName/redactedFileName ile AYNI desen -
        # sortColumn/sortAscending/sortedFileName SADECE EXCEL_SORT icin
        # zorunlu, diger operationType'larda tamamen yasak.
        if self.operationType == OperationType.EXCEL_SORT:
            if self.sortColumn is None or self.sortColumn.strip() == "":
                raise ValueError("sortColumn is required when operationType is EXCEL_SORT")
            if self.sortAscending is None:
                raise ValueError("sortAscending is required when operationType is EXCEL_SORT")
            if self.sortedFileName is None or self.sortedFileName.strip() == "":
                raise ValueError("sortedFileName is required when operationType is EXCEL_SORT")
            if len(self.fileNames) != 1:
                raise ValueError("fileNames must contain exactly 1 entry when operationType is EXCEL_SORT")
            normalized_sorted = os.path.normcase(self.sortedFileName)
            normalized_sources = [os.path.normcase(name) for name in self.fileNames]
            if normalized_sorted in normalized_sources:
                raise ValueError(
                    f"sortedFileName ('{self.sortedFileName}') collides with one of this "
                    "step's fileNames (case-insensitive) — sort output must not overwrite "
                    "a source file"
                )
        else:
            if self.sortColumn is not None:
                raise ValueError("sortColumn must be omitted unless operationType is EXCEL_SORT")
            if self.sortAscending is not None:
                raise ValueError("sortAscending must be omitted unless operationType is EXCEL_SORT")
            if self.sortedFileName is not None:
                raise ValueError("sortedFileName must be omitted unless operationType is EXCEL_SORT")
        return self

    @model_validator(mode="after")
    def excel_filter_fields_only_for_excel_filter(self) -> "PlanStep":
        # Saga #325: excel_sort_fields_only_for_excel_sort ile AYNI desen -
        # filterColumn/filterValue/filteredFileName SADECE EXCEL_FILTER icin
        # zorunlu, diger operationType'larda tamamen yasak.
        if self.operationType == OperationType.EXCEL_FILTER:
            if self.filterColumn is None or self.filterColumn.strip() == "":
                raise ValueError("filterColumn is required when operationType is EXCEL_FILTER")
            if self.filterValue is None:
                raise ValueError("filterValue is required when operationType is EXCEL_FILTER")
            if self.filteredFileName is None or self.filteredFileName.strip() == "":
                raise ValueError("filteredFileName is required when operationType is EXCEL_FILTER")
            if len(self.fileNames) != 1:
                raise ValueError("fileNames must contain exactly 1 entry when operationType is EXCEL_FILTER")
            normalized_filtered = os.path.normcase(self.filteredFileName)
            normalized_sources = [os.path.normcase(name) for name in self.fileNames]
            if normalized_filtered in normalized_sources:
                raise ValueError(
                    f"filteredFileName ('{self.filteredFileName}') collides with one of this "
                    "step's fileNames (case-insensitive) — filter output must not overwrite "
                    "a source file"
                )
        else:
            if self.filterColumn is not None:
                raise ValueError("filterColumn must be omitted unless operationType is EXCEL_FILTER")
            if self.filterValue is not None:
                raise ValueError("filterValue must be omitted unless operationType is EXCEL_FILTER")
            if self.filteredFileName is not None:
                raise ValueError("filteredFileName must be omitted unless operationType is EXCEL_FILTER")
        return self

    @model_validator(mode="after")
    def pdf_extract_pages_fields_only_for_pdf_extract_pages(self) -> "PlanStep":
        # Saga #321: excel_filter_fields_only_for_excel_filter ile AYNI desen -
        # pageSpec/extractedFileName SADECE PDF_EXTRACT_PAGES icin zorunlu,
        # diger operationType'larda tamamen yasak.
        if self.operationType == OperationType.PDF_EXTRACT_PAGES:
            if self.pageSpec is None or self.pageSpec.strip() == "":
                raise ValueError("pageSpec is required when operationType is PDF_EXTRACT_PAGES")
            if self.extractedFileName is None or self.extractedFileName.strip() == "":
                raise ValueError("extractedFileName is required when operationType is PDF_EXTRACT_PAGES")
            if len(self.fileNames) != 1:
                raise ValueError("fileNames must contain exactly 1 entry when operationType is PDF_EXTRACT_PAGES")
            normalized_extracted = os.path.normcase(self.extractedFileName)
            normalized_sources = [os.path.normcase(name) for name in self.fileNames]
            if normalized_extracted in normalized_sources:
                raise ValueError(
                    f"extractedFileName ('{self.extractedFileName}') collides with one of this "
                    "step's fileNames (case-insensitive) — extract output must not overwrite "
                    "a source file"
                )
        else:
            if self.extractedFileName is not None:
                raise ValueError("extractedFileName must be omitted unless operationType is PDF_EXTRACT_PAGES")
        return self

    @model_validator(mode="after")
    def pdf_delete_pages_fields_only_for_pdf_delete_pages(self) -> "PlanStep":
        # Saga #321: excel_filter_fields_only_for_excel_filter ile AYNI desen -
        # pageSpec/remainingFileName SADECE PDF_DELETE_PAGES icin zorunlu,
        # diger operationType'larda tamamen yasak.
        if self.operationType == OperationType.PDF_DELETE_PAGES:
            if self.pageSpec is None or self.pageSpec.strip() == "":
                raise ValueError("pageSpec is required when operationType is PDF_DELETE_PAGES")
            if self.remainingFileName is None or self.remainingFileName.strip() == "":
                raise ValueError("remainingFileName is required when operationType is PDF_DELETE_PAGES")
            if len(self.fileNames) != 1:
                raise ValueError("fileNames must contain exactly 1 entry when operationType is PDF_DELETE_PAGES")
            normalized_remaining = os.path.normcase(self.remainingFileName)
            normalized_sources = [os.path.normcase(name) for name in self.fileNames]
            if normalized_remaining in normalized_sources:
                raise ValueError(
                    f"remainingFileName ('{self.remainingFileName}') collides with one of this "
                    "step's fileNames (case-insensitive) — delete output must not overwrite "
                    "a source file"
                )
        else:
            if self.remainingFileName is not None:
                raise ValueError("remainingFileName must be omitted unless operationType is PDF_DELETE_PAGES")
        if self.operationType not in (
            OperationType.PDF_EXTRACT_PAGES,
            OperationType.PDF_DELETE_PAGES,
        ) and self.pageSpec is not None:
            raise ValueError(
                "pageSpec must be omitted unless operationType is PDF_EXTRACT_PAGES or PDF_DELETE_PAGES"
            )
        return self

    @model_validator(mode="after")
    def pdf_compress_fields_only_for_pdf_compress(self) -> "PlanStep":
        # Saga #322: excel_filter_fields_only_for_excel_filter ile AYNI desen
        # (minimal versiyonu, sortedFileName'e daha yakin) - compressedFileName
        # SADECE PDF_COMPRESS icin zorunlu, diger operationType'larda tamamen
        # yasak. Bu operasyonda filterColumn/filterValue gibi ek zorunlu bir
        # alan YOK.
        if self.operationType == OperationType.PDF_COMPRESS:
            if self.compressedFileName is None or self.compressedFileName.strip() == "":
                raise ValueError("compressedFileName is required when operationType is PDF_COMPRESS")
            if len(self.fileNames) != 1:
                raise ValueError("fileNames must contain exactly 1 entry when operationType is PDF_COMPRESS")
            normalized_compressed = os.path.normcase(self.compressedFileName)
            normalized_sources = [os.path.normcase(name) for name in self.fileNames]
            if normalized_compressed in normalized_sources:
                raise ValueError(
                    f"compressedFileName ('{self.compressedFileName}') collides with one of this "
                    "step's fileNames (case-insensitive) — compress output must not overwrite "
                    "a source file"
                )
        else:
            if self.compressedFileName is not None:
                raise ValueError("compressedFileName must be omitted unless operationType is PDF_COMPRESS")
        return self

    @model_validator(mode="after")
    def word_to_pdf_fields_only_for_word_to_pdf(self) -> "PlanStep":
        # Saga #339: pdf_compress_fields_only_for_pdf_compress ile AYNI desen
        # - pdfFileName SADECE WORD_TO_PDF icin zorunlu, diger
        # operationType'larda tamamen yasak. Bu operasyonda ek zorunlu bir alan YOK.
        if self.operationType == OperationType.WORD_TO_PDF:
            if self.pdfFileName is None or self.pdfFileName.strip() == "":
                raise ValueError("pdfFileName is required when operationType is WORD_TO_PDF")
            if len(self.fileNames) != 1:
                raise ValueError("fileNames must contain exactly 1 entry when operationType is WORD_TO_PDF")
            normalized_pdf = os.path.normcase(self.pdfFileName)
            normalized_sources = [os.path.normcase(name) for name in self.fileNames]
            if normalized_pdf in normalized_sources:
                raise ValueError(
                    f"pdfFileName ('{self.pdfFileName}') collides with one of this "
                    "step's fileNames (case-insensitive) — word-to-pdf output must not overwrite "
                    "a source file"
                )
        else:
            if self.pdfFileName is not None:
                raise ValueError("pdfFileName must be omitted unless operationType is WORD_TO_PDF")
        return self

    @model_validator(mode="after")
    def file_names_length_exactly_one_for_split(self) -> "PlanStep":
        # Saga #305: SPLIT MERGE'in tam tersi - MERGE "en az 2 kaynak"
        # gerektirirken, SPLIT TAM OLARAK 1 kaynak gerektirir (birden fazla
        # dosyayi AYNI step'te bolmek, her biri farklı sayida cikti
        # uretecegi icin belirsizlik yaratir, bkz. ATDD S3).
        if self.operationType == OperationType.SPLIT and len(self.fileNames) != 1:
            raise ValueError("fileNames must contain exactly 1 entry when operationType is SPLIT")
        return self

    @model_validator(mode="after")
    def file_names_length_exactly_one_for_ocr(self) -> "PlanStep":
        if self.operationType == OperationType.OCR and len(self.fileNames) != 1:
            raise ValueError("fileNames must contain exactly 1 entry when operationType is OCR")
        return self

    @model_validator(mode="after")
    def append_text_only_for_append(self) -> "PlanStep":
        # Saga #323: mergedFileName/redactedFileName ile AYNI desen -
        # appendText SADECE APPEND için zorunlu, diğer operationType'larda
        # tamamen yasak.
        if self.operationType == OperationType.APPEND:
            if self.appendText is None:
                raise ValueError("appendText is required when operationType is APPEND")
            if len(self.fileNames) != 1:
                raise ValueError("fileNames must contain exactly 1 entry when operationType is APPEND")
        elif self.appendText is not None:
            raise ValueError("appendText must be omitted unless operationType is APPEND")
        return self

    @model_validator(mode="after")
    def excel_create_fields_only_for_excel_create(self) -> "PlanStep":
        # Saga #326: excel_filter_fields_only_for_excel_filter ile AYNI
        # desen - createRows/createdFileName SADECE EXCEL_CREATE icin
        # zorunlu, diger operationType'larda tamamen yasak. EXCEL_CREATE
        # kaynaksiz bir operasyon oldugu icin fileNames TAM OLARAK 0 eleman
        # olmali (MERGE'in ">=2"/SPLIT'in "==1" desenlerinin yanina yeni
        # bir "==0" varyanti, plan.md ile dogrulandi).
        if self.operationType == OperationType.EXCEL_CREATE:
            if self.createRows is None or len(self.createRows) == 0:
                raise ValueError("createRows is required when operationType is EXCEL_CREATE")
            if self.createdFileName is None or self.createdFileName.strip() == "":
                raise ValueError("createdFileName is required when operationType is EXCEL_CREATE")
            if len(self.fileNames) != 0:
                raise ValueError("fileNames must contain exactly 0 entries when operationType is EXCEL_CREATE")
        else:
            if self.createRows is not None:
                raise ValueError("createRows must be omitted unless operationType is EXCEL_CREATE")
            if self.createdFileName is not None:
                raise ValueError("createdFileName must be omitted unless operationType is EXCEL_CREATE")
        return self

    @model_validator(mode="after")
    def excel_append_fields_only_for_excel_append(self) -> "PlanStep":
        # Saga #326: append_text_only_for_append ile AYNI desen -
        # appendRows SADECE EXCEL_APPEND icin zorunlu, diger
        # operationType'larda tamamen yasak.
        if self.operationType == OperationType.EXCEL_APPEND:
            if self.appendRows is None or len(self.appendRows) == 0:
                raise ValueError("appendRows is required when operationType is EXCEL_APPEND")
            if len(self.fileNames) != 1:
                raise ValueError("fileNames must contain exactly 1 entry when operationType is EXCEL_APPEND")
        elif self.appendRows is not None:
            raise ValueError("appendRows must be omitted unless operationType is EXCEL_APPEND")
        return self

    @model_validator(mode="after")
    def word_append_table_fields_only_for_word_append_table(self) -> "PlanStep":
        # Saga #327: excel_append_fields_only_for_excel_append ile AYNI
        # desen - tableRows SADECE WORD_APPEND_TABLE icin zorunlu,
        # tableHeaders OPSIYONEL (None olabilir), diger operationType'larda
        # ikisi de tamamen yasak.
        if self.operationType == OperationType.WORD_APPEND_TABLE:
            if self.tableRows is None or len(self.tableRows) == 0:
                raise ValueError("tableRows is required when operationType is WORD_APPEND_TABLE")
            if len(self.fileNames) != 1:
                raise ValueError("fileNames must contain exactly 1 entry when operationType is WORD_APPEND_TABLE")
        else:
            if self.tableHeaders is not None:
                raise ValueError("tableHeaders must be omitted unless operationType is WORD_APPEND_TABLE")
            if self.tableRows is not None:
                raise ValueError("tableRows must be omitted unless operationType is WORD_APPEND_TABLE")
        return self

    @model_validator(mode="after")
    def zip_create_fields_only_for_zip_create(self) -> "PlanStep":
        # Saga #328: MERGE'in ">=2" degil, en az 1 dosya zip'lemek yeterli
        # (klasor rekursif DEGIL, atdd.md karari) - zippedFileName SADECE
        # ZIP_CREATE icin zorunlu, diger operationType'larda tamamen yasak.
        if self.operationType == OperationType.ZIP_CREATE:
            if self.zippedFileName is None or self.zippedFileName.strip() == "":
                raise ValueError("zippedFileName is required when operationType is ZIP_CREATE")
            if len(self.fileNames) < 1:
                raise ValueError("fileNames must contain at least 1 entry when operationType is ZIP_CREATE")
            normalized_zipped = os.path.normcase(self.zippedFileName)
            normalized_sources = [os.path.normcase(name) for name in self.fileNames]
            if normalized_zipped in normalized_sources:
                raise ValueError(
                    f"zippedFileName ('{self.zippedFileName}') collides with one of this "
                    "step's fileNames (case-insensitive) — zip output must not overwrite "
                    "a source file"
                )
        else:
            if self.zippedFileName is not None:
                raise ValueError("zippedFileName must be omitted unless operationType is ZIP_CREATE")
        return self

    @model_validator(mode="after")
    def zip_add_fields_only_for_zip_add(self) -> "PlanStep":
        # Saga #328: EXCEL_FILTER'in "==1 kaynak" deseni - filesToAdd/
        # addedFileName SADECE ZIP_ADD icin zorunlu, diger operationType'larda
        # tamamen yasak.
        if self.operationType == OperationType.ZIP_ADD:
            if self.filesToAdd is None or len(self.filesToAdd) == 0:
                raise ValueError("filesToAdd is required when operationType is ZIP_ADD")
            if self.addedFileName is None or self.addedFileName.strip() == "":
                raise ValueError("addedFileName is required when operationType is ZIP_ADD")
            if len(self.fileNames) != 1:
                raise ValueError("fileNames must contain exactly 1 entry when operationType is ZIP_ADD")
        else:
            if self.filesToAdd is not None:
                raise ValueError("filesToAdd must be omitted unless operationType is ZIP_ADD")
            if self.addedFileName is not None:
                raise ValueError("addedFileName must be omitted unless operationType is ZIP_ADD")
        return self

    @model_validator(mode="after")
    def zip_extract_fields_only_for_zip_extract(self) -> "PlanStep":
        # Saga #328: EXCEL_FILTER'in "==1 kaynak" deseni - destinationFolder
        # SADECE ZIP_EXTRACT icin zorunlu, diger operationType'larda tamamen
        # yasak.
        if self.operationType == OperationType.ZIP_EXTRACT:
            if self.destinationFolder is None or self.destinationFolder.strip() == "":
                raise ValueError("destinationFolder is required when operationType is ZIP_EXTRACT")
            if len(self.fileNames) != 1:
                raise ValueError("fileNames must contain exactly 1 entry when operationType is ZIP_EXTRACT")
        else:
            if self.destinationFolder is not None:
                raise ValueError("destinationFolder must be omitted unless operationType is ZIP_EXTRACT")
        return self

    @model_validator(mode="after")
    def zip_merge_fields_only_for_zip_merge(self) -> "PlanStep":
        # Saga #328: MERGE'in ">=2 kaynak" deseni - mergedZipFileName SADECE
        # ZIP_MERGE icin zorunlu, diger operationType'larda tamamen yasak.
        if self.operationType == OperationType.ZIP_MERGE:
            if self.mergedZipFileName is None or self.mergedZipFileName.strip() == "":
                raise ValueError("mergedZipFileName is required when operationType is ZIP_MERGE")
            if len(self.fileNames) < 2:
                raise ValueError("fileNames must contain at least 2 entries when operationType is ZIP_MERGE")
            normalized_merged = os.path.normcase(self.mergedZipFileName)
            normalized_sources = [os.path.normcase(name) for name in self.fileNames]
            if normalized_merged in normalized_sources:
                raise ValueError(
                    f"mergedZipFileName ('{self.mergedZipFileName}') collides with one of this "
                    "step's fileNames (case-insensitive) — merge output must not overwrite "
                    "a source file"
                )
        else:
            if self.mergedZipFileName is not None:
                raise ValueError("mergedZipFileName must be omitted unless operationType is ZIP_MERGE")
        return self

    @model_validator(mode="after")
    def image_crop_fields_only_for_image_crop(self) -> "PlanStep":
        # Saga #329: excel_filter_fields_only_for_excel_filter ile AYNI
        # desen - cropBox/croppedFileName SADECE IMAGE_CROP icin zorunlu,
        # diger operationType'larda tamamen yasak.
        if self.operationType == OperationType.IMAGE_CROP:
            if self.cropBox is None:
                raise ValueError("cropBox is required when operationType is IMAGE_CROP")
            if self.croppedFileName is None or self.croppedFileName.strip() == "":
                raise ValueError("croppedFileName is required when operationType is IMAGE_CROP")
            if len(self.fileNames) != 1:
                raise ValueError("fileNames must contain exactly 1 entry when operationType is IMAGE_CROP")
            normalized_cropped = os.path.normcase(self.croppedFileName)
            normalized_sources = [os.path.normcase(name) for name in self.fileNames]
            if normalized_cropped in normalized_sources:
                raise ValueError(
                    f"croppedFileName ('{self.croppedFileName}') collides with one of this "
                    "step's fileNames (case-insensitive) — crop output must not overwrite "
                    "a source file"
                )
        else:
            if self.cropBox is not None:
                raise ValueError("cropBox must be omitted unless operationType is IMAGE_CROP")
            if self.croppedFileName is not None:
                raise ValueError("croppedFileName must be omitted unless operationType is IMAGE_CROP")
        return self

    @model_validator(mode="after")
    def image_thumbnail_fields_only_for_image_thumbnail(self) -> "PlanStep":
        # Saga #329: image_crop_fields_only_for_image_crop ile AYNI desen -
        # maxWidth/maxHeight/thumbnailFileName SADECE IMAGE_THUMBNAIL icin
        # zorunlu, diger operationType'larda tamamen yasak. maxWidth/
        # maxHeight'in POZITIF olması (AC-6) BİLİNÇLİ olarak burada
        # kontrol EDİLMEZ — test_orchestrator.py AC-6 çalışma zamanında
        # `PlanApplicationError` bekliyor, şema seviyesinde `ValidationError`
        # değil; bu kontrol `image_ops.create_thumbnail` içinde yapılır.
        if self.operationType == OperationType.IMAGE_THUMBNAIL:
            if self.maxWidth is None:
                raise ValueError("maxWidth is required when operationType is IMAGE_THUMBNAIL")
            if self.maxHeight is None:
                raise ValueError("maxHeight is required when operationType is IMAGE_THUMBNAIL")
            if self.thumbnailFileName is None or self.thumbnailFileName.strip() == "":
                raise ValueError("thumbnailFileName is required when operationType is IMAGE_THUMBNAIL")
            if len(self.fileNames) != 1:
                raise ValueError("fileNames must contain exactly 1 entry when operationType is IMAGE_THUMBNAIL")
            normalized_thumbnail = os.path.normcase(self.thumbnailFileName)
            normalized_sources = [os.path.normcase(name) for name in self.fileNames]
            if normalized_thumbnail in normalized_sources:
                raise ValueError(
                    f"thumbnailFileName ('{self.thumbnailFileName}') collides with one of this "
                    "step's fileNames (case-insensitive) — thumbnail output must not overwrite "
                    "a source file"
                )
        else:
            if self.maxWidth is not None:
                raise ValueError("maxWidth must be omitted unless operationType is IMAGE_THUMBNAIL")
            if self.maxHeight is not None:
                raise ValueError("maxHeight must be omitted unless operationType is IMAGE_THUMBNAIL")
            if self.thumbnailFileName is not None:
                raise ValueError("thumbnailFileName must be omitted unless operationType is IMAGE_THUMBNAIL")
        return self


class DateSource(str, Enum):
    """Not: `PlanSkeleton.steps` boşsa (taşınacak PDF yoksa),
    `dateSource`/`sortOrder` yine de şema tutarlılığı için gerçek bir enum
    değeri taşır ama HİÇBİR GERÇEK KARARI TEMSİL ETMEZ — `generate_plan_skeleton`
    bu durumda LLM'e hiç istek atmadan varsayılan değerler atar (bkz.
    plan_generation.py). Downstream kod (Security/Orchestrator, Saga #271+)
    bu alanları `steps` boşken anlamlı veri gibi yorumlamamalı (red-team
    bulgusu, Saga #270)."""

    CREATED_AT = "created_at"


class SortOrder(str, Enum):
    ASCENDING = "ascending"
    DESCENDING = "descending"


class PlanSkeleton(BaseModel):
    steps: list[PlanStep]
    dateSource: DateSource
    sortOrder: SortOrder

    @field_validator("steps")
    @classmethod
    def unique_orders(cls, value: list[PlanStep]) -> list[PlanStep]:
        orders = [step.order for step in value]
        if len(orders) != len(set(orders)):
            raise ValueError("step order values must be unique")
        return value


class PdfFileMetadata(BaseModel):
    filename: str
    createdAt: str

    @field_validator("filename", "createdAt")
    @classmethod
    def not_blank(cls, value: str) -> str:
        if value.strip() == "":
            raise ValueError("must not be empty or whitespace-only")
        return value

    @field_validator("filename")
    @classmethod
    def filename_has_no_path_separators(cls, value: str) -> str:
        # Saga #272 red-team bulgusu: path-traversal/derinlik istismarının
        # tek gerçek yüzeyi filename'dir (targetFolder zaten YYYY-MM
        # regex'iyle kilitli) — bunu şema seviyesinde erkenden kapatmak,
        # backend/security.py'deki runtime derinlik kontrolünü gerçek bir
        # defense-in-depth yapar, TEK savunma olmaktan çıkarır.
        if "/" in value or "\\" in value:
            raise ValueError("must not contain path separators")
        return value


class SearchResultItem(BaseModel):
    """Saga #313: Dosya arama sonucu — `filename`, `extension`, `modifiedAt`,
    `sizeBytes` içerir. Mutlak path İÇERMEZ (Saga #283 ilkesiyle tutarlı)."""

    filename: str
    extension: str
    modifiedAt: str
    sizeBytes: int

    @field_validator("filename")
    @classmethod
    def filename_has_no_path_separators(cls, value: str) -> str:
        if "/" in value or "\\" in value:
            raise ValueError("must not contain path separators")
        return value

    @field_validator("modifiedAt")
    @classmethod
    def modified_at_not_blank(cls, value: str) -> str:
        if value.strip() == "":
            raise ValueError("must not be empty or whitespace-only")
        return value

    @field_validator("sizeBytes")
    @classmethod
    def size_bytes_non_negative(cls, value: int) -> int:
        if value < 0:
            raise ValueError("must be non-negative")
        return value


class TransactionPreviewFile(BaseModel):
    """Saga #317: diff-tray önizlemesindeki TEK bir dosya satırı. `name`
    (ve `before`/`after`) SADECE dosya adı (`Path.name`) — tam path
    Saga #283 ilkesiyle tutarlı şekilde asla taşınmaz."""

    name: str
    before: str | None
    after: str | None
    # "ok": önce/sonra hesaplanabildi. "unknown": hesaplanamadı (kısmi
    # başarı, davranış sözleşmesi durum 7) — satır atlanmaz, işaretlenir.
    status: str
    # Bu TEK dosya için "geri getirilemez" durumu (ör. DELETE yedeği
    # purge edilmiş) — transaction-seviyesindeki `available`den FARKLI,
    # dosya-seviyesinde.
    available: bool = True
    reason: str | None = None


class TransactionPreview(BaseModel):
    """Saga #317: `TransactionSummary.preview` alanının şekli. `empty`
    ("değişiklik yok") ile `available=False` ("önizleme mevcut değil")
    KASITLI olarak ayrı alanlar — aynı boş görünüm arkasındaki farklı kök
    nedenler UI'da farklı mesajla gösterilmeli (atdd.md davranış
    sözleşmesi, "boş sonuç ↔ hata ayrımı")."""

    files: list[TransactionPreviewFile]
    truncated: bool
    total_count: int
    empty: bool
    # Transaction-seviyesinde önizleme hiç mevcut değilse (ör. TÜM
    # operasyonlar purge edilmiş DELETE'ler) False olur.
    available: bool = True
    reason: str | None = None


class TransactionSummary(BaseModel):
    """Saga #294: `GET /api/transactions`'ın döndürdüğü, geçmiş bir
    işlemin ÖZETİ — tam `FileOperation` satırları (kaynak/hedef tam
    path'ler) İÇERMEZ, sadece `targetFolders` klasör ADLARINI taşır
    (Saga #283'teki "tam path istemciye sızdırılmaz" ilkesiyle tutarlı).
    Saga #317: `preview` alanı, hover'da gösterilen hafif dosya-adı
    önizlemesini taşır — aynı path-sızdırmama ilkesine tabidir."""

    id: int
    createdAt: dt.datetime
    status: str
    fileCount: int
    targetFolders: list[str]
    preview: TransactionPreview


class RevertTransactionRequest(BaseModel):
    """Saga #301: `revert_transaction`'ın kullandığı `allowed_root` artık
    `Transaction` tablosunda server tarafında kaydedilir (bkz.
    `db_models.Transaction.allowed_root`) — Saga #294/#295'teki "kolon YOK,
    istemciden gönderilir" kararı bir güvenlik açığıydı (istemci spoofed bir
    `allowedRoot` ile başka bir köke ait dosyaları geri alma mantığına
    sokabilirdi). Bu yüzden istemciden hiçbir alan alınmaz; şu an boş, ama
    gelecekte genişleyebilir."""

    pass


class RevertTransactionResponse(BaseModel):
    transactionId: int
    status: str


class ApplyPlanRequest(BaseModel):
    """Saga #309: onaylanan planı `POST /api/transactions/apply`e taşır.
    `plan` tam `PlanSkeleton` (fileNames dahil) — backend henüz `/api/plan`
    yanıtını server tarafında saklamıyor, bu yüzden istemci HAM yanıtı
    olduğu gibi geri gönderir (bkz. atdd.md Soru 1/2)."""

    sessionId: str
    plan: PlanSkeleton

    @field_validator("sessionId")
    @classmethod
    def session_id_not_blank(cls, value: str) -> str:
        if value.strip() == "":
            raise ValueError("must not be empty or whitespace-only")
        return value


class AppliedFileOperation(BaseModel):
    """Frontend'in `transactionResult.ts`'teki `BackendFileOperation` ile
    birebir eşleşmesi için alan adları AYNEN snake_case (Saga #277
    sözleşmesi, camelCase'e ÇEVRİLMEZ)."""

    destination_path: str
    status: str


class TransactionApplyResponse(BaseModel):
    id: int
    status: str
    operations: list[AppliedFileOperation]
    # Saga #320 red-team bulgusu 3 (AC6/P1): REDACT adimi ciktisi ARTIK
    # rasterize edilmis bir sayfa icerir - metin katmani kaybolur (bu
    # ISTENEN garanti) ama YAN ETKI olarak dosya buyur ve o sayfa artik
    # aranabilir/kopyalanabilir DEGILDIR. İstemcinin bunu sessizce
    # kesfetmemesi icin her REDACT step'i icin bir uyari metni.
    warnings: list[str] = []


class PlanRequest(BaseModel):
    # Saga #285: pdfFiles istemciden ALINMAZ — backend, session'ın
    # selectedFolder'ını kendisi tarar (backend/pdf_discovery.py). İstemcinin
    # dosya listesi göndermesi (a) client'ın PDF içeriğine erişimini
    # gerektirir (Tauri fs plugin, yeni native bağımlılık) ve (b) whitelist
    # doğrulamasının güvendiği "kaynak dosya" listesini istemcinin
    # kontrolüne bırakırdı — backend'in kendi taraması daha az güven
    # sınırı taşır.
    sessionId: str

    @field_validator("sessionId")
    @classmethod
    def session_id_not_blank(cls, value: str) -> str:
        if value.strip() == "":
            raise ValueError("must not be empty or whitespace-only")
        return value


class SearchRequest(BaseModel):
    """Saga #313: Dosya arama endpoint'i için istek şeması."""

    sessionId: str
    nameContains: str | None = None
    extension: str | None = None
    modifiedAfter: str | None = None
    modifiedBefore: str | None = None
    # Saga #314: icerik arama (AC-4/AC-9) - bos/whitespace-only reddedilir,
    # 500 karakterle sinirlanir.
    contentContains: str | None = Field(default=None, max_length=500)
    # Saga #316: fuzzy/regex isim eslesmesi - birbirini disleyen iki mod
    # (endpoint seviyesinde AC-4 ile birlikte kullanimi 422 ile reddedilir).
    # Red-team follow-up (Saga #316, medium bulgusu): contentContains ile
    # AYNI ucuz ReDoS mitigasyonu - ucuncu parti kutuphane gerektirmeden
    # asiri uzun/karmasik pattern'leri en bastan reddet. namePattern regex
    # oldugu icin fuzzyName'den biraz daha uzun bir sinir aliyor.
    fuzzyName: str | None = Field(default=None, max_length=100)
    namePattern: str | None = Field(default=None, max_length=200)

    @field_validator("sessionId")
    @classmethod
    def session_id_not_blank(cls, value: str) -> str:
        if value.strip() == "":
            raise ValueError("must not be empty or whitespace-only")
        return value

    @field_validator("contentContains")
    @classmethod
    def content_contains_not_blank_if_given(cls, value: str | None) -> str | None:
        if value is not None and value.strip() == "":
            raise ValueError("must not be empty or whitespace-only")
        return value


class SearchResponse(BaseModel):
    """Saga #313: Dosya arama endpoint'i yanıtı."""

    results: list[SearchResultItem]
    # Saga #314 (AC-2): global 10sn timeout asilirsa True - o ana kadarki
    # kismi sonuclar dondurulur, hata firlatilmaz.
    partial: bool = False


class ExcelReadRequest(BaseModel):
    """Saga #326: `/api/excel/read` istek şeması - `SearchRequest` ile AYNI
    session/allowed_root doğrulama deseni (senkron sorgu, plan/transaction
    kavramı YOK)."""

    sessionId: str
    filename: str
    range: str | None = None

    @field_validator("filename")
    @classmethod
    def filename_has_no_path_separators(cls, value: str) -> str:
        if "/" in value or "\\" in value:
            raise ValueError("filename must not contain path separators")
        return value


class ExcelReadResponse(BaseModel):
    """Saga #326: `/api/excel/read` yanıt şeması."""

    values: list[list]
    range: str | None = None


class ZipListRequest(BaseModel):
    """Saga #328: `/api/zip/list` istek şeması - `ExcelReadRequest` ile AYNI
    session/allowed_root doğrulama deseni (senkron sorgu, plan/transaction
    kavramı YOK)."""

    sessionId: str
    filename: str

    @field_validator("filename")
    @classmethod
    def filename_has_no_path_separators(cls, value: str) -> str:
        if "/" in value or "\\" in value:
            raise ValueError("filename must not contain path separators")
        return value


class ZipListResponse(BaseModel):
    """Saga #328: `/api/zip/list` yanıt şeması."""

    entries: list[dict]


class ScanStartResponse(BaseModel):
    """Saga #337: `POST /api/search/scan` yanıtı — arka planda başlatılan
    taramanın kimliği, tarama henüz TAMAMLANMADAN döner (AC-1)."""

    scanId: str


class ScanStatusResponse(BaseModel):
    """Saga #337: `GET /api/search/scan/{scan_id}` yanıtı."""

    status: Literal["running", "done", "not_found"]
    scannedCount: int
    results: list[SearchResultItem] | None = None
    partial: bool | None = None


class DetectPiiRequest(BaseModel):
    """Saga #333: `/api/pdf/detect-pii` istek şeması - `ExcelReadRequest` ile
    AYNI session/allowed_root doğrulama deseni (senkron sorgu)."""

    sessionId: str
    filename: str

    @field_validator("filename")
    @classmethod
    def filename_has_no_path_separators(cls, value: str) -> str:
        if "/" in value or "\\" in value:
            raise ValueError("filename must not contain path separators")
        return value


class DetectPiiResponse(BaseModel):
    """Saga #333: `/api/pdf/detect-pii` yanıt şeması — AC-S1 güvenlik
    kısıtlaması: ham TC kimlik no/IBAN değerleri hiçbir yerde YER ALMAZ,
    sadece RedactionRegion (page + koordinatlar)."""

    regions: list[RedactionRegion]
