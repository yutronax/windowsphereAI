import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import ResultCard from './ResultCard';

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('ResultCard (Saga #277)', () => {
  it('shows the processed file count (AC-2)', () => {
    render(<ResultCard result={{ fileCount: 3, destinationFolders: ['2026-08'], status: 'completed' }} />);

    expect(screen.getByTestId('result-file-count')).toHaveTextContent('3 dosya işlendi');
  });

  it('lists all destination folders (AC-2)', () => {
    render(
      <ResultCard result={{ fileCount: 3, destinationFolders: ['2026-07', '2026-08'], status: 'completed' }} />,
    );

    const list = screen.getByTestId('result-destination-folders');
    expect(list).toHaveTextContent('2026-07');
    expect(list).toHaveTextContent('2026-08');
  });

  it('shows a clear empty-state message when no folders were created, without crashing (AC-6)', () => {
    render(<ResultCard result={{ fileCount: 0, destinationFolders: [], status: 'completed' }} />);

    expect(screen.getByTestId('result-no-folders')).toHaveTextContent('Hiçbir klasör oluşturulmadı.');
    expect(screen.queryByTestId('result-destination-folders')).not.toBeInTheDocument();
  });

  it('shows a distinguishable completion status text (AC-3)', () => {
    render(<ResultCard result={{ fileCount: 1, destinationFolders: ['2026-08'], status: 'completed' }} />);

    expect(screen.getByTestId('result-status-text')).toHaveTextContent('İşlem tamamlandı.');
  });

  it('visually distinguishes a failed status from a completed one (AC-3)', () => {
    render(<ResultCard result={{ fileCount: 0, destinationFolders: [], status: 'failed' }} />);

    const statusText = screen.getByTestId('result-status-text');
    expect(statusText).toHaveTextContent('İşlem tamamlanamadı.');
    expect(statusText).toHaveClass('is-failed');
  });

  it('announces the status text inside an aria-live polite region (AC-4)', () => {
    render(<ResultCard result={{ fileCount: 1, destinationFolders: ['2026-08'], status: 'completed' }} />);

    const region = screen.getByTestId('result-status-text').closest('[aria-live]');
    expect(region).toHaveAttribute('aria-live', 'polite');
  });
});

