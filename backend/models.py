import datetime as dt
import os
import re
from enum import Enum

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


class TransactionSummary(BaseModel):
    """Saga #294: `GET /api/transactions`'ın döndürdüğü, geçmiş bir
    işlemin ÖZETİ — tam `FileOperation` satırları (kaynak/hedef tam
    path'ler) İÇERMEZ, sadece `targetFolders` klasör ADLARINI taşır
    (Saga #283'teki "tam path istemciye sızdırılmaz" ilkesiyle tutarlı)."""

    id: int
    createdAt: dt.datetime
    status: str
    fileCount: int
    targetFolders: list[str]


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
