import type { TransactionResult } from '../components/chat/ResultCard';

// backend/db_models.py'deki Transaction/FileOperation şekliyle gevşek
// eşleşir (Saga #285 HTTP wiring'i gerçek bir Pydantic response şeması
// tanımlayana kadar kesin sözleşme değil, red-team bulgusu Saga #277).
export type BackendFileOperation = { destination_path: string; status: string };
export type BackendTransaction = { status: string; operations: BackendFileOperation[] };

function parentFolder(fullPath: string): string {
  const normalized = fullPath.replace(/\\/g, '/');
  const lastSlash = normalized.lastIndexOf('/');
  return lastSlash === -1 ? normalized : normalized.slice(0, lastSlash);
}

function uniqueParentFolders(operations: BackendFileOperation[]): string[] {
  return Array.from(new Set(operations.map((op) => parentFolder(op.destination_path))));
}

/**
 * backend'in `Transaction`/`FileOperation` kayıtlarını `ResultCard`'ın
 * beklediği `TransactionResult`'a çevirir. `transaction.status`:
 * - "committed" → tüm operasyonlar kalıcı olarak taşınmış → "completed".
 * - "rolled_back" → Saga #274/#276 TÜM taşımaları geri aldığı için net
 *   sonuçta HİÇBİR dosya kalıcı olarak taşınmamıştır → "failed" (backend
 *   "partial" bir ara durum bırakmaz, atomik geri alma "hep ya da hiç"
 *   garantisi verir).
 * - "pending" → apply_plan henüz tamamlanmamış/yarım kalmış (ör. süreç
 *   çökmesi, Saga #286) → "partial", sadece fiilen "completed" olan
 *   operasyonlar sayılır.
 */
export function toTransactionResult(transaction: BackendTransaction): TransactionResult {
  if (transaction.status === 'rolled_back') {
    return { fileCount: 0, destinationFolders: [], status: 'failed' };
  }

  if (transaction.status === 'committed') {
    return {
      fileCount: transaction.operations.length,
      destinationFolders: uniqueParentFolders(transaction.operations),
      status: 'completed',
    };
  }

  const completedOps = transaction.operations.filter((op) => op.status === 'completed');
  return {
    fileCount: completedOps.length,
    destinationFolders: uniqueParentFolders(completedOps),
    status: 'partial',
  };
}