describe('ResultCard "Geri al" (Saga #295)', () => {
  const baseResult = { fileCount: 1, destinationFolders: ['2026-08'], status: 'completed' as const };

  it('does not show the revert button when transactionId is missing (AC-2)', () => {
    render(<ResultCard result={{ ...baseResult, selectedFolder: 'C:\\Users\\Yusuf\\Documents' }} />);

    expect(screen.queryByTestId('result-revert-button')).not.toBeInTheDocument();
  });

  it('shows the revert button even when selectedFolder is missing, since only transactionId gates it now (Saga #301)', () => {
    render(<ResultCard result={{ ...baseResult, transactionId: 1 }} />);

    expect(screen.getByTestId('result-revert-button')).toBeInTheDocument();
  });

  it('shows the revert button when both transactionId and selectedFolder are given (AC-2)', () => {
    render(
      <ResultCard result={{ ...baseResult, transactionId: 1, selectedFolder: 'C:\\Users\\Yusuf\\Documents' }} />,
    );

    expect(screen.getByTestId('result-revert-button')).toBeInTheDocument();
  });

  it('requires a second confirmation click before sending the revert request (AC-3)', () => {
    const fetchSpy = vi.fn();
    vi.stubGlobal('fetch', fetchSpy);
    render(
      <ResultCard result={{ ...baseResult, transactionId: 1, selectedFolder: 'C:\\Users\\Yusuf\\Documents' }} />,
    );

    fireEvent.click(screen.getByTestId('result-revert-button'));

    expect(fetchSpy).not.toHaveBeenCalled();
    expect(screen.getByTestId('result-revert-confirm-button')).toBeInTheDocument();
    expect(screen.getByTestId('result-revert-cancel-button')).toBeInTheDocument();
  });

  it('cancelling the confirmation step returns to the initial button without sending a request (AC-3)', () => {
    const fetchSpy = vi.fn();
    vi.stubGlobal('fetch', fetchSpy);
    render(
      <ResultCard result={{ ...baseResult, transactionId: 1, selectedFolder: 'C:\\Users\\Yusuf\\Documents' }} />,
    );

    fireEvent.click(screen.getByTestId('result-revert-button'));
    fireEvent.click(screen.getByTestId('result-revert-cancel-button'));

    expect(fetchSpy).not.toHaveBeenCalled();
    expect(screen.getByTestId('result-revert-button')).toBeInTheDocument();
    expect(screen.queryByTestId('result-revert-confirm-button')).not.toBeInTheDocument();
  });

  it('sends the revert request with an empty body (no allowedRoot) only after the second click (Saga #301)', async () => {
    const fetchSpy = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ transactionId: 42, status: 'reverted' }),
    });
    vi.stubGlobal('fetch', fetchSpy);
    render(
      <ResultCard result={{ ...baseResult, transactionId: 42, selectedFolder: 'C:\\Users\\Yusuf\\Documents' }} />,
    );

    fireEvent.click(screen.getByTestId('result-revert-button'));
    fireEvent.click(screen.getByTestId('result-revert-confirm-button'));

    await waitFor(() => expect(fetchSpy).toHaveBeenCalledTimes(1));
    const [url, options] = fetchSpy.mock.calls[0];
    expect(url).toContain('/api/transactions/42/revert');
    expect(options.method).toBe('POST');
    expect(JSON.parse(options.body)).toEqual({});
  });

  it('shows the revert button and sends an empty body even when selectedFolder is undefined (Saga #301)', async () => {
    const fetchSpy = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ transactionId: 42, status: 'reverted' }),
    });
    vi.stubGlobal('fetch', fetchSpy);
    render(<ResultCard result={{ ...baseResult, transactionId: 42 }} />);

    expect(screen.getByTestId('result-revert-button')).toBeInTheDocument();

    fireEvent.click(screen.getByTestId('result-revert-button'));
    fireEvent.click(screen.getByTestId('result-revert-confirm-button'));

    await waitFor(() => expect(fetchSpy).toHaveBeenCalledTimes(1));
    const [url, options] = fetchSpy.mock.calls[0];
    expect(url).toContain('/api/transactions/42/revert');
    expect(JSON.parse(options.body)).toEqual({});
  });

  it('shows a success message inside aria-live after a successful revert (AC-4)', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, json: async () => ({ transactionId: 1, status: 'reverted' }) }),
    );
    render(
      <ResultCard result={{ ...baseResult, transactionId: 1, selectedFolder: 'C:\\Users\\Yusuf\\Documents' }} />,
    );

    fireEvent.click(screen.getByTestId('result-revert-button'));
    fireEvent.click(screen.getByTestId('result-revert-confirm-button'));

    const statusText = await screen.findByTestId('result-revert-status-text');
    expect(statusText).toHaveTextContent('İşlem geri alındı.');
    expect(statusText.closest('[aria-live]')).toHaveAttribute('aria-live', 'polite');
    expect(screen.queryByTestId('result-revert-button')).not.toBeInTheDocument();
  });

  it('shows a distinguishable message when the backend reports a partial/failed revert (AC-4)', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, json: async () => ({ transactionId: 1, status: 'revert_failed' }) }),
    );
    render(
      <ResultCard result={{ ...baseResult, transactionId: 1, selectedFolder: 'C:\\Users\\Yusuf\\Documents' }} />,
    );

    fireEvent.click(screen.getByTestId('result-revert-button'));
    fireEvent.click(screen.getByTestId('result-revert-confirm-button'));

    const statusText = await screen.findByTestId('result-revert-status-text');
    expect(statusText).toHaveTextContent('İşlem tam olarak geri alınamadı');
    expect(statusText).toHaveClass('is-failed');
  });

  it('re-enables the button and shows an error message when the request fails, without a false success (AC-4)', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false }));
    render(
      <ResultCard result={{ ...baseResult, transactionId: 1, selectedFolder: 'C:\\Users\\Yusuf\\Documents' }} />,
    );

    fireEvent.click(screen.getByTestId('result-revert-button'));
    fireEvent.click(screen.getByTestId('result-revert-confirm-button'));

    const errorText = await screen.findByTestId('result-revert-status-text');
    expect(errorText).toHaveTextContent('Geri alma isteği başarısız oldu');

    fireEvent.click(screen.getByTestId('result-revert-retry-button'));
    expect(screen.getByTestId('result-revert-button')).toBeInTheDocument();
    expect(screen.queryByTestId('result-revert-status-text')).not.toBeInTheDocument();
  });

  it('re-enables the button and shows an error message on a network error (AC-4)', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('network down')));
    render(
      <ResultCard result={{ ...baseResult, transactionId: 1, selectedFolder: 'C:\\Users\\Yusuf\\Documents' }} />,
    );

    fireEvent.click(screen.getByTestId('result-revert-button'));
    fireEvent.click(screen.getByTestId('result-revert-confirm-button'));

    expect(await screen.findByTestId('result-revert-status-text')).toHaveTextContent(
      'Geri alma isteği başarısız oldu',
    );
  });
});

