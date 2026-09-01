import { useEffect, useState } from 'react';
import { BACKEND_ORIGIN } from '../../lib/backendHealth';
import { relativeTime } from '../../lib/relativeTime';

type TransactionSummary = {
  id: string;
  createdAt: string;
  status: string;
  fileCount: number;
  targetFolders: string[];
};

type HealthCheckResponse = {
  status: string;
  llm_reachable: boolean;
  path_allowed: boolean;
};

type Props = {
  sessionId?: string;
  refreshTrigger?: number;
};

export default function TransactionHistoryPanel({ sessionId, refreshTrigger = 0 }: Props) {
  const [transactions, setTransactions] = useState<TransactionSummary[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<'connected' | 'disconnected' | null>(null);

  useEffect(() => {
    if (!sessionId || sessionId.trim() === '') {
      setTransactions([]);
      setIsLoading(false);
      setError(null);
      return;
    }

    let cancelled = false;

    // Fetch transactions
    const fetchTransactions = async () => {
      if (cancelled) return;
      setIsLoading(true);
      setError(null);

      const timeoutPromise = new Promise<never>((_, reject) =>
        setTimeout(() => reject(new Error('Timeout')), 3000)
      );

      try {
        const response = await Promise.race([
          fetch(`${BACKEND_ORIGIN}/api/transactions?sessionId=${encodeURIComponent(sessionId)}`, {
            method: 'GET',
          }),
          timeoutPromise,
        ]);

        if (!response.ok) {
          if (!cancelled) {
            setError('İşlem geçmişi yüklenemedi, sayfayı yenileyin');
            setTransactions([]);
            setIsLoading(false);
          }
          return;
        }

        const data: TransactionSummary[] = await response.json();
        if (!cancelled) {
          setTransactions(Array.isArray(data) ? data.slice(0, 5) : []);
          setIsLoading(false);
        }
      } catch (err) {
        if (!cancelled) {
          setError('İşlem geçmişi yüklenemedi, sayfayı yenileyin');
          setTransactions([]);
          setIsLoading(false);
        }
      }
    };

    // Fetch health status
    const fetchHealthStatus = async () => {
      try {
        const response = await fetch(`${BACKEND_ORIGIN}/api/health`, {
          method: 'GET',
        });

        if (!cancelled) {
          setConnectionStatus(response.ok ? 'connected' : 'disconnected');
        }
      } catch (err) {
        if (!cancelled) {
          setConnectionStatus('disconnected');
        }
      }
    };

    fetchTransactions();
    fetchHealthStatus();

    return () => {
      cancelled = true;
    };
  }, [sessionId, refreshTrigger]);

  if (!sessionId || sessionId.trim() === '') {
    return null;
  }

  return (
    <div data-testid="chat-left-panel" style={{ padding: '12px', borderRight: '1px solid #E5E7EB' }}>
      <div style={{ marginBottom: '12px', fontSize: '14px', fontWeight: 600 }}>
        İşlem Geçmişi
      </div>

      {connectionStatus && (
        <div
          data-testid="connection-status"
          style={{
            marginBottom: '8px',
            fontSize: '12px',
            color: connectionStatus === 'connected' ? '#059669' : '#DC2626',
          }}
        >
          {connectionStatus === 'connected' ? '✓ Bağlı' : 'Bağlantı kesildi'}
        </div>
      )}

      {isLoading && (
        <div data-testid="transaction-history-loading" style={{ padding: '8px 0', color: '#6B7280', fontSize: '13px' }}>
          Yükleniyor...
        </div>
      )}

      {error && (
        <div data-testid="transaction-history-error" style={{ padding: '8px 0', color: '#DC2626', fontSize: '13px' }}>
          {error}
        </div>
      )}

      {!isLoading && !error && transactions.length === 0 && (
        <div style={{ padding: '8px 0', color: '#6B7280', fontSize: '13px' }}>
          Henüz hiç işlem yok
        </div>
      )}

      {!isLoading && !error && transactions.length > 0 && (
        <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
          {transactions.map((tx) => (
            <li key={tx.id} style={{ padding: '8px 0', fontSize: '13px', color: '#111827', borderBottom: '1px solid #E5E7EB' }}>
              {tx.targetFolders.join(', ')} → {tx.fileCount} dosya · {relativeTime(tx.createdAt)}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
