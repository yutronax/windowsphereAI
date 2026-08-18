# Plan — PDF Bölme (SPLIT) Operasyonu (Saga #305)

## Değişecek dosyalar
- `backend/models.py` — `OperationType.SPLIT = "Böl"`; `PlanStep`e yeni
  bir `model_validator`: SPLIT için `fileNames` uzunluğu TAM OLARAK 1
  değilse reddet (RENAME/MERGE validator'larının hemen yanına, aynı
  stil).
- `backend/orchestrator.py` — `_forward_split_page(source_path, page_index, destination_path)`
  (MERGE'in düzeltilmiş geçici-dosya-yaz + atomik-taşı desenini
  kullanan bir yardımcı, veya tek bir `_forward_split(source_path, output_paths)`
  fonksiyonu — HER sayfa için önce `output_path.exists()` kontrolü,
  varsa `PlanApplicationError`); `_ROLLBACK_OPERATIONS[OperationType.SPLIT] = _rollback_copy`;
  `_SUPPORTED_OPERATION_TYPES`e SPLIT; `apply_plan`'ın ana döngüsünde
  MERGE'e benzer bir özel dal — kaynağı açar, sayfa sayısınca döner,
  her sayfa için `{stem}_{sayfa_no}.pdf` hesaplar, yazar, BİR
  `FileOperation` kaydı oluşturur (N kayıt toplam); `target_dir.mkdir`
  hariç tutma listesine SPLIT eklenir (MERGE/DELETE/RENAME gibi).
- `backend/plan_generation.py` — `PLAN_SYSTEM_PROMPT`e "böl"/"sayfalara
  ayır" → "Böl" eşlemesi + SPLIT için `fileNames`in tam 1 dosya
  içermesi gerektiği notu.

## Yeni bağımlılık
Yok.

## Riskler
- Çıktı adı çakışması SADECE çalışma zamanında tespit edilebilir (ATDD
  S4) — `validate_plan_paths`e yeni bir ön-doğrulama EKLENMİYOR,
  bilinçli bir kapsam kararı.
