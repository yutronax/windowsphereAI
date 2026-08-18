import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import SearchPanel from './SearchPanel';

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

function mockJsonResponse(body: unknown, ok = true, status = ok ? 200 : 500) {
  return {
    ok,
    status,
    json: () => Promise.resolve(body),
  } as Response;
}

describe('SearchPanel (dosya-arama-frontend-ui / Saga #334)', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.stubGlobal('fetch', vi.fn());
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it('renders an empty result list with the "enter a filter" hint and does not call fetch initially (AC-1)', () => {
    render(<SearchPanel sessionId="session-1" />);

    expect(screen.getByText('Aramak için bir filtre girin')).toBeVisible();
    expect(screen.queryAllByRole('listitem')).toHaveLength(0);
    expect(fetch).not.toHaveBeenCalled();
  });

  it('debounces nameContains input and calls fetch exactly once after 300ms, rendering results (AC-2)', async () => {
    (fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(
      mockJsonResponse({
        results: [{ filename: 'a.pdf', extension: '.pdf', modifiedAt: '2026-08-01T00:00:00Z', sizeBytes: 100 }],
        partial: false,
      }),
    );

    render(<SearchPanel sessionId="session-1" />);

    fireEvent.change(screen.getByLabelText(/isim/i), { target: { value: 'a' } });

    expect(fetch).not.toHaveBeenCalled();

    vi.advanceTimersByTime(300);

    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(1));

    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/search'),
      expect.objectContaining({
        method: 'POST',
        body: expect.stringContaining('"sessionId":"session-1"'),
      }),
    );

    await waitFor(() => expect(screen.getByText('a.pdf')).toBeVisible());
  });

  it('only shows the result of the most recently sent request when requests race (AC-3)', async () => {
    const first = deferred<Response>();
    const second = deferred<Response>();
    const fetchMock = fetch as unknown as ReturnType<typeof vi.fn>;
    fetchMock.mockImplementationOnce(() => first.promise).mockImplementationOnce(() => second.promise);

    render(<SearchPanel sessionId="session-1" />);
    const input = screen.getByLabelText(/isim/i);

    fireEvent.change(input, { target: { value: 'a' } });
    vi.advanceTimersByTime(300);
    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(1));

    fireEvent.change(input, { target: { value: 'ab' } });
    vi.advanceTimersByTime(300);
    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(2));

    // Second (latest) request resolves first.
    second.resolve(
      mockJsonResponse({
        results: [{ filename: 'second.pdf', extension: '.pdf', modifiedAt: '2026-08-01T00:00:00Z', sizeBytes: 1 }],
        partial: false,
      }),
    );
    await waitFor(() => expect(screen.getByText('second.pdf')).toBeVisible());

    // First (stale) request resolves late — must not overwrite the latest result.
    first.resolve(
      mockJsonResponse({
        results: [{ filename: 'first-stale.pdf', extension: '.pdf', modifiedAt: '2026-08-01T00:00:00Z', sizeBytes: 1 }],
        partial: false,
      }),
    );

    await new Promise((resolve) => setTimeout(resolve, 0));

    expect(screen.getByText('second.pdf')).toBeVisible();
    expect(screen.queryByText('first-stale.pdf')).not.toBeInTheDocument();
  });

  it('shows an error message and clears the result list when fetch rejects (AC-4)', async () => {
    (fetch as unknown as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('network down'));

    render(<SearchPanel sessionId="session-1" />);
    fireEvent.change(screen.getByLabelText(/isim/i), { target: { value: 'a' } });
    vi.advanceTimersByTime(300);

    await waitFor(() => expect(screen.getByTestId('search-panel-error')).toBeVisible());
    expect(screen.getByTestId('search-panel-error')).toHaveTextContent('Sunucuya ulaşılamadı. Lütfen tekrar deneyin.');
    expect(screen.queryAllByRole('listitem')).toHaveLength(0);
  });

  it('shows an error message and clears the result list when response.ok is false (AC-4)', async () => {
    (fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(mockJsonResponse({ detail: 'geçersiz filtre' }, false));

    render(<SearchPanel sessionId="session-1" />);
    fireEvent.change(screen.getByLabelText(/isim/i), { target: { value: 'a' } });
    vi.advanceTimersByTime(300);

    await waitFor(() => expect(screen.getByTestId('search-panel-error')).toBeVisible());
    expect(screen.queryAllByRole('listitem')).toHaveLength(0);
  });

  it('shows the backend detail message from the search contract when response.status is 422 (Saga #334 red-team fix)', async () => {
    (fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(
      mockJsonResponse({ detail: "modifiedAfter geçersiz ISO 8601 formatı: 'not-a-date'" }, false, 422),
    );

    render(<SearchPanel sessionId="session-1" />);
    fireEvent.change(screen.getByLabelText(/isim/i), { target: { value: 'a' } });
    vi.advanceTimersByTime(300);

    await waitFor(() => expect(screen.getByTestId('search-panel-error')).toBeVisible());
    expect(screen.getByTestId('search-panel-error')).toHaveTextContent(
      "modifiedAfter geçersiz ISO 8601 formatı: 'not-a-date'",
    );
    expect(screen.queryAllByRole('listitem')).toHaveLength(0);
  });

  it('shows the "folder no longer exists" message when response.status is 410 (Saga #334 red-team fix)', async () => {
    (fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(
      mockJsonResponse({ detail: 'Seçili klasör artık mevcut değil' }, false, 410),
    );

    render(<SearchPanel sessionId="session-1" />);
    fireEvent.change(screen.getByLabelText(/isim/i), { target: { value: 'a' } });
    vi.advanceTimersByTime(300);

    await waitFor(() => expect(screen.getByTestId('search-panel-error')).toBeVisible());
    expect(screen.getByTestId('search-panel-error')).toHaveTextContent('Seçili klasör artık mevcut değil');
    expect(screen.queryAllByRole('listitem')).toHaveLength(0);
  });

  it('shows a "no results" message distinct from the initial hint when filters match nothing (AC-5)', async () => {
    (fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(mockJsonResponse({ results: [], partial: false }));

    render(<SearchPanel sessionId="session-1" />);
    fireEvent.change(screen.getByLabelText(/isim/i), { target: { value: 'yoktur' } });
    vi.advanceTimersByTime(300);

    await waitFor(() => expect(screen.getByTestId('search-panel-empty')).toBeVisible());
    expect(screen.getByTestId('search-panel-empty')).toHaveTextContent('Sonuç bulunamadı');
    expect(screen.queryByText('Aramak için bir filtre girin')).not.toBeInTheDocument();
  });

  it('resets filters/results state when unmounted and remounted (AC-6)', async () => {
    (fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(
      mockJsonResponse({
        results: [{ filename: 'a.pdf', extension: '.pdf', modifiedAt: '2026-08-01T00:00:00Z', sizeBytes: 100 }],
        partial: false,
      }),
    );

    const { unmount } = render(<SearchPanel sessionId="session-1" />);
    fireEvent.change(screen.getByLabelText(/isim/i), { target: { value: 'a' } });
    vi.advanceTimersByTime(300);
    await waitFor(() => expect(screen.getByText('a.pdf')).toBeVisible());

    unmount();

    render(<SearchPanel sessionId="session-1" />);

    expect(screen.getByText('Aramak için bir filtre girin')).toBeVisible();
    expect(screen.queryByText('a.pdf')).not.toBeInTheDocument();
    expect(screen.getByLabelText(/isim/i)).toHaveValue('');
  });

  it('does not trigger any action when a result row is clicked (AC-7, read-only list)', async () => {
    (fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(
      mockJsonResponse({
        results: [{ filename: 'a.pdf', extension: '.pdf', modifiedAt: '2026-08-01T00:00:00Z', sizeBytes: 100 }],
        partial: false,
      }),
    );

    render(<SearchPanel sessionId="session-1" />);
    fireEvent.change(screen.getByLabelText(/isim/i), { target: { value: 'a' } });
    vi.advanceTimersByTime(300);
    await waitFor(() => expect(screen.getByText('a.pdf')).toBeVisible());

    const row = screen.getByText('a.pdf').closest('li');
    expect(row).not.toBeNull();
    expect(screen.queryByRole('button', { name: /a\.pdf/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: /a\.pdf/i })).not.toBeInTheDocument();

    expect(() => fireEvent.click(row as HTMLElement)).not.toThrow();
    // No navigation/callback exists to assert on — the contract is simply
    // that the row is not an interactive element (no button/link role).
  });
});
