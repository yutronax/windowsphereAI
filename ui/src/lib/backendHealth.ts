const BACKEND_ORIGIN = 'http://127.0.0.1:8000';

type BackendHealthStatus = 'ready' | 'backend_timeout';

export function waitForBackendHealth(
  { intervalMs = 1000, timeoutMs = 10000 }: { intervalMs?: number; timeoutMs?: number } = {},
): Promise<{ status: BackendHealthStatus }> {
  return new Promise((resolve) => {
    let settled = false;
    let retryTimer: ReturnType<typeof setTimeout> | undefined;

    const finish = (status: BackendHealthStatus) => {
      if (settled) return;
      settled = true;
      clearTimeout(deadlineTimer);
      if (retryTimer) clearTimeout(retryTimer);
      resolve({ status });
    };

    const retry = () => {
      if (!settled) retryTimer = setTimeout(check, intervalMs);
    };

    const check = () => {
      fetch(`${BACKEND_ORIGIN}/api/health`, { method: 'GET' })
        .then((response) => {
          if (response.ok) finish('ready');
          else retry();
        })
        .catch(retry);
    };

    const deadlineTimer = setTimeout(() => finish('backend_timeout'), timeoutMs);
    check();
  });
}
