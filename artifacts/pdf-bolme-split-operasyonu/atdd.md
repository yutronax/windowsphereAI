---
task_slug: pdf-bolme-split-operasyonu
priority: medium
coverage_target: "80/0/20"
performance_target: "yok"
test_strategy: "unit (pytest, gerçek pypdf ile gerçek geçici PDF dosyaları)"
affected_modules:
  - backend/models.py
  - backend/orchestrator.py
  - backend/plan_generation.py
saga_task_id: 305
epic_id: 29
---

# ATDD — PDF Bölme (SPLIT) Operasyonu (Saga #305)

## Goal
Tek bir kaynak PDF'i birden fazla yeni PDF'e bölen bir operasyon
eklemek. MERGE'in (Saga #304) TAM TERSİ şekli: MERGE "N kaynak → 1
hedef", SPLIT "1 kaynak → N hedef".

## Sorular ve Cevaplar (saga-oto tarafından otomatik seçildi)

**S1: Sayfa aralığına mı, sayfa başına mı bölme?** Cevap: **Sayfa
başına (her sayfa kendi dosyasına).** Task açıklaması iki seçenek
sunuyor ("sayfa aralığına VEYA sayfa başına"). Sayfa ARALIĞI, LLM'in
plan'a `[[1,3],[4,7],...]` gibi bir aralık listesi üretmesini
gerektirir — bu hem şemaya yeni, karmaşık bir alan eklemeyi hem de
LLM'in aralıkların GEÇERLİ/ÇAKIŞMASIZ/kaynak sayfa sayısını AŞMAYAN
olduğunu garanti etmesini gerektirirdi (LLM plan üretim ANINDA gerçek
sayfa sayısını bilmiyor, sadece dosya adı+tarih görüyor — Saga #292).
Sayfa başına bölme bu sorunu TAMAMEN ORTADAN KALDIRIYOR: hiçbir yeni
şema alanı gerekmiyor, çıktı dosya adları KAYNAK dosya adından
TÜRETİLİYOR (`kaynak.pdf` → `kaynak_1.pdf`, `kaynak_2.pdf`, ...),
gerçek sayfa sayısı SADECE apply_plan çalışırken (dosya gerçekten
açıldığında) bilinir. (saga-oto tarafından otomatik seçildi — dar
kapsam, MVP'nin en dar kapsamlı ve LLM-güvenli yorumu; sayfa-aralığı
gerçek bir talep çıkarsa ayrı bir takip task'ı olarak eklenebilir)

**S2: Mimari — MERGE'in ANALOJİSİ mi kullanılmalı?** Cevap: EVET,
simetrik ters şekil. `apply_plan`'ın ana döngüsüne MERGE'e benzer bir
özel dal eklenir: TEK kaynağı açar, HER SAYFA için AYRI bir
`FileOperation` kaydı oluşturur (destination=o sayfanın çıktı dosyası,
backup=destination — MERGE'deki AYNI desen), `_rollback_copy`
(sadece hedefi sil, kaynağa dokunma) HER kayıt için bağımsız çalışır —
SPLIT'e özel YENİ bir rollback fonksiyonu GEREKMİYOR (COPY'nin
zaten paylaştığı fonksiyon N kez çağrılır). (saga-oto tarafından
otomatik seçildi — MERGE'in kurduğu deseni simetrik olarak yeniden
kullanır, kod tekrarı yok)

**S3: `fileNames` uzunluğu SPLIT için ne olmalı?** Cevap: TAM OLARAK 1
— SPLIT tek bir kaynağı böler, birden fazla dosyayı AYNI step'te
bölmek (her biri farklı sayıda çıktı üretir) belirsizlik yaratır,
şema seviyesinde reddedilir. (saga-oto tarafından otomatik seçildi —
MERGE'in "en az 2" kısıtının simetriği, dar kapsam)

**S4: Çıktı dosya adı çakışması nasıl önlenir?** Cevap: Çıktı adları
SADECE apply_plan ÇALIŞIRKEN (gerçek sayfa sayısı bilindiğinde)
hesaplanabildiği için, `validate_plan_paths` (plan ONAYLANMADAN önce
çalışır) bunları ÖNCEDEN doğrulayamaz — bu, MERGE/RENAME'in
`validate_...destinations` desenlerinden BİLİNÇLİ bir SAPMADIR (ATDD'de
açıkça not edilen bir sınırlama). Bunun yerine ÇALIŞMA ZAMANINDA
(apply_plan'ın SPLIT dalı içinde), her çıktı dosyası YAZILMADAN HEMEN
ÖNCE `output_path.exists()` kontrol edilir — VARSA, tüm işlem
`PlanApplicationError` ile reddedilir (mevcut genel except-bloğu
transaction'ı TAMAMEN geri alır, o ana kadar yazılmış SPLIT çıktıları
dahil). Bu, RENAME'in `shutil.move`'un sessizce üzerine yazmasını
önleyen ÖNCEDEN-doğrulama ilkesiyle AYNI SONUCA (asla sessiz üzerine
yazma) farklı bir ZAMANLAMA ile ulaşır. (saga-oto tarafından otomatik
seçildi — dar kapsam, gerçek sayfa sayısı bilinmeden ön-doğrulama
mümkün değil)

**S5: Yazma güvenliği (Saga #304'ün MERGE red-team dersi)?** Cevap:
HER çıktı dosyası, MERGE'in düzeltilmiş `_forward_merge`iyle AYNI
geçici-dosya-yaz + atomik-taşı desenini kullanır — yarıda kesilen bir
yazma gerçek hedefte yarım/bozuk bir dosya BIRAKMAZ. (saga-oto
tarafından otomatik seçildi — Saga #304'ün red-team bulgusundan
öğrenilen dersin doğrudan uygulanması)

**S6: `PLAN_SYSTEM_PROMPT`a SPLIT eklenmeli mi?** Cevap: EVET —
"böl", "sayfalara ayır" → "Böl" eşlemesi eklenir, `fileNames`in SPLIT
için TAM OLARAK 1 dosya içermesi gerektiği belirtilir. Yeni bir şema
alanı GEREKMİYOR (S1 kararı sayesinde). (saga-oto tarafından otomatik
seçildi — Saga #292/#304 emsaline tutarlı)

## Kabul Kriterleri
1. **AC-1 (kritik):** `apply_plan`, `operationType: "Böl"` içeren bir
   step'i işleyip kaynak PDF'in HER sayfası için `{stem}_{sayfa_no}.pdf`
   adında AYRI bir dosya üretiyor, sayfa içeriği doğru.
2. **AC-2 (kritik):** Kaynak dosya bölme SONRASI DOKUNULMADAN duruyor.
3. **AC-3 (yüksek):** Herhangi bir çıktı dosyası ADI zaten VARSA (plan
   BİLMEDİĞİ bir dosyayla çakışıyorsa), TÜM transaction reddediliyor,
   HİÇBİR dosya sessizce üzerine yazılmıyor.
4. **AC-4 (yüksek):** Bir SPLIT step'i başarısız olursa (kısmi
   yazıldıktan sonra), rollback O ANA KADAR yazılmış TÜM çıktı
   dosyalarını siliyor, kaynağa dokunmuyor.
5. **AC-5 (orta):** `fileNames` uzunluğu SPLIT için 1 DEĞİLSE şema
   seviyesinde reddediliyor.
6. **AC-6 (orta):** `PLAN_SYSTEM_PROMPT` "Böl" eşlemesini içeriyor.
7. **AC-7 (orta):** Mevcut tüm testler (177, Saga #304 sonrası)
   değişmeden geçmeye devam ediyor.

## Riskler / Varsayımlar / Bilinmeyenler
- Sayfa-aralığına-göre bölme (kullanıcının "1-5. sayfaları ayrı dosyaya
  koy" gibi daha ayrıntılı bir isteği) desteklenmiyor — S1'de açıkça
  ertelendi, gerçek talep çıkarsa ayrı bir task.
- Çok sayfalı (yüzlerce sayfa) bir PDF'i bölmek yüzlerce `FileOperation`
  kaydı ve yüzlerce dosya oluşturabilir — MVP ölçeğinde performans
  sorunu beklenmiyor (kod tabanında aksini gösteren kanıt yok).

## Test Stratejisi
`backend/tests/test_orchestrator.py`: gerçek çok sayfalı bir pypdf PDF'i
SPLIT ile bölünüp her çıktının DOĞRU tek sayfaya sahip olduğu + kaynağın
dokunulmadan kaldığı + rollback'in TÜM çıktıları sildiği + isim
çakışmasının TÜM transaction'ı reddettiği doğrulanır.
`backend/tests/test_models.py`: `fileNames` uzunluğu SPLIT için != 1
reddi. `backend/tests/test_plan_generation.py`: prompt rehberi.
