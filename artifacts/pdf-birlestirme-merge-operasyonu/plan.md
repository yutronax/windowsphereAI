# Plan — PDF Birleştirme (MERGE) Operasyonu (Saga #304)

## Değişecek dosyalar
- `backend/models.py` — `OperationType.MERGE = "Birleştir"`;
  `PlanStep.mergedFileName: str | None = None` + validator (path
  separator yasak, sadece MERGE için zorunlu, MERGE için `fileNames`
  uzunluğu >= 2).
- `backend/security.py` — `validate_plan_paths`e MERGE hedefi için
  `_validate_single_path` çağrısı; `validate_rename_destinations`e
  benzer yeni bir `validate_merge_destinations` (veya mevcut fonksiyonu
  genelleştirme) — çakışma/zincir kontrolü.
- `backend/orchestrator.py` — `_forward_merge(source_paths, destination_path)`
  (pypdf.PdfWriter.append+write); `_FORWARD_OPERATIONS`/`_ROLLBACK_OPERATIONS`
  MERGE girdileri (rollback = `_rollback_copy`); `apply_plan`'ın ana
  döngüsünde MERGE için LIST'e benzer bir özel dal (N dosya → 1
  `FileOperation` kaydı); `_SUPPORTED_OPERATION_TYPES`e MERGE eklenir;
  `target_dir.mkdir` hariç tutma listesine MERGE eklenir (DELETE/RENAME
  gibi).
- `backend/plan_generation.py` — `PLAN_SYSTEM_PROMPT`e "birleştir" →
  "Birleştir" eşlemesi + `mergedFileName` şema açıklaması.

## Yeni bağımlılık
Yok (`pypdf` zaten Saga #303'te eklendi).

## Riskler
- `_distribute_files_to_steps`in "her dosya tam olarak bir step'e atanır"
  kısıtı MERGE'in N-dosya-tek-step doğasıyla ÇAKIŞMIYOR (zaten dosya
  bazlı, step bazlı değil) — değişiklik gerekmiyor, doğrulanacak.
- Şifreli PDF açma hatası → mevcut genel `except Exception` rollback
  mekanizması zaten yakalıyor, ek kod gerekmiyor.
