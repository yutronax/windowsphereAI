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
