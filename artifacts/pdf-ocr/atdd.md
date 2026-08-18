---
task_slug: pdf-ocr
priority: P2
coverage_target: 70% unit / 30% e2e (gerçek OCR motoru mock'lanır)
performance_target: N/A (MVP kapsamında performans hedefi yok; büyük dosyalar red-team'e Risk olarak bırakıldı)
test_strategy: unit-heavy, OCR motor çağrısı (pytesseract.image_to_string) her testte mock'lanır; gerçek Tesseract binary testte GEREKMEZ
affected_modules:
  - backend/pdf_ocr.py (yeni)
  - backend/tests/test_pdf_ocr.py (yeni)
  - requirements.txt
---

# PDF OCR Desteği — ATDD

Saga #306 (epic #29). Saga #299 kararıyla ayrı epic olmaktan çıkarılıp Format Agent Sistemi'nin PDF alt-özelliği olarak buraya taşındı.

## Persona
Taranmış (görüntü tabanlı, metin katmanı olmayan) PDF dosyalarıyla çalışan, bu dosyaları arattırabilir/kopyalanabilir hale getirmek isteyen kullanıcı.

## Goal
Taranmış bir PDF'in sayfalarındaki görüntüleri OCR motoruna (pytesseract) vererek metne çevirmek ve bu metni erişilebilir, test edilebilir bir arayüz üzerinden döndürmek.

## User Story
Kullanıcı olarak, taranmış bir PDF dosyasını sisteme verdiğimde, her sayfadan OCR ile çıkarılmış metni almak istiyorum; böylece dosya içeriğini arayabilir veya işleyebilirim.

## Kapsam Kararı (saga-oto tarafından otomatik seçildi)
- **Soru: OCR çıktısı ne olmalı — aranabilir PDF mi, düz metin mi?**
  Cevap: MVP kapsamında düz metin listesi (`sayfa başına metin`) döndürülür; aranabilir PDF üretimi (ocrmypdf tarzı, metin katmanını orijinal PDF'e gömme) kapsam dışı bırakıldı — bu, orchestrator'daki MERGE/SPLIT gibi dosya-üreten bir OperationType'a dönüştürülmesini gerektirir ve mevcut Format Agent orchestration'ına (models.py/orchestrator.py) entegrasyon ayrı bir Saga task'ı olarak red-team sonrası önerilecek. (saga-oto tarafından otomatik seçildi)
- **Soru: OCR motoru — pytesseract+Tesseract mi, ocrmypdf mi?**
  Cevap: pytesseract + Pillow + pdf2image seçildi (görev açıklamasında önerilen ilk seçenek); ocrmypdf daha ağır bir sistem bağımlılığı zinciri (Ghostscript vb.) gerektirir, MVP için orantısız. (saga-oto tarafından otomatik seçildi)
- **Soru: Tesseract sistem binary'si test ortamında yoksa ne olur?**
  Cevap: OCR motor çağrısının kendisi (`pytesseract.image_to_string`) modül seviyesinde bir fonksiyona (`_run_ocr_engine`) izole edilir ve TÜM testler bu fonksiyonu mock'lar; gerçek Tesseract kurulumu test suite'inin YEŞİL olması için GEREKMEZ. Bu bir Risk/Assumption olarak aşağıda belgelendi. (saga-oto tarafından otomatik seçildi)
- **Soru: PDF'den görüntü çıkarma nasıl yapılır?**
  Cevap: `pdf2image.convert_from_path` (Poppler sistem bağımlılığı gerektirir) yerine, projenin zaten bağımlılığı olan `pypdf`'in sayfa nesnelerinden `pypdf` + `Pillow` kombinasyonuyla DEĞİL — pdf2image kullanılacak ancak bu fonksiyon da (`_pdf_to_images`) ayrı bir noktada izole edilip testlerde mock'lanacak; böylece Poppler binary'si de test ortamında gerekli DEĞİL. (saga-oto tarafından otomatik seçildi)

## Prioritized Acceptance Criteria
1. (P0) `ocr_pdf_file(pdf_path: Path) -> list[str]` fonksiyonu, PDF'in her sayfası için `_pdf_to_images` ile görüntü elde eder, her görüntüyü `_run_ocr_engine`'e verir ve sayfa sırasına göre metin listesi döndürür.
2. (P0) Girdi dosyası mevcut değilse `FileNotFoundError` yükseltilir.
3. (P0) Girdi dosyası `.pdf` uzantılı değilse `ValueError` yükseltilir.
4. (P1) PDF bozuksa/açılamıyorsa (`_pdf_to_images` bir istisna fırlatırsa) bu istisna sarmalanmadan (veya açık bir `ValueError` ile) yukarı taşınır — sessiz yutulmaz.
5. (P1) Boş/0 sayfalı PDF için boş liste (`[]`) döner, hata fırlatılmaz.
6. (P2) Her sayfanın OCR metni `str.strip()` uygulanmış olarak döner (baştaki/sondaki boşluk temizlenir); OCR motoru boş string döndürürse listede boş string olarak kalır (sayfa index'i korunur).

## Behavior-Contract Table
| Durum | Girdi | Beklenen Dönüş/Davranış |
|---|---|---|
| Başarılı OCR | Var olan, geçerli, N sayfalı PDF | `list[str]`, uzunluk N, sayfa sırasına göre |
| Dosya yok | Var olmayan path | `FileNotFoundError` |
| PDF değil | `.docx`, `.txt` vb. | `ValueError("... .pdf uzantılı olmalı ...")` |
| Bozuk PDF | Geçersiz/corrupt PDF içeriği | `_pdf_to_images` istisnası yukarı taşınır (yutulmaz) |
| 0 sayfalı PDF | Boş sayfa listesi üreten PDF | `[]` |
| Tesseract sistemde yok | (yalnızca gerçek ortamda, testte mock'lu) | `_run_ocr_engine` çağrısı `pytesseract.TesseractNotFoundError` fırlatabilir; fonksiyon bunu yutmaz, çağırana taşır |

## Risks / Assumptions
- **[RISK - kabul edildi] Tesseract sistem bağımlılığı**: `pytesseract` sadece bir Python wrapper'dır; gerçek OCR için sistemde Tesseract binary'si (ve Türkçe dil paketi `tur.traineddata`) kurulu olmalıdır. Bu ortamda kurulu olduğu doğrulanmadı. Mitigasyon: OCR motor çağrısı izole edilip TÜM testler mock'landı, gerçek kurulum gerektirmiyor. Prod dağıtımı için Tesseract kurulumu ayrı bir devops/packaging adımı olarak not düşüldü (windows-ai-files zaten .exe paketleme gündeminde — bkz. proje hafızası).
- **[RISK - kabul edildi] pdf2image → Poppler bağımlılığı**: `pdf2image` de sistemde Poppler (`pdftoppm`) gerektirir; aynı şekilde `_pdf_to_images` izole edilip mock'landı.
- **[ASSUMPTION] Orchestrator entegrasyonu kapsam dışı**: Bu task sadece OCR çekirdek fonksiyonunu (pdf_discovery.py paterni gibi bağımsız modül) sağlar; yeni bir `OperationType.OCR` olarak orchestrator.py/models.py/plan_generation.py'a tam entegrasyon YAPILMADI — bu, kapsamı görev açıklamasındaki "dar kapsamı tercih et" talimatına göre bilinçli olarak dışarıda bırakıldı ve red-team sonrası ayrı bir takip Saga task'ı olarak önerilecek.

## Test Strategy
- %70 unit: `backend/tests/test_pdf_ocr.py` — `_pdf_to_images` ve `_run_ocr_engine`'i `unittest.mock.patch` ile mock'layarak sayfa-sırası, hata yolları, boş PDF, dosya yok, yanlış uzantı senaryolarını kapsar.
- %30 e2e/entegrasyon niteliğinde: gerçek küçük bir PDF (pypdf ile testte üretilen, tek sayfalı) üzerinden `ocr_pdf_file` çağrılır ama yine `_run_ocr_engine` mock'lanarak (gerçek Tesseract gerektirmeden) uçtan uca akış (dosya aç → sayfa say → OCR çağır → metin topla) doğrulanır.
- Gerçek Tesseract/Poppler kurulumu CI/test ortamında YOKTUR varsayımıyla hiçbir test bunlara bağımlı değildir.

## Benchmark
Bu MVP'de performans benchmarkı hedeflenmiyor (N/A) — fonksiyonellik ve mock-edilebilirlik önceliklidir.