// --- Saga #317: diff-tray-onizleme-ui (RED STEP) ---
// Kullanici transaction'in uzerine hover yaptiginda, GET /api/transactions'in
// dondurdugu `preview` alanindan (kendi transactionId'sine karsilik gelen
// transaction'i bularak) etkilenen dosyalarin kisa bir onizlemesini gorur.
// Henuz implementasyon YOK (ResultCard'da hover handler'i/preview render'i
// yok) - bu testler simdi KIRMIZI olmali.
describe('ResultCard hover onizleme (Saga #317)', () => {
  const baseResult = { fileCount: 1, destinationFolders: ['2026-08'], status: 'completed' as const, transactionId: 7 };

  function mockTransactionsResponse(preview: unknown) {
    return vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [{ id: 7, createdAt: '2026-08-20T10:00:00Z', status: 'committed', fileCount: 1, targetFolders: ['2026-08'], preview }],
    });
  }

  it('fetches and shows the file name preview list on hover (AC-1/AC-2)', async () => {
    vi.stubGlobal(
      'fetch',
      mockTransactionsResponse({
        empty: false,
        available: true,
        truncated: false,
        total_count: 1,
        files: [{ name: 'a.pdf', before: 'a.pdf', after: 'a.pdf', status: 'ok', available: true }],
      }),
    );
    render(<ResultCard result={baseResult} />);

    fireEvent.mouseEnter(screen.getByTestId('result-card'));

    const preview = await screen.findByTestId('result-preview');
    expect(preview).toHaveTextContent('a.pdf');
  });

  it('shows a "no changes" message when the preview is empty, distinct from unavailable (AC-3)', async () => {
    vi.stubGlobal('fetch', mockTransactionsResponse({ empty: true, available: true, truncated: false, total_count: 0, files: [] }));
    render(<ResultCard result={baseResult} />);

    fireEvent.mouseEnter(screen.getByTestId('result-card'));

    expect(await screen.findByTestId('result-preview-empty')).toHaveTextContent('Değişiklik yok');
    expect(screen.queryByTestId('result-preview-unavailable')).not.toBeInTheDocument();
  });

  it('shows an "unavailable" message distinguishable from the empty state when preview.available is false (AC-4)', async () => {
    vi.stubGlobal(
      'fetch',
      mockTransactionsResponse({ empty: false, available: false, reason: 'backup_purged', truncated: false, total_count: 0, files: [] }),
    );
    render(<ResultCard result={baseResult} />);

    fireEvent.mouseEnter(screen.getByTestId('result-card'));

    expect(await screen.findByTestId('result-preview-unavailable')).toHaveTextContent('Önizleme mevcut değil');
    expect(screen.queryByTestId('result-preview-empty')).not.toBeInTheDocument();
  });

  it('shows a "+N daha" summary when the preview was truncated (AC-5)', async () => {
    vi.stubGlobal(
      'fetch',
      mockTransactionsResponse({
        empty: false,
        available: true,
        truncated: true,
        total_count: 15,
        files: Array.from({ length: 10 }, (_, i) => ({ name: `dosya${i}.pdf`, before: `dosya${i}.pdf`, after: `dosya${i}.pdf`, status: 'ok', available: true })),
      }),
    );
    render(<ResultCard result={baseResult} />);

    fireEvent.mouseEnter(screen.getByTestId('result-card'));

    expect(await screen.findByTestId('result-preview-truncated')).toHaveTextContent('+5 daha');
  });

  it('marks a file whose before/after state could not be computed with a distinguishable "?" marker (AC-6)', async () => {
    vi.stubGlobal(
      'fetch',
      mockTransactionsResponse({
        empty: false,
        available: true,
        truncated: false,
        total_count: 2,
        files: [
          { name: 'iyi.pdf', before: 'iyi.pdf', after: 'iyi.pdf', status: 'ok', available: true },
          { name: 'bilinmeyen.pdf', before: null, after: null, status: 'unknown', available: true },
        ],
      }),
    );
    render(<ResultCard result={baseResult} />);

    fireEvent.mouseEnter(screen.getByTestId('result-card'));

    const preview = await screen.findByTestId('result-preview');
    expect(preview).toHaveTextContent('iyi.pdf');
    expect(preview).toHaveTextContent('bilinmeyen.pdf');
    expect(screen.getByTestId('result-preview-unknown-bilinmeyen.pdf')).toHaveTextContent('?');
  });

  it('does not show any preview when transactionId is missing', () => {
    render(<ResultCard result={{ fileCount: 1, destinationFolders: ['2026-08'], status: 'completed' }} />);

    fireEvent.mouseEnter(screen.getByTestId('result-card'));

    expect(screen.queryByTestId('result-preview')).not.toBeInTheDocument();
  });

  it('shows a visible error message when the preview fetch fails, instead of silently showing nothing (red-team bulgusu)', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false }));
    render(<ResultCard result={baseResult} />);

    fireEvent.mouseEnter(screen.getByTestId('result-card'));

    expect(await screen.findByTestId('result-preview-error')).toHaveTextContent('Önizleme yüklenemedi.');
    expect(screen.queryByTestId('result-preview')).not.toBeInTheDocument();
  });

  it('shows a visible error message when the transactions list does not contain this transaction id', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => [] }));
    render(<ResultCard result={baseResult} />);

    fireEvent.mouseEnter(screen.getByTestId('result-card'));

    expect(await screen.findByTestId('result-preview-error')).toBeInTheDocument();
  });

  it('the top-level preview.available=false (not just the per-file one) drives the "unavailable" message (red-team bulgusu)', async () => {
    vi.stubGlobal(
      'fetch',
      mockTransactionsResponse({
        empty: false,
        available: false,
        reason: 'backup_purged',
        truncated: false,
        total_count: 1,
        files: [{ name: 'silinen.pdf', before: 'silinen.pdf', after: 'silinen.pdf', status: 'ok', available: false, reason: 'backup_purged' }],
      }),
    );
    render(<ResultCard result={baseResult} />);

    fireEvent.mouseEnter(screen.getByTestId('result-card'));

    expect(await screen.findByTestId('result-preview-unavailable')).toHaveTextContent('Önizleme mevcut değil');
  });
});
