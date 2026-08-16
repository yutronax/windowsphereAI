import { afterEach, describe, expect, it, vi } from 'vitest';

import { waitForBackendHealth } from './backendHealth';

describe('waitForBackendHealth', () => {
  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it('reports ready immediately when the health endpoint responds successfully', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ status: 'ok' }), { status: 200 }));
    vi.stubGlobal('fetch', fetchMock);

    await expect(waitForBackendHealth()).resolves.toEqual({ status: 'ready' });
    expect(fetchMock).toHaveBeenCalledWith('http://127.0.0.1:8000/api/health', expect.any(Object));
  });

  it('continues polling while the sidecar is unavailable and becomes ready once it responds', async () => {
    vi.useFakeTimers();
    const fetchMock = vi
      .fn()
      .mockRejectedValueOnce(new TypeError('Failed to fetch'))
      .mockResolvedValueOnce(new Response(JSON.stringify({ status: 'ok' }), { status: 200 }));
    vi.stubGlobal('fetch', fetchMock);

    const health = waitForBackendHealth({ intervalMs: 1_000, timeoutMs: 10_000 });
    await vi.advanceTimersByTimeAsync(1_000);

    await expect(health).resolves.toEqual({ status: 'ready' });
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it('returns backend_timeout exactly after the configured ten-second health-check deadline', async () => {
    vi.useFakeTimers();
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')));

    const health = waitForBackendHealth({ intervalMs: 1_000, timeoutMs: 10_000 });
    let settled = false;
    void health.finally(() => {
      settled = true;
    });
    await vi.advanceTimersByTimeAsync(9_999);
    expect(settled).toBe(false);

    await vi.advanceTimersByTimeAsync(1);
    await expect(health).resolves.toEqual({ status: 'backend_timeout' });
  });
});
