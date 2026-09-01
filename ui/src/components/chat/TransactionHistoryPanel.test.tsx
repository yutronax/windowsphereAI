import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';

import TransactionHistoryPanel from './TransactionHistoryPanel';

// Mock the backendHealth module to control BACKEND_ORIGIN
vi.mock('../../lib/backendHealth', () => ({
  BACKEND_ORIGIN: 'http://localhost:8000',
  waitForBackendHealth: vi.fn(),
}));

describe('TransactionHistoryPanel (sol panel — işlem geçmişi)', () => {
  beforeEach(() => {
    // Fetch mock'larını sıfırla
    vi.clearAllMocks();
  });

  describe('Happy path — başarılı veri yükleme (AC-1)', () => {
    it('renders the last 5 transactions in the correct format (AC-1)', async () => {
      const mockTransactions = [
        {
          id: 'tx-1',
          createdAt: '2026-09-01T13:55:00Z',
          status: 'completed',
          fileCount: 3,
          targetFolders: ['Belgeler', '2026-09'],
        },
        {
          id: 'tx-2',
          createdAt: '2026-09-01T13:50:00Z',
          status: 'completed',
          fileCount: 5,
          targetFolders: ['İndirilenler'],
        },
        {
          id: 'tx-3',
          createdAt: '2026-09-01T13:45:00Z',
          status: 'completed',
          fileCount: 1,
          targetFolders: ['Masaüstü', 'Proje-A'],
        },
      ];

      const fetchMock = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => mockTransactions,
      });
      vi.stubGlobal('fetch', fetchMock);

      try {
        render(<TransactionHistoryPanel sessionId="session-123" />);

        await waitFor(() => {
          // Her işlem liste öğesi olarak render edilmeli
          const listItems = screen.getAllByRole('listitem');
          expect(listItems).toHaveLength(3);

          // Format: "{targetFolders} → {fileCount} dosya · {göreceli zaman}"
          expect(listItems[0]).toHaveTextContent('Belgeler, 2026-09 → 3 dosya');
          expect(listItems[1]).toHaveTextContent('İndirilenler → 5 dosya');
          expect(listItems[2]).toHaveTextContent('Masaüstü, Proje-A → 1 dosya');
        });

        // GET /api/transactions çağrıldığını doğrula
        expect(fetchMock).toHaveBeenCalledWith(
          expect.stringContaining('/api/transactions'),
          expect.objectContaining({ method: 'GET' })
        );
      } finally {
        vi.unstubAllGlobals();
      }
    });

    it('renders at most 5 transactions even if more are returned (AC-1)', async () => {
      const mockTransactions = Array.from({ length: 10 }, (_, i) => ({
        id: `tx-${i}`,
        createdAt: new Date(Date.now() - i * 60000).toISOString(),
        status: 'completed',
        fileCount: i + 1,
        targetFolders: [`Klasör-${i}`],
      }));

      const fetchMock = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => mockTransactions,
      });
      vi.stubGlobal('fetch', fetchMock);

      try {
        render(<TransactionHistoryPanel sessionId="session-123" />);

        await waitFor(() => {
          const listItems = screen.getAllByRole('listitem');
          expect(listItems).toHaveLength(5);
        });
      } finally {
        vi.unstubAllGlobals();
      }
    });

    it('renders transaction items as non-clickable plain text (not buttons or links) (AC-1)', async () => {
      const mockTransactions = [
        {
          id: 'tx-1',
          createdAt: '2026-09-01T13:55:00Z',
          status: 'completed',
          fileCount: 2,
          targetFolders: ['Belgeler'],
        },
      ];

      const fetchMock = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => mockTransactions,
      });
      vi.stubGlobal('fetch', fetchMock);

      try {
        render(<TransactionHistoryPanel sessionId="session-123" />);

        await waitFor(() => {
          const listItem = screen.getByRole('listitem');
          // Öğe button veya link olmamalı
          expect(listItem.tagName).not.toBe('BUTTON');
          expect(listItem.tagName).not.toBe('A');
        });
      } finally {
        vi.unstubAllGlobals();
      }
    });
  });

  describe('Loading state (AC-6)', () => {
    it('shows a loading indicator while transactions are being fetched (AC-6)', async () => {
      const fetchMock = vi.fn(() => new Promise(() => {})); // Never resolves
      vi.stubGlobal('fetch', fetchMock);

      try {
        render(<TransactionHistoryPanel sessionId="session-123" />);

        // Loading spinner/indicator görülmeli
        await waitFor(() => {
          expect(screen.getByTestId('transaction-history-loading')).toBeVisible();
        });

        // Liste boş olmalı (henüz yüklenmedi)
        expect(screen.queryByRole('listitem')).not.toBeInTheDocument();
      } finally {
        vi.unstubAllGlobals();
      }
    });
  });

  describe('Empty transactions (AC-5)', () => {
    it('renders "Henüz hiç işlem yok" when transactions list is empty (AC-5)', async () => {
      const fetchMock = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => [],
      });
      vi.stubGlobal('fetch', fetchMock);

      try {
        render(<TransactionHistoryPanel sessionId="session-123" />);

        await waitFor(() => {
          expect(screen.getByText('Henüz hiç işlem yok')).toBeVisible();
        });

        // Liste boş olmalı
        expect(screen.queryByRole('listitem')).not.toBeInTheDocument();
      } finally {
        vi.unstubAllGlobals();
      }
    });
  });

  describe('Network/API errors (AC-4)', () => {
    it('shows error message when fetch fails due to network error (AC-4)', async () => {
      const fetchMock = vi.fn().mockRejectedValue(new Error('Network error'));
      vi.stubGlobal('fetch', fetchMock);

      try {
        render(<TransactionHistoryPanel sessionId="session-123" />);

        await waitFor(() => {
          const errorMsg = screen.getByText('İşlem geçmişi yüklenemedi, sayfayı yenileyin');
          expect(errorMsg).toBeVisible();

          // Uyarı ikonu veya error indicator görülmeli
          expect(screen.getByTestId('transaction-history-error')).toBeVisible();
        });
      } finally {
        vi.unstubAllGlobals();
      }
    });

    it('shows error message when response.ok is false (AC-4)', async () => {
      const fetchMock = vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        json: async () => ({ detail: 'Internal server error' }),
      });
      vi.stubGlobal('fetch', fetchMock);

      try {
        render(<TransactionHistoryPanel sessionId="session-123" />);

        await waitFor(() => {
          expect(screen.getByText('İşlem geçmişi yüklenemedi, sayfayı yenileyin')).toBeVisible();
          expect(screen.getByTestId('transaction-history-error')).toBeVisible();
        });
      } finally {
        vi.unstubAllGlobals();
      }
    });

    it('shows error message on 404 response (AC-4)', async () => {
      const fetchMock = vi.fn().mockResolvedValue({
        ok: false,
        status: 404,
        json: async () => ({ detail: 'Not found' }),
      });
      vi.stubGlobal('fetch', fetchMock);

      try {
        render(<TransactionHistoryPanel sessionId="session-123" />);

        await waitFor(() => {
          expect(screen.getByText('İşlem geçmişi yüklenemedi, sayfayı yenileyin')).toBeVisible();
        });
      } finally {
        vi.unstubAllGlobals();
      }
    });
  });

  describe('Timeout handling (AC-4)', () => {
    it('shows error message if fetch takes longer than 3 seconds (AC-4)', async () => {
      vi.useFakeTimers();
      const fetchPromise = new Promise(() => {}); // Never resolves
      const fetchMock = vi.fn(() => fetchPromise);
      vi.stubGlobal('fetch', fetchMock);

      try {
        render(<TransactionHistoryPanel sessionId="session-123" />);

        // 3 saniye bekle
        vi.advanceTimersByTime(3000);

        await waitFor(() => {
          expect(screen.getByText('İşlem geçmişi yüklenemedi, sayfayı yenileyin')).toBeVisible();
        });
      } finally {
        vi.unstubAllGlobals();
        vi.useRealTimers();
      }
    });
  });

  describe('Input validation (AC-2, AC-5)', () => {
    it('renders safe empty state when sessionId is not provided (AC-2, AC-5)', () => {
      render(<TransactionHistoryPanel />);

      // Fetch hiç çağrılmamalı
      expect(screen.queryByRole('listitem')).not.toBeInTheDocument();

      // Boş/nötr bir state gösterilmeli (uyarı yok, hata yok)
      expect(screen.queryByTestId('transaction-history-error')).not.toBeInTheDocument();
    });

    it('does not call fetch when sessionId is empty string (AC-2, AC-5)', async () => {
      const fetchMock = vi.fn();
      vi.stubGlobal('fetch', fetchMock);

      try {
        render(<TransactionHistoryPanel sessionId="" />);

        // Fetch çağrılmamalı
        expect(fetchMock).not.toHaveBeenCalled();
      } finally {
        vi.unstubAllGlobals();
      }
    });
  });

  describe('Partial success — transactions succeed, health-check fails (AC-7)', () => {
    it('renders transactions normally while connection status shows disconnected (AC-7, behaviour contract)', async () => {
      const mockTransactions = [
        {
          id: 'tx-1',
          createdAt: '2026-09-01T13:55:00Z',
          status: 'completed',
          fileCount: 2,
          targetFolders: ['Belgeler'],
        },
      ];

      const fetchMock = vi.fn((url) => {
        if (url.includes('/api/transactions')) {
          return Promise.resolve({
            ok: true,
            json: async () => mockTransactions,
          });
        }
        if (url.includes('/api/health')) {
          return Promise.reject(new Error('Health check failed'));
        }
        return Promise.reject(new Error('Unknown endpoint'));
      });
      vi.stubGlobal('fetch', fetchMock);

      try {
        render(<TransactionHistoryPanel sessionId="session-123" />);

        await waitFor(() => {
          // Transactions listesi render edilmeli
          const listItem = screen.getByRole('listitem');
          expect(listItem).toHaveTextContent('Belgeler → 2 dosya');

          // Connection status "Bağlantı kesildi" gösterilmeli
          expect(screen.getByTestId('connection-status')).toHaveTextContent('Bağlantı kesildi');
        });
      } finally {
        vi.unstubAllGlobals();
      }
    });

    it('shows "Bağlı" status when health-check succeeds with llm_reachable=true (AC-7)', async () => {
      const mockTransactions = [
        {
          id: 'tx-1',
          createdAt: '2026-09-01T13:55:00Z',
          status: 'completed',
          fileCount: 1,
          targetFolders: ['Belgeler'],
        },
      ];

      const fetchMock = vi.fn((url) => {
        if (url.includes('/api/transactions')) {
          return Promise.resolve({
            ok: true,
            json: async () => mockTransactions,
          });
        }
        if (url.includes('/api/health')) {
          return Promise.resolve({
            ok: true,
            json: async () => ({ status: 'ok', llm_reachable: true, path_allowed: true }),
          });
        }
        return Promise.reject(new Error('Unknown endpoint'));
      });
      vi.stubGlobal('fetch', fetchMock);

      try {
        render(<TransactionHistoryPanel sessionId="session-123" />);

        await waitFor(() => {
          expect(screen.getByTestId('connection-status')).toHaveTextContent('✓ Bağlı');
        });
      } finally {
        vi.unstubAllGlobals();
      }
    });

    it('shows "Bağlı" status when health-check succeeds with llm_reachable=false (AC-7)', async () => {
      const mockTransactions = [
        {
          id: 'tx-1',
          createdAt: '2026-09-01T13:55:00Z',
          status: 'completed',
          fileCount: 1,
          targetFolders: ['Belgeler'],
        },
      ];

      const fetchMock = vi.fn((url) => {
        if (url.includes('/api/transactions')) {
          return Promise.resolve({
            ok: true,
            json: async () => mockTransactions,
          });
        }
        if (url.includes('/api/health')) {
          return Promise.resolve({
            ok: true,
            json: async () => ({ status: 'ok', llm_reachable: false, path_allowed: true }),
          });
        }
        return Promise.reject(new Error('Unknown endpoint'));
      });
      vi.stubGlobal('fetch', fetchMock);

      try {
        render(<TransactionHistoryPanel sessionId="session-123" />);

        await waitFor(() => {
          // İki durum da "Bağlı" gösterilir, LLM ayrı durum
          expect(screen.getByTestId('connection-status')).toHaveTextContent('✓ Bağlı');
        });
      } finally {
        vi.unstubAllGlobals();
      }
    });
  });

  describe('Auto-refresh on refreshTrigger change (AC-8)', () => {
    it('refetches transactions when refreshTrigger prop changes (AC-8)', async () => {
      const mockTransactionsV1 = [
        {
          id: 'tx-1',
          createdAt: '2026-09-01T13:55:00Z',
          status: 'completed',
          fileCount: 2,
          targetFolders: ['Belgeler'],
        },
      ];

      const mockTransactionsV2 = [
        {
          id: 'tx-1',
          createdAt: '2026-09-01T13:55:00Z',
          status: 'completed',
          fileCount: 2,
          targetFolders: ['Belgeler'],
        },
        {
          id: 'tx-2',
          createdAt: '2026-09-01T13:50:00Z',
          status: 'completed',
          fileCount: 3,
          targetFolders: ['İndirilenler'],
        },
      ];

      let callCount = 0;
      const fetchMock = vi.fn().mockImplementation((url) => {
        if (url.includes('/api/transactions')) {
          callCount++;
          const data = callCount === 1 ? mockTransactionsV1 : mockTransactionsV2;
          return Promise.resolve({
            ok: true,
            json: async () => data,
          });
        }
        return Promise.reject(new Error('Unknown endpoint'));
      });
      vi.stubGlobal('fetch', fetchMock);

      try {
        const { rerender } = render(
          <TransactionHistoryPanel sessionId="session-123" refreshTrigger={0} />
        );

        // İlk yükleme
        await waitFor(() => {
          const listItems = screen.getAllByRole('listitem');
          expect(listItems).toHaveLength(1);
        });

        // refreshTrigger değişti
        rerender(
          <TransactionHistoryPanel sessionId="session-123" refreshTrigger={1} />
        );

        // Yeniden fetch yapılmalı
        await waitFor(() => {
          const listItems = screen.getAllByRole('listitem');
          expect(listItems).toHaveLength(2);
        });

        // Fetch en az 2 kez çağrılmış olmalı
        const transactionsFetches = fetchMock.mock.calls.filter((call) =>
          call[0].includes('/api/transactions')
        );
        expect(transactionsFetches.length).toBeGreaterThanOrEqual(2);
      } finally {
        vi.unstubAllGlobals();
      }
    });
  });

  describe('Regression — data-testid preservation (AC-2)', () => {
    it('maintains the data-testid="chat-left-panel" structure for ChatScreen integration (AC-2)', async () => {
      const mockTransactions = [
        {
          id: 'tx-1',
          createdAt: '2026-09-01T13:55:00Z',
          status: 'completed',
          fileCount: 1,
          targetFolders: ['Belgeler'],
        },
      ];

      const fetchMock = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => mockTransactions,
      });
      vi.stubGlobal('fetch', fetchMock);

      try {
        render(<TransactionHistoryPanel sessionId="session-123" />);

        await waitFor(() => {
          // Panel kendi data-testid'si olmalı (ChatScreen tarafından selectable)
          expect(screen.getByTestId('chat-left-panel')).toBeVisible();
        });
      } finally {
        vi.unstubAllGlobals();
      }
    });
  });
});
