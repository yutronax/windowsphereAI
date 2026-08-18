# Plan — Format Agent Parametre Güvenlik Katmanı (Saga #319)

## Kapsam
Kod boşluğu YOK (bkz. atdd.md keşif bulguları) — bu görev sadece:
1. Yeni dokümantasyon bölümü (konvansiyon).
2. İki yeni test (RENAME/MERGE "alan değişince çıktı değişir" kanıtı).

Orchestrator/models.py değişikliği YOK.

## Değiştirilecek/eklenecek dosyalar
1. `docs/DESIGN_DECISIONS.md` — yeni bölüm eklenir (dosya sonuna):
   "Operasyon-özel PlanStep alanları için test konvansiyonu (Saga #319)".
   İçerik: kural metni + kısa checklist + iki mevcut örneğe (RENAME/
   MERGE) referans.
2. `backend/tests/test_orchestrator.py` — iki yeni test eklenir:
   - `test_apply_plan_rename_output_filename_changes_when_new_file_names_changes`
     — aynı `fileNames=["a.pdf"]` ile, iki farklı `apply_plan` çağrısı
     (iki farklı tmp_path/session), `newFileNames=["x.pdf"]` vs
     `newFileNames=["y.pdf"]`; her ikisinde de karşılık gelen dosyanın
     diskte oluştuğu, ve İKİ farklı ismin birbirinden bağımsız olarak
     doğru şekilde oluştuğu assert edilir.
   - `test_apply_plan_merge_output_filename_changes_when_merged_file_name_changes`
     — aynı 2 kaynak PDF ile, iki farklı `mergedFileName` değeri
     ("birlesik1.pdf" vs "birlesik2.pdf"), her ikisinde de karşılık
     gelen dosyanın oluştuğu assert edilir.

## Bağımlılıklar
Yok — sadece pytest + mevcut test fixture'ları (`_step`, `_merge_step`,
`_write_pdf`, `_write_real_pdf`, `session`, `tmp_path`).

## Riskler
- Testler mevcut yardımcı fonksiyonları (`_step`, `_merge_step`, `_plan`)
  kullanacak; imzaları değişmeyecek, sadece çağrı sayısı artacak.
- `docs/DESIGN_DECISIONS.md`'nin mevcut formatı/başlık stiliyle tutarlı
  olunacak (dosya okunup üslup eşleştirilecek).

## Uygulama sırası
1. Genel amaçlı subagent'a delege: sadece `backend/tests/test_orchestrator.py`'ye
   yukarıdaki iki testi ekle (red step — ama testler zaten var olan,
   doğru çalışan koda karşı yazılıyor, muhtemelen ilk denemede YEŞİL
   olacak çünkü wiring zaten doğru; bu görev için "red" adımı, testin
   YANLIŞ yazılıp yazılmadığını doğrulamak için kritik: örn. yanlışlıkla
   sabit bir dosya adı assert edilirse test her koşulda geçer ve hiçbir
   şey kanıtlamaz — bu yüzden ana akış (ben) testleri ayrıca
   `git stash`layıp orchestrator'ın ilgili satırını (destination_path
   hesaplaması) geçici olarak bozup testin GERÇEKTEN kırmızı olduğunu
   doğrulayacak, sonra stash'i geri getirecek).
2. `docs/DESIGN_DECISIONS.md` güncellemesini ben (ana akış) yazacağım —
   bu dokümantasyon, "test/code authoring" kapsamına girmiyor.
3. Gerçek pytest ile doğrula (verify adımı).
