---
task_slug: excel-sort-formula-guard
priority: high
coverage_target: "orchestrator EXCEL_SORT dispatch + excel_sort.py sort/formula-guard logic + models.py alan sözleşmesi"
performance_target: "tek sayfalık, birkaç bin satırlık .xlsx dosyaları için saniyeler içinde"
test_strategy: "gerçek openpyxl workbook fixture'ları (mock YOK) + Saga #319 wiring-testi konvansiyonu"
affected_modules:
  - backend/models.py
  - backend/orchestrator.py
  - backend/security.py
  - backend/excel_sort.py (yeni)
  - backend/tests/test_models.py
  - backend/tests/test_orchestrator.py
  - requirements.txt
---

# ATDD — Excel: Formüllü satırların sıralanmasını engelle (Saga #324)

## Persona

Muhasebeci kullanıcı — LLM'e "Tutar sütununa göre sırala" gibi doğal dilde
bir istek verir. Elindeki .xlsx dosyasında bazı hücreler formül içerir
(örn. `=C2+C3` gibi bir ara toplam). Kullanıcı Excel/openpyxl'in fiziksel
satır taşımada formül metnini OTOMATİK OLARAK güncellemediğini bilmez —
bu, projenin **ilk Excel özelliği** olduğu için burada sıfırdan
tasarlanan bir güvenlik ağıyla kapatılmalıdır.

## Goal

Kullanıcı bir sütuna göre satır sıralaması istediğinde: sıralanacak
aralıkta (data satırları) **herhangi bir formül** varsa işlem TAMAMEN
reddedilir (sıfır satır değiştirilir, kısmi sıralama YOK) ve kullanıcıya
neden reddedildiği açıkça bildirilir. Formül yoksa satırlar gerçekten
(hücre değerleriyle) yeniden sıralanır ve yeni bir çıktı dosyasına
yazılır (kaynak dosyaya asla dokunulmaz — projenin MERGE/SPLIT/REDACT'te
kurduğu "kaynak korunur, yeni dosya üretilir" ilkesiyle tutarlı).

## User Story

"Muhasebeci olarak, bir Excel dosyasındaki satırları bir sütuna
(örn. 'Tutar') göre sıralamak istiyorum, ama dosyada formül varsa
verimin sessizce bozulmasını İSTEMİYORUM — ya işlem güvenle tamamlanır
ya da bana neden yapılamadığı açıkça söylenir."

## Prioritized Acceptance Criteria

1. **P0 — Formül tespiti sıralamayı bloke eder.** Sıralanacak veri
   aralığındaki (header hariç) herhangi bir satırın herhangi bir
   hücresi formül ise (`cell.data_type == "f"`), TÜM işlem reddedilir.
   Sıfır satır fiziksel olarak değiştirilmiş olmalı, çıktı dosyası
   oluşturulmamalı.
2. **P0 — Formül yoksa gerçek sıralama.** Formül bulunmazsa veri satırları
   hedef sütuna göre (artan/azalan) fiilen yeniden sıralanır ve YENİ bir
   dosyaya yazılır; kaynak dosya değişmeden kalır.
3. **P0 — Sütun çözümleme: header metni ÖNCE denenir.** Kullanıcı/LLM
   sütunu "Tutar" gibi bir başlık metniyle belirtirse, ilk satır (header)
   bu metinle (case-insensitive, boşluk kırpılmış) eşleşen bir hücre
   içeriyorsa o sütun kullanılır.
4. **P1 — Bare harf fallback.** Header eşleşmesi bulunamazsa VE verilen
   değer tek/çift harfli geçerli bir Excel sütun harfi ("C", "AA" gibi)
   ise o sütun harfi olarak kabul edilir.
5. **P1 — Sütun bulunamama hatası.** Ne header eşleşmesi ne geçerli bir
   sütun harfi ise açık bir hata döner, hiçbir değişiklik yapılmaz.
6. **P2 — Boş sayfa / tek satır (sadece header).** Sıralanacak veri
   satırı yoksa (0 veya sadece header) işlem no-op sayılır: dosya
   değişmeden kopyalanır/yeni ada yazılır, hata FIRLATILMAZ (sıralamanın
   anlamsız olduğu bir durum, hata değil).
7. **P2 — Path whitelist.** `allowed_root` dışına çıkan kaynak/hedef
   dosya adları merkezi `backend/security.py::validate_plan_paths` /
   `validate_excel_sort_destinations` tarafından reddedilir (excel_sort.py
   İÇİNDE path kontrolü YAPILMAZ — Saga #307 dersi, DESIGN_DECISIONS §6).

## Behavior Contract Table

| Durum | Davranış | Değişen satır sayısı |
|---|---|---|
| Sıralama aralığında ≥1 formül hücresi | `ExcelSortFormulaGuardError` (veya eşdeğer) — işlem reddedilir | 0 |
| Formül yok, sütun header metniyle bulundu | Gerçek sıralama, yeni dosyaya yazılır | tüm veri satırları |
| Formül yok, sütun bare harfle bulundu (header eşleşmesi yok) | Gerçek sıralama | tüm veri satırları |
| Header'da da harf eşlemesinde de bulunamayan sütun adı | Hata, işlem reddedilir | 0 |
| 0 veri satırı (boş sayfa veya sadece header) | No-op, dosya (kopya olarak) yeni ada yazılır, hata yok | 0 |
| `sortedFileName` kaynak dosyalardan biriyle çakışıyor | Şema seviyesinde `ValidationError` (mergedFileName/redactedFileName deseniyle AYNI) | 0 |
| Kaynak/hedef `allowed_root` dışında | `PathWhitelistError` (security.py, excel_sort.py'de DEĞİL) | 0 |

## Operation-Specific Field (Saga #319 convention, DESIGN_DECISIONS §6)

Yeni `OperationType.EXCEL_SORT`. Yeni `PlanStep` alanları:
`sortColumn: str | None`, `sortAscending: bool | None`,
`sortedFileName: str | None` — hepsi SADECE `EXCEL_SORT` için zorunlu/dolu,
diğer operationType'larda tamamen yasak (mergedFileName/redactedFileName
ile AYNI model_validator deseni). `sortedFileName`, `mergedFileName` ile
AYNI kurallara tabi: path ayracı yok, kaynak `fileNames` ile çakışamaz.

Wiring testi (ZORUNLU): `test_orchestrator.py`'de EN AZ İKİ farklı
`sortColumn` değeriyle (örn. "Tutar" header ve "B" bare harf) `apply_plan`
çağrılıp GERÇEK dosya sisteminde iki farklı somut sıralama sonucu
gözlenmeli.

## Risks / Assumptions (saga-oto tarafından otomatik seçildi)

- **Kapsam dışı (bilinçli):** Excel create/read/append genel desteği
  (Saga #326'ya bırakıldı) ve çok-sütunlu sıralama. Bu task SADECE
  tek-sütun sıralama + formül-güvenlik-ağı.
- Sıralama kararlılığı: Python `sorted()` stabil sort kullanır — eşit
  değerli satırlar orijinal sırasını korur (varsayım, dokümante edildi).
- Hücre biçimlendirmesi (renk/font) bu task'ta KORUNMAZ — sadece hücre
  DEĞERLERİ taşınır (openpyxl'de stil kopyalama ayrı bir karmaşıklık;
  P2/kapsam dışı, follow-up olarak not edilebilir).
- Birleşik hücreler (merged cells) desteklenmez — sıralama aralığında
  merged cell varsa şu an ele alınmıyor (follow-up riski).
- `sortColumn` boş string veya sadece boşluksa hata (header/harf
  eşleşmesi başarısız sayılır).
