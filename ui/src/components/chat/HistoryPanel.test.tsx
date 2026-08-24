import { render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import HistoryPanel from './HistoryPanel';

afterEach(() => {
  vi.unstubAllGlobals();
});

// Saga #28 (epic_id): gecmis-transaction-listesi-ui — GET /api/transactions'in
// dondurdugu TUM transaction'lari listeleyen panel. ResultCard'daki tekil-kart
// onizlemesiyle AYNI uc-durumlu preview render mantigi (empty/available===false/
// normal), ama ayri bir bilesen (tip'ler kopyalanir, import edilmez).
describe('HistoryPanel (gecmis-transaction-listesi-ui)', () => {
  it('shows a loading state while the request is in flight (AC1/AC3)', () => {
    vi.stubGlobal('fetch', vi.fn(() => new Promise(() => {})));
    render(<HistoryPanel />);

    expect(screen.getByTestId('history-panel-loading')).toHaveTextContent('Yükleniyor…');
  });

  it('fetches GET /api/transactions on mount (AC2)', async () => {
    const fetchSpy = vi.fn().mockResolvedValue({ ok: true, json: async () => [] });
    vi.stubGlobal('fetch', fetchSpy);
    render(<HistoryPanel />);

    await waitFor(() => expect(fetchSpy).toHaveBeenCalledTimes(1));
    const [url] = fetchSpy.mock.calls[0];
    expect(url).toContain('/api/transactions');
  });

  it('renders id, createdAt, status, fileCount and targetFolders for each transaction (AC2)', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => [
          {
            id: 5,
            createdAt: '2026-08-20T10:00:00Z',
            status: 'completed',
            fileCount: 3,
            targetFolders: ['2026-08', 'faturalar'],
            preview: { empty: false, available: true, truncated: false, total_count: 1, files: [{ name: 'a.pdf', before: 'a.pdf', after: 'a.pdf', status: 'ok', available: true }] },
          },
        ],
      }),
    );
    render(<HistoryPanel />);

    const row = await screen.findByTestId('history-panel-row-5');
    expect(row).toHaveTextContent('5');
    expect(row).toHaveTextContent('2026-08-20');
    expect(row).toHaveTextContent('completed');
    expect(row).toHaveTextContent('3');
    expect(row).toHaveTextContent('2026-08');
    expect(row).toHaveTextContent('faturalar');
  });

  it('shows an error message when the request fails (not a silent failure) (AC3)', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false }));
    render(<HistoryPanel />);

    expect(await screen.findByTestId('history-panel-error')).toHaveTextContent('Geçmiş yüklenemedi.');
  });

  it('shows an error message on a network error (AC3)', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('network down')));
    render(<HistoryPanel />);

    expect(await screen.findByTestId('history-panel-error')).toHaveTextContent('Geçmiş yüklenemedi.');
  });

  it('shows an empty-state message when there is no transaction history (AC4)', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => [] }));
    render(<HistoryPanel />);

    expect(await screen.findByTestId('history-panel-empty')).toHaveTextContent('Henüz bir işlem geçmişi yok.');
  });

  it('shows a "no changes" message when preview.empty is true, distinct from unavailable (AC5)', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => [
          {
            id: 1,
            createdAt: '2026-08-20T10:00:00Z',
            status: 'completed',
            fileCount: 0,
            targetFolders: [],
            preview: { empty: true, available: true, truncated: false, total_count: 0, files: [] },
          },
        ],
      }),
    );
    render(<HistoryPanel />);

    const row = await screen.findByTestId('history-panel-row-1');
    expect(row).toHaveTextContent('Değişiklik yok');
  });

  it('shows an "unavailable" message when preview.available is false (AC5)', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => [
          {
            id: 2,
            createdAt: '2026-08-20T10:00:00Z',
            status: 'completed',
            fileCount: 1,
            targetFolders: ['2026-08'],
            preview: { empty: false, available: false, reason: 'backup_purged', truncated: false, total_count: 0, files: [] },
          },
        ],
      }),
    );
    render(<HistoryPanel />);

    const row = await screen.findByTestId('history-panel-row-2');
    expect(row).toHaveTextContent('Önizleme mevcut değil');
  });

  it('shows the file name list for a normal preview, without leaking a full path (AC5)', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => [
          {
            id: 3,
            createdAt: '2026-08-20T10:00:00Z',
            status: 'completed',
            fileCount: 1,
            targetFolders: ['2026-08'],
            preview: {
              empty: false,
              available: true,
              truncated: false,
              total_count: 1,
              files: [{ name: 'rapor.pdf', before: 'C:\\Users\\Yusuf\\rapor.pdf', after: 'C:\\Users\\Yusuf\\2026-08\\rapor.pdf', status: 'ok', available: true }],
            },
          },
        ],
      }),
    );
    render(<HistoryPanel />);

    const row = await screen.findByTestId('history-panel-row-3');
    expect(row).toHaveTextContent('rapor.pdf');
    expect(row).not.toHaveTextContent('C:\\Users\\Yusuf');
  });

  it('preserves the order returned by the backend (newest first), without re-sorting (AC6)', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => [
          { id: 9, createdAt: '2026-08-21T10:00:00Z', status: 'completed', fileCount: 1, targetFolders: [], preview: { empty: true, available: true, truncated: false, total_count: 0, files: [] } },
          { id: 4, createdAt: '2026-08-20T10:00:00Z', status: 'completed', fileCount: 1, targetFolders: [], preview: { empty: true, available: true, truncated: false, total_count: 0, files: [] } },
        ],
      }),
    );
    render(<HistoryPanel />);

    const rows = await screen.findAllByTestId(/^history-panel-row-/);
    expect(rows.map((row) => row.getAttribute('data-testid'))).toEqual([
      'history-panel-row-9',
      'history-panel-row-4',
    ]);
  });

  it('re-fetches on every mount, so closing and reopening the panel refreshes the list (AC7)', async () => {
    const fetchSpy = vi.fn().mockResolvedValue({ ok: true, json: async () => [] });
    vi.stubGlobal('fetch', fetchSpy);

    const { unmount } = render(<HistoryPanel />);
    await waitFor(() => expect(fetchSpy).toHaveBeenCalledTimes(1));
    unmount();

    render(<HistoryPanel />);
    await waitFor(() => expect(fetchSpy).toHaveBeenCalledTimes(2));
  });
});
