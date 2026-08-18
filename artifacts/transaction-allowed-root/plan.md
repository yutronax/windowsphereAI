# Plan — Transaction'a allowed_root kolonu ekle (Saga #301)

## Değiştirilecek dosyalar

### 1. `backend/db_models.py`
- `Transaction` sınıfına `allowed_root: Mapped[str | None] = mapped_column(String, nullable=True)`
  ekle. Nullable çünkü eski (migration öncesi) kayıtlarda yok, `db.py`'deki
  `_add_missing_columns` shim'i nullable/default'lı kolonları destekliyor.

### 2. `backend/file_operations.py`
- `create_transaction(session: Session, *, allowed_root: str | None = None) -> Transaction`
  imzasını güncelle, `Transaction(allowed_root=allowed_root)` olarak oluştur.

### 3. `backend/orchestrator.py`
- `apply_plan(...)` içindeki `transaction = create_transaction(session)` çağrısını
  `create_transaction(session, allowed_root=str(allowed_root))` yap.
- `revert_transaction(session: Session, transaction: Transaction) -> Transaction`
  — `allowed_root: Path` parametresini KALDIR, fonksiyon içinde
  `if transaction.allowed_root is None: raise TransactionRevertError(...)`
  ekle, sonra `Path(transaction.allowed_root)` kullan (mevcut
  `_rollback_completed_operations` çağrısına bunu geçir).
- Docstring'leri güncelle (Saga #295/#294 referanslarını Saga #301 ile
  güncelleyen bir not ekle — eski "allowed_root Transaction'da YOK" iddiası
  artık YANLIŞ, düzelt).

### 4. `backend/models.py`
- `RevertTransactionRequest`'ten `allowedRoot: str` alanını ve
  `normalize_allowed_root` validator'ını SİL, docstring'i güncelle (artık
  boş bir model, gelecekte genişleyebilir).
- `field_validator`/`normalize_selected_folder` importu başka yerde
  kullanılmıyorsa import'u temizle (kontrol et — `normalize_selected_folder`
  başka modelde de kullanılıyor olabilir, öyleyse import'u SİLME).

### 5. `backend/main.py`
- `revert_transaction_endpoint`: `payload.allowedRoot` kullanımını kaldır,
  `revert_transaction(db, transaction)` olarak çağır (allowed_root parametresi
  yok). `TransactionRevertError`'ı hâlâ yakala (NULL allowed_root durumu da
  bu exception'dan geçecek) — mevcut except bloğunun mesajını gözden geçir,
  gerekirse NULL-allowed_root durumunu ayrı bir dal olarak ele almak yerine
  aynı genel `TransactionRevertError` → mevcut hata response'una düşür (dar
  kapsam, ayrı bir HTTP status kodu icat etme).
- Docstring'i güncelle (Saga #295/#294 "istemciden gelir" cümlesini kaldır).

### 6. `ui/src/components/chat/ResultCard.tsx`
- `handleConfirmRevert`: fetch body'sini `JSON.stringify({})` yap (ya da
  `body` alanını tamamen kaldır — FastAPI boş POST body'sini boş obje olarak
  kabul ediyor mu kontrol edilecek, güvenli seçenek `JSON.stringify({})`).
- `canShowRevert` ve `handleConfirmRevert`'in erken-çıkış kontrolünü sadece
  `result.transactionId !== undefined` bak şekilde sadeleştir (ATDD S4).
  `selectedFolder` prop'u ve tip alanı KALIR (component tipi bozulmasın diye),
  sadece zorunlu-kontrol mantığından çıkar.
- Yorum satırlarını güncelle (Saga #295 → #301 referansı).

## Test dosyaları (test-copilot subagent yazacak, kod-copilot DEĞİL)
- `backend/tests/test_orchestrator.py` — yeni testler (yukarıdaki ATDD Test
  Stratejisi a/b/c).
- `backend/tests/test_main_integration.py` — revert endpoint testleri güncelle
  (mevcut `allowedRoot` gönderen testler varsa güncelle + yeni "spoofed
  allowedRoot etkisiz" testi ekle).
- `ui/src/components/chat/ResultCard.test.tsx` — fetch body assertion güncelle.

## Migration
Yok — `backend/db.py::_add_missing_columns` shim'i otomatik ekliyor
(nullable kolon). Ek kod YAZILMIYOR.

## Riskler
- `backend/models.py`'de `normalize_selected_folder` başka yerde de
  kullanılıyorsa import'u koru — implementasyon subagent'ı bunu kontrol
  etmeli.
- `revert_transaction`'ın imzasını değiştirmek onu çağıran TÜM yerleri
  (test dosyaları dahil, ~hepsi zaten task kapsamında güncellenecek)
  etkiler — grep ile tüm çağrı yerleri taranmalı.
