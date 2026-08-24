import { useEffect, useState } from 'react';

import { BACKEND_ORIGIN } from '../../lib/backendHealth';

// gecmis-transaction-listesi-ui (epic #28): GET /api/transactions'in
// dondurdugu sekil - backend/models.py::TransactionPreview/TransactionPreviewFile
// ile AYNI alanlar. Bilincli olarak ResultCard.tsx'ten IMPORT EDILMEZ, burada
// YENIDEN TANIMLANIR (bkz. plan.md) - iki bilesen birbirinden bagimsiz kalir.
// SADECE dosya adi tasir (Saga #283 ilkesi), tam path YOK.
type PreviewFile = {
  name: string;
  before: string | null;
  after: string | null;
  status: string;
  available?: boolean;
  reason?: string | null;
};

type Preview = {
  files: PreviewFile[];
  truncated: boolean;
  total_count: number;
  empty: boolean;
  available?: boolean;
  reason?: string | null;
};

type HistoryTransaction = {
  id: number;
  createdAt: string;
  status: string;
  fileCount: number;
  targetFolders: string[];
  preview: Preview;
};

type LoadState = 'loading' | 'loaded' | 'error';

export default function HistoryPanel() {
  const [loadState, setLoadState] = useState<LoadState>('loading');
  const [transactions, setTransactions] = useState<HistoryTransaction[]>([]);

  // AC7: panel her kapat/ac'ta yeniden mount edilir (ChatScreen'deki
  // conditional render), bu da bu effect'i her acilista yeniden calistirir -
  // ekstra bir "refresh" mekanizmasina gerek yok.
  useEffect(() => {
    let cancelled = false;
    setLoadState('loading');

    fetch(`${BACKEND_ORIGIN}/api/transactions`)
      .then(async (response) => {
        if (cancelled) return;
        if (!response.ok) {
          setLoadState('error');
          return;
        }
        const body: HistoryTransaction[] = await response.json();
        if (cancelled) return;
        setTransactions(Array.isArray(body) ? body : []);
        setLoadState('loaded');
      })
      .catch(() => {
        if (cancelled) return;
        setLoadState('error');
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <section className="history-panel" data-testid="history-panel" aria-label="İşlem geçmişi">
      <style>{`
        .history-panel {
          border: 1px solid #E5E7EB;
          border-radius: 12px;
          padding: 12px 16px;
          margin-top: 8px;
          background-color: #FAFAFA;
        }
        .history-panel-row {
          border-bottom: 1px solid #E5E7EB;
          padding: 8px 0;
        }
        .history-panel-row:last-child {
          border-bottom: none;
        }
        .history-panel-folders {
          margin: 4px 0 0;
          padding-left: 20px;
          color: #4B5563;
          font-size: 14px;
        }
        .history-panel-status-text {
          color: #4B5563;
          font-size: 14px;
          margin: 4px 0 0;
        }
      `}</style>
      {loadState === 'loading' && (
        <p className="history-panel-status-text" data-testid="history-panel-loading">
          Yükleniyor…
        </p>
      )}
      {loadState === 'error' && (
        <p className="history-panel-status-text" data-testid="history-panel-error" role="alert">
          Geçmiş yüklenemedi.
        </p>
      )}
      {loadState === 'loaded' && transactions.length === 0 && (
        <p className="history-panel-status-text" data-testid="history-panel-empty">
          Henüz bir işlem geçmişi yok.
        </p>
      )}
      {loadState === 'loaded' && transactions.length > 0 && (
        <ul data-testid="history-panel-list">
          {transactions.map((transaction) => (
            <li
              key={transaction.id}
              className="history-panel-row"
              data-testid={`history-panel-row-${transaction.id}`}
            >
              <p className="history-panel-status-text">
                #{transaction.id} — {transaction.createdAt} — {transaction.status} — {transaction.fileCount} dosya
              </p>
              {transaction.targetFolders.length > 0 && (
                <ul className="history-panel-folders">
                  {transaction.targetFolders.map((folder) => (
                    <li key={folder}>{folder}</li>
                  ))}
                </ul>
              )}
              {transaction.preview.empty ? (
                <p className="history-panel-status-text">Değişiklik yok</p>
              ) : transaction.preview.available === false ? (
                <p className="history-panel-status-text">Önizleme mevcut değil</p>
              ) : (
                <ul className="history-panel-folders">
                  {transaction.preview.files.map((file, index) => (
                    <li key={`${file.name}-${index}`}>
                      {file.status === 'unknown' ? (
                        <span>{file.name || '?'} (?)</span>
                      ) : file.available === false ? (
                        <span>
                          {file.name} — Önizleme mevcut değil{file.reason ? ` (${file.reason})` : ''}
                        </span>
                      ) : (
                        <span>{file.name}</span>
                      )}
                    </li>
                  ))}
                  {transaction.preview.truncated && (
                    <li>+{transaction.preview.total_count - transaction.preview.files.length} daha</li>
                  )}
                </ul>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
